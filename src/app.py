import os
import joblib
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS

from src.database.db import SessionLocal, init_db, execute_raw_sql
from src.database.models import Patient, LabResult, MedicalRecord, Prediction, ClinicalDocument, AuditLog
from src.security.auth import get_current_user_context, log_audit_action, ROLES
from src.rag.assistant import ClinicalRAGAssistant
from src.ml.trainer import train_and_evaluate_all

app = Flask(__name__, template_folder="templates", static_folder="static")
CORS(app)

rag_assistant = ClinicalRAGAssistant()

@app.before_request
def ensure_db_ready():
    init_db()

@app.route('/')
def index():
    """Render main Single Page Application dashboard."""
    return render_template('index.html')

# --- 1. DASHBOARD OVERVIEW ENDPOINTS ---
@app.route('/api/dashboard/stats', methods=['GET'])
def get_dashboard_stats():
    role, user_name = get_current_user_context(request)
    log_audit_action(role, user_name, "VIEW_STATS", "dashboard_overview")

    session = SessionLocal()
    total_patients = session.query(Patient).count()
    
    # Risk counts based on predictions table
    high_risk_count = session.query(Prediction).filter_by(risk_category="HIGH").group_by(Prediction.patient_id).count()
    mod_risk_count = session.query(Prediction).filter_by(risk_category="MODERATE").group_by(Prediction.patient_id).count()
    low_risk_count = max(0, total_patients - high_risk_count - mod_risk_count)

    readmissions_count = session.query(MedicalRecord).filter(MedicalRecord.prior_admissions > 0).count()

    # Risk Distribution chart data
    risk_distribution = {
        "Low": low_risk_count,
        "Moderate": mod_risk_count,
        "High": high_risk_count
    }

    # Disease Risk Averages
    diabetes_preds = session.query(Prediction).filter_by(model_name="Diabetes Risk").all()
    cardiac_preds = session.query(Prediction).filter_by(model_name="Cardiac Risk").all()
    readmit_preds = session.query(Prediction).filter_by(model_name="Readmission Risk").all()

    avg_diabetes = round(sum([p.risk_score for p in diabetes_preds]) / max(1, len(diabetes_preds)) * 100, 1)
    avg_cardiac = round(sum([p.risk_score for p in cardiac_preds]) / max(1, len(cardiac_preds)) * 100, 1)
    avg_readmit = round(sum([p.risk_score for p in readmit_preds]) / max(1, len(readmit_preds)) * 100, 1)

    session.close()

    return jsonify({
        "total_patients": total_patients,
        "high_risk_patients": high_risk_count,
        "readmissions_count": readmissions_count,
        "risk_distribution": risk_distribution,
        "disease_risk_trends": {
            "Diabetes Risk Avg": avg_diabetes,
            "Cardiac Risk Avg": avg_cardiac,
            "Readmission Risk Avg": avg_readmit
        }
    })

# --- 2. PATIENT DIRECTORY & DETAILS ---
@app.route('/api/patients', methods=['GET'])
def get_patients():
    role, user_name = get_current_user_context(request)
    log_audit_action(role, user_name, "LIST_PATIENTS", "patients_table")

    search_q = request.args.get('search', '').strip().lower()
    risk_filter = request.args.get('risk', '').strip().upper()
    anonymize = ROLES[role]["can_anonymize"]

    session = SessionLocal()
    query = session.query(Patient)

    patients = query.all()
    patient_list = []

    for p in patients:
        labs = session.query(LabResult).filter_by(patient_id=p.patient_id).first()
        rec = session.query(MedicalRecord).filter_by(patient_id=p.patient_id).first()
        preds = session.query(Prediction).filter_by(patient_id=p.patient_id).all()

        p_dict = p.to_dict(anonymize=anonymize)
        p_dict['lab_results'] = labs.to_dict() if labs else {}
        p_dict['medical_record'] = rec.to_dict() if rec else {}
        p_dict['predictions'] = [pr.to_dict() for pr in preds]

        # Highest risk category calculation
        categories = [pr.risk_category for pr in preds]
        max_cat = "HIGH" if "HIGH" in categories else ("MODERATE" if "MODERATE" in categories else "LOW")
        p_dict['overall_risk'] = max_cat

        # Apply search and filter
        if search_q and search_q not in p.patient_id.lower() and search_q not in p.name.lower():
            continue
        if risk_filter and risk_filter != "ALL" and max_cat != risk_filter:
            continue

        patient_list.append(p_dict)

    session.close()
    return jsonify({"count": len(patient_list), "patients": patient_list})

