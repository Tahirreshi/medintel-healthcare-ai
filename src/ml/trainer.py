import os
import joblib
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier

from src.data.synthetic_generator import generate_synthetic_patients
from src.ml.evaluator import evaluate_model_performance, extract_feature_importance
from src.database.db import SessionLocal, init_db
from src.database.models import Patient, LabResult, MedicalRecord, Prediction

MODELS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "models")
os.makedirs(MODELS_DIR, exist_ok=True)

FEATURE_COLS_DIABETES = [
    'age', 'bmi', 'glucose', 'blood_pressure_sys', 'blood_pressure_dia',
    'hba1c', 'triglycerides', 'insulin', 'family_history_diabetes'
]

FEATURE_COLS_CARDIAC = [
    'age', 'bmi', 'blood_pressure_sys', 'blood_pressure_dia',
    'cholesterol', 'hdl', 'ldl', 'triglycerides'
]

FEATURE_COLS_READMISSION = [
    'age', 'bmi', 'blood_pressure_sys', 'glucose',
    'length_of_stay', 'prior_admissions', 'creatinine'
]

def train_and_evaluate_all():
    """Train multiple ML models, compare performance metrics, and persist predictions to DB."""
    print("[ML Trainer] Generating synthetic clinical dataset for training...", flush=True)
    df = generate_synthetic_patients(count=800, seed=42)

    results = {}

    # --- 1. DIABETES RISK MODELS ---
    print("[ML Trainer] Training Diabetes Risk Models (Logistic Regression, Random Forest, XGBoost)...", flush=True)
    X_diab = df[FEATURE_COLS_DIABETES]
    y_diab = df['target_diabetes']
    X_tr_d, X_te_d, y_tr_d, y_te_d = train_test_split(X_diab, y_diab, test_size=0.25, random_state=42, stratify=y_diab)

    models_diab = {
        "Logistic Regression": LogisticRegression(max_iter=1000, random_state=42),
        "Random Forest": RandomForestClassifier(n_estimators=60, max_depth=5, random_state=42),
        "XGBoost": XGBClassifier(n_estimators=60, max_depth=4, learning_rate=0.08, eval_metric="logloss", random_state=42)
    }

    results["diabetes_risk"] = {}
    best_diab_model = None
    best_diab_auc = 0.0

    for name, m in models_diab.items():
        m.fit(X_tr_d, y_tr_d)
        metrics = evaluate_model_performance(m, X_te_d, y_te_d, model_name=name)
        feat_imp = extract_feature_importance(m, FEATURE_COLS_DIABETES)
        metrics["feature_importance"] = feat_imp
        results["diabetes_risk"][name] = metrics

        if metrics["roc_auc"] > best_diab_auc:
            best_diab_auc = metrics["roc_auc"]
            best_diab_model = m

    joblib.dump(best_diab_model, os.path.join(MODELS_DIR, "diabetes_risk_model.joblib"))

    # --- 2. CARDIAC RISK MODELS ---
    print("[ML Trainer] Training Cardiac Risk Models...", flush=True)
    X_card = df[FEATURE_COLS_CARDIAC]
    y_card = df['target_cardiac']
    X_tr_c, X_te_c, y_tr_c, y_te_c = train_test_split(X_card, y_card, test_size=0.25, random_state=42, stratify=y_card)

    models_card = {
        "Logistic Regression": LogisticRegression(max_iter=1000, random_state=42),
        "Random Forest": RandomForestClassifier(n_estimators=60, max_depth=5, random_state=42),
        "XGBoost": XGBClassifier(n_estimators=60, max_depth=4, learning_rate=0.08, eval_metric="logloss", random_state=42)
    }

    results["cardiac_risk"] = {}
    best_card_model = None
    best_card_auc = 0.0

    for name, m in models_card.items():
        m.fit(X_tr_c, y_tr_c)
        metrics = evaluate_model_performance(m, X_te_c, y_te_c, model_name=name)
        feat_imp = extract_feature_importance(m, FEATURE_COLS_CARDIAC)
        metrics["feature_importance"] = feat_imp
        results["cardiac_risk"][name] = metrics

        if metrics["roc_auc"] > best_card_auc:
            best_card_auc = metrics["roc_auc"]
            best_card_model = m

    joblib.dump(best_card_model, os.path.join(MODELS_DIR, "cardiac_risk_model.joblib"))

    # --- 3. 30-DAY HOSPITAL READMISSION MODELS ---
    print("[ML Trainer] Training Readmission Risk Models...", flush=True)
    X_read = df[FEATURE_COLS_READMISSION]
    y_read = df['target_readmission']
    X_tr_r, X_te_r, y_tr_r, y_te_r = train_test_split(X_read, y_read, test_size=0.25, random_state=42, stratify=y_read)

    models_read = {
        "Random Forest": RandomForestClassifier(n_estimators=60, max_depth=5, random_state=42),
        "XGBoost": XGBClassifier(n_estimators=60, max_depth=4, learning_rate=0.08, eval_metric="logloss", random_state=42)
    }

    results["readmission_risk"] = {}
    best_read_model = None
    best_read_auc = 0.0

    for name, m in models_read.items():
        m.fit(X_tr_r, y_tr_r)
        metrics = evaluate_model_performance(m, X_te_r, y_te_r, model_name=name)
        feat_imp = extract_feature_importance(m, FEATURE_COLS_READMISSION)
        metrics["feature_importance"] = feat_imp
        results["readmission_risk"][name] = metrics

        if metrics["roc_auc"] > best_read_auc:
            best_read_auc = metrics["roc_auc"]
            best_read_model = m

    joblib.dump(best_read_model, os.path.join(MODELS_DIR, "readmission_risk_model.joblib"))
    joblib.dump(results, os.path.join(MODELS_DIR, "evaluation_summary.joblib"))

    print("[ML Trainer] All ML models successfully trained, evaluated, and saved!", flush=True)
    populate_db_predictions(best_diab_model, best_card_model, best_read_model)
    return results

