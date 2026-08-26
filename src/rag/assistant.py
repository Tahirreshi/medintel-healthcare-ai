import os
try:
    import google.generativeai as genai
    HAS_GEMINI_LIB = True
except ImportError:
    HAS_GEMINI_LIB = False

from src.rag.vector_store import get_vector_store
from src.database.db import SessionLocal
from src.database.models import Patient, LabResult, Prediction, MedicalRecord

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

if GEMINI_API_KEY and HAS_GEMINI_LIB:
    genai.configure(api_key=GEMINI_API_KEY)

class ClinicalRAGAssistant:
    def __init__(self):
        self.vector_store = get_vector_store()

    def query_knowledge_base(self, question, top_k=3):
        """Mode 1: General Medical Guideline Q&A based on vector search citations."""
        results = self.vector_store.search(question, top_k=top_k)

        if not results:
            return {
                "answer": "No relevant clinical guidelines found in the knowledge base.",
                "citations": []
            }

        context_str = "\n\n".join([f"[{r['filename']} - {r['section_title']}]\n{r['content']}" for r in results])

        if GEMINI_API_KEY and HAS_GEMINI_LIB:
            try:
                model = genai.GenerativeModel("gemini-1.5-flash")
                prompt = f"""You are a Clinical Decision Support RAG Assistant. 
Answer the user question strictly using the clinical guideline passages provided below. 
Include inline document citations [Document Name] for every claim made. 

Clinical Guideline Passages:
{context_str}

User Question: {question}

Clinical Answer with Citations:"""
                resp = model.generate_content(prompt)
                return {
                    "answer": resp.text,
                    "sources": results
                }
            except Exception as e:
                print(f"[RAG Assistant] Gemini API call error: {e}. Falling back to structured response.")

        # Deterministic Structured RAG Response Fallback
        top_match = results[0]
        answer_text = f"Based on retrieved clinical literature:\n\n{top_match['content']}\n\n"
        if len(results) > 1:
            answer_text += f"Additional Guideline Reference ({results[1]['filename']}):\n{results[1]['section_title']}"

        return {
            "answer": answer_text,
            "sources": results
        }

    def explain_patient_risk(self, patient_id):
        """Mode 2: Synthesize patient vitals, labs, ML predictions, and clinical RAG evidence into a complete explanation."""
        session = SessionLocal()
        patient = session.query(Patient).filter_by(patient_id=patient_id).first()
        if not patient:
            session.close()
            return {"error": f"Patient {patient_id} not found."}

        labs = session.query(LabResult).filter_by(patient_id=patient_id).first()
        record = session.query(MedicalRecord).filter_by(patient_id=patient_id).first()
        preds = session.query(Prediction).filter_by(patient_id=patient_id).all()
        session.close()

        # Extract predictions
        pred_dict = {p.model_name: p.to_dict() for p in preds}

        # Build retrieval query based on patient's key risk factors
        risk_terms = []
        if labs and labs.glucose > 125: risk_terms.append("diabetes elevated glucose hba1c target")
        if patient.blood_pressure_sys >= 135: risk_terms.append("hypertension blood pressure stage target")
        if labs and labs.bmi >= 30: risk_terms.append("obesity lifestyle risk factor")
        if record and record.prior_admissions > 1: risk_terms.append("hospital readmission high risk prior admissions")

        search_query = " ".join(risk_terms) if risk_terms else "clinical guidelines primary disease prevention"
        retrieved_docs = self.vector_store.search(search_query, top_k=3)

        vitals_summary = f"""
PATIENT PROFILE: {patient.name} ({patient.patient_id})
- Age: {patient.age} | Gender: {patient.gender} | BMI: {labs.bmi if labs else 'N/A'} kg/m2
- Blood Pressure: {patient.blood_pressure_sys}/{patient.blood_pressure_dia} mmHg
- Fasting Glucose: {labs.glucose if labs else 'N/A'} mg/dL | HbA1c: {labs.hemoglobin_a1c if labs else 'N/A'}%
- Total Cholesterol: {labs.cholesterol if labs else 'N/A'} mg/dL | LDL: {labs.ldl if labs else 'N/A'} mg/dL
- Hospital Stay: {record.length_of_stay_days if record else 1} days | Prior Admissions: {record.prior_admissions if record else 0}
"""

        preds_summary = ""
        for name, p in pred_dict.items():
            preds_summary += f"- {name}: {p['risk_score']}% ({p['risk_category']})\n  Contributing Factors: {', '.join(p['contributing_factors'] or [])}\n"

        context_str = "\n\n".join([f"[{r['filename']} - {r['section_title']}]\n{r['content']}" for r in retrieved_docs])

        if GEMINI_API_KEY and HAS_GEMINI_LIB:
            try:
                model = genai.GenerativeModel("gemini-1.5-flash")
                prompt = f"""You are a Clinical Decision Support AI. Analyze the following patient profile, ML risk model predictions, and retrieved clinical guidelines.
Provide a clear, evidence-based clinical explanation for the attending physician. Highlight contributing risk factors, correlate with medical guidelines, and include citations.

{vitals_summary}

ML RISK MODEL PREDICTIONS:
{preds_summary}

CLINICAL GUIDELINES RETRIEVED:
{context_str}

Clinical Decision Support Summary with Citations:"""
                resp = model.generate_content(prompt)
                return {
                    "patient_id": patient_id,
                    "explanation": resp.text,
                    "predictions": pred_dict,
                    "sources": retrieved_docs
                }
            except Exception as e:
                print(f"[RAG Assistant] Gemini generation error: {e}. Using deterministic clinical template.")

        # Structured Clinical Explanation Fallback
        explanation_md = f"""### 🏥 AI Clinical Decision Support Analysis

**Patient ID**: #{patient.patient_id} ({patient.name}, Age {patient.age}, {patient.gender})

---

#### 📊 ML Risk Model Summary
"""
        for model_name, p in pred_dict.items():
            badge_color = "🔴" if p['risk_category'] == "HIGH" else ("🟡" if p['risk_category'] == "MODERATE" else "🟢")
            explanation_md += f"- **{model_name}**: {badge_color} **{p['risk_score']}%** ({p['risk_category']})\n"
            if p['contributing_factors']:
                explanation_md += f"  - *Key Factors*: {', '.join(p['contributing_factors'])}\n"

        explanation_md += "\n---\n\n#### 🔬 Clinical Context & Guideline Evidence\n"

        for doc in retrieved_docs:
            explanation_md += f"##### 📖 Citation: [{doc['filename']}]\n> *{doc['section_title']}*\n\n{doc['content']}\n\n"

        explanation_md += """
> [!NOTE]
> *This clinical intelligence summary is generated as an automated prototype decision-support tool. All treatment decisions must be confirmed by a licensed clinician.*
"""

        return {
            "patient_id": patient_id,
            "explanation": explanation_md,
            "predictions": pred_dict,
            "sources": retrieved_docs
        }

if __name__ == "__main__":
    assistant = ClinicalRAGAssistant()
    res = assistant.query_knowledge_base("What is the blood pressure threshold for Stage 2 hypertension?")
    print("KB Query Output:", res["answer"][:200])