@app.route('/api/patients/<patient_id>', methods=['GET'])
def get_patient_detail(patient_id):
    role, user_name = get_current_user_context(request)
    log_audit_action(role, user_name, "VIEW_PATIENT", f"patient_id:{patient_id}")

    anonymize = ROLES[role]["can_anonymize"]
    session = SessionLocal()

    p = session.query(Patient).filter_by(patient_id=patient_id).first()
    if not p:
        session.close()
        return jsonify({"error": "Patient not found"}), 404

    labs = session.query(LabResult).filter_by(patient_id=patient_id).first()
    rec = session.query(MedicalRecord).filter_by(patient_id=patient_id).first()
    preds = session.query(Prediction).filter_by(patient_id=patient_id).all()

    data = p.to_dict(anonymize=anonymize)
    data['lab_results'] = labs.to_dict() if labs else {}
    data['medical_record'] = rec.to_dict() if rec else {}
    data['predictions'] = [pr.to_dict() for pr in preds]

    session.close()
    return jsonify(data)

# --- 3. ML MODEL METRICS & TRAINING ---
@app.route('/api/ml/metrics', methods=['GET'])
def get_ml_metrics():
    role, user_name = get_current_user_context(request)
    log_audit_action(role, user_name, "VIEW_ML_METRICS", "evaluation_summary")

    summary_path = os.path.join(os.path.dirname(__file__), "..", "models", "evaluation_summary.joblib")
    if os.path.exists(summary_path):
        results = joblib.load(summary_path)
    else:
        results = train_and_evaluate_all()

    return jsonify(results)

@app.route('/api/ml/train', methods=['POST'])
def train_models_endpoint():
    role, user_name = get_current_user_context(request)
    if not ROLES[role]["can_run_ml"]:
        return jsonify({"error": "Unauthorized role for ML retraining"}), 403

    log_audit_action(role, user_name, "RETRAIN_MODELS", "ml_pipeline")
    results = train_and_evaluate_all()
    return jsonify({"status": "Success", "message": "ML models retrained and predictions re-generated!", "metrics": results})

# --- 4. CLINICAL RAG ASSISTANT ENDPOINTS ---
@app.route('/api/rag/query', methods=['POST'])
def query_rag():
    role, user_name = get_current_user_context(request)
    data = request.json or {}
    question = data.get("question", "").strip()

    if not question:
        return jsonify({"error": "Question is required"}), 400

    log_audit_action(role, user_name, "RAG_KB_QUERY", f"query:{question[:50]}")
    res = rag_assistant.query_knowledge_base(question)
    return jsonify(res)

@app.route('/api/rag/explain_patient', methods=['POST'])
def explain_patient():
    role, user_name = get_current_user_context(request)
    data = request.json or {}
    patient_id = data.get("patient_id", "").strip()

    if not patient_id:
        return jsonify({"error": "patient_id is required"}), 400

    log_audit_action(role, user_name, "RAG_PATIENT_EXPLANATION", f"patient_id:{patient_id}")
    res = rag_assistant.explain_patient_risk(patient_id)
    return jsonify(res)