def populate_db_predictions(diab_model, card_model, read_model):
    """Run inferences on active database patients and save risk scores into predictions table."""
    init_db()
    session = SessionLocal()

    session.query(Prediction).delete()
    session.commit()

    patients = session.query(Patient).all()
    count = 0

    for p in patients:
        lab = session.query(LabResult).filter_by(patient_id=p.patient_id).first()
        rec = session.query(MedicalRecord).filter_by(patient_id=p.patient_id).first()

        if not lab or not rec:
            continue

        input_diab = pd.DataFrame([{
            'age': p.age, 'bmi': lab.bmi, 'glucose': lab.glucose,
            'blood_pressure_sys': p.blood_pressure_sys, 'blood_pressure_dia': p.blood_pressure_dia,
            'hba1c': lab.hemoglobin_a1c, 'triglycerides': lab.triglycerides,
            'insulin': lab.insulin, 'family_history_diabetes': p.family_history_diabetes
        }])
        prob_diab = float(diab_model.predict_proba(input_diab)[0, 1])
        cat_diab = "HIGH" if prob_diab >= 0.65 else ("MODERATE" if prob_diab >= 0.35 else "LOW")
        factors_diab = []
        if lab.glucose > 125: factors_diab.append("Elevated Glucose (>125 mg/dL)")
        if lab.bmi >= 30: factors_diab.append("High BMI (Obesity)")
        if p.blood_pressure_sys >= 135: factors_diab.append("Elevated Blood Pressure")
        if p.family_history_diabetes: factors_diab.append("Family History of Diabetes")

        session.add(Prediction(
            patient_id=p.patient_id, model_name="Diabetes Risk",
            risk_score=prob_diab, risk_category=cat_diab, contributing_factors=factors_diab
        ))

        input_card = pd.DataFrame([{
            'age': p.age, 'bmi': lab.bmi, 'blood_pressure_sys': p.blood_pressure_sys,
            'blood_pressure_dia': p.blood_pressure_dia, 'cholesterol': lab.cholesterol,
            'hdl': lab.hdl, 'ldl': lab.ldl, 'triglycerides': lab.triglycerides
        }])
        prob_card = float(card_model.predict_proba(input_card)[0, 1])
        cat_card = "HIGH" if prob_card >= 0.65 else ("MODERATE" if prob_card >= 0.35 else "LOW")
        factors_card = []
        if p.blood_pressure_sys >= 140: factors_card.append("Stage 1/2 Hypertension")
        if lab.ldl >= 130: factors_card.append("Elevated LDL Cholesterol")
        if p.smoking_status == "Current": factors_card.append("Active Tobacco Smoke Exposure")
        if p.age > 55: factors_card.append("Age-Related Vascular Stiffness")

        session.add(Prediction(
            patient_id=p.patient_id, model_name="Cardiac Risk",
            risk_score=prob_card, risk_category=cat_card, contributing_factors=factors_card
        ))

        input_read = pd.DataFrame([{
            'age': p.age, 'bmi': lab.bmi, 'blood_pressure_sys': p.blood_pressure_sys,
            'glucose': lab.glucose, 'length_of_stay': rec.length_of_stay_days,
            'prior_admissions': rec.prior_admissions, 'creatinine': lab.creatinine
        }])
        prob_read = float(read_model.predict_proba(input_read)[0, 1])
        cat_read = "HIGH" if prob_read >= 0.60 else ("MODERATE" if prob_read >= 0.30 else "LOW")
        factors_read = []
        if rec.prior_admissions > 1: factors_read.append(f"Multiple Prior Admissions ({rec.prior_admissions})")
        if rec.length_of_stay_days > 4: factors_read.append(f"Extended Hospital Stay ({rec.length_of_stay_days} days)")
        if p.age > 65: factors_read.append("Geriatric Readmission Vulnerability")
        if lab.creatinine > 1.3: factors_read.append("Impaired Renal Function")

        session.add(Prediction(
            patient_id=p.patient_id, model_name="Readmission Risk",
            risk_score=prob_read, risk_category=cat_read, contributing_factors=factors_read
        ))
        count += 1

    session.commit()
    session.close()
    print(f"[ML Trainer] Generated {count * 3} prediction records in SQLite DB!", flush=True)

if __name__ == "__main__":
    train_and_evaluate_all()