@app.route('/api/rag/documents', methods=['GET', 'POST'])
def manage_documents():
    role, user_name = get_current_user_context(request)

    session = SessionLocal()
    if request.method == 'GET':
        docs = session.query(ClinicalDocument).all()
        doc_list = [d.to_dict() for d in docs]
        session.close()
        return jsonify({"count": len(doc_list), "documents": doc_list})

    if request.method == 'POST':
        if not ROLES[role]["can_upload_docs"]:
            session.close()
            return jsonify({"error": "Unauthorized role to upload clinical documents"}), 403

        data = request.json or {}
        filename = data.get("filename", "custom_guideline.pdf")
        doc_type = data.get("document_type", "Guideline")
        content = data.get("content", "").strip()

        if not content:
            session.close()
            return jsonify({"error": "Document content is required"}), 400

        doc = ClinicalDocument(
            filename=filename,
            document_type=doc_type,
            file_size_bytes=len(content),
            chunk_count=len(content.split("\n\n"))
        )
        session.add(doc)
        session.commit()
        session.close()

        log_audit_action(role, user_name, "UPLOAD_DOCUMENT", f"filename:{filename}")
        
        # Re-index RAG store
        rag_assistant.vector_store.build_index()

        return jsonify({"status": "Success", "message": f"Document '{filename}' indexed into vector DB!"})

# --- 5. INTERACTIVE SQL ANALYTICS EXPLORER ---
PREDEFINED_SQL_QUERIES = {
    "high_risk_join": """
SELECT 
    p.patient_id, 
    p.name, 
    p.age, 
    l.glucose, 
    l.hemoglobin_a1c AS hba1c, 
    l.bmi, 
    pr.risk_score * 100 AS diabetes_risk_pct, 
    pr.risk_category
FROM patients p
JOIN lab_results l ON p.patient_id = l.patient_id
JOIN predictions pr ON p.patient_id = pr.patient_id
WHERE pr.model_name = 'Diabetes Risk' AND pr.risk_category = 'HIGH'
ORDER BY l.glucose DESC
LIMIT 10;
""",
    "readmission_aggregates": """
SELECT 
    p.smoking_status,
    COUNT(p.patient_id) AS total_patients,
    AVG(m.length_of_stay_days) AS avg_hospital_stay_days,
    SUM(CASE WHEN m.prior_admissions > 0 THEN 1 ELSE 0 END) AS readmitted_patients,
    ROUND(AVG(m.prior_admissions), 2) AS avg_prior_admissions
FROM patients p
JOIN medical_records m ON p.patient_id = m.patient_id
GROUP BY p.smoking_status
ORDER BY readmitted_patients DESC;
""",
    "subquery_lab_outliers": """
SELECT 
    p.patient_id, 
    p.name, 
    p.age, 
    l.glucose, 
    l.cholesterol
FROM patients p
JOIN lab_results l ON p.patient_id = l.patient_id
WHERE l.glucose > (SELECT AVG(glucose) + 1.5 * AVG(glucose)/4 FROM lab_results)
ORDER BY l.glucose DESC;
"""
}

@app.route('/api/sql/query', methods=['POST'])
def run_sql_query():
    role, user_name = get_current_user_context(request)
    if not ROLES[role]["can_execute_sql"]:
        return jsonify({"error": "Unauthorized role for SQL execution"}), 403

    data = request.json or {}
    query_key = data.get("preset_key", "")
    custom_query = data.get("query", "").strip()

    sql_to_run = PREDEFINED_SQL_QUERIES.get(query_key, custom_query)

    if not sql_to_run:
        return jsonify({"error": "No valid SQL query provided"}), 400

    # Prevent destructive DROP/DELETE statements for safety demo
    upper_sql = sql_to_run.upper()
    if "DROP " in upper_sql or "DELETE " in upper_sql or "TRUNCATE " in upper_sql:
        return jsonify({"error": "Destructive DDL/DML queries are disabled in safety demo mode."}), 400

    log_audit_action(role, user_name, "EXECUTE_SQL", f"query:{sql_to_run[:60]}")
    try:
        res = execute_raw_sql(sql_to_run)
        return jsonify({"status": "Success", "query": sql_to_run, "result": res})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# --- 6. AUDIT LOGS ENDPOINT ---
@app.route('/api/audit', methods=['GET'])
def get_audit_logs():
    role, user_name = get_current_user_context(request)
    session = SessionLocal()

    logs = session.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(50).all()
    log_list = [l.to_dict() for l in logs]

    session.close()
    return jsonify({"count": len(log_list), "logs": log_list})

if __name__ == '__main__':
    print("[Flask App] Starting MedIntel Healthcare Platform REST Server...")
    app.run(host='0.0.0.0', port=5000, debug=True)
