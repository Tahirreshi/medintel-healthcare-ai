import random
import datetime
import numpy as np
import pandas as pd
from src.database.db import SessionLocal, init_db
from src.database.models import Patient, MedicalRecord, LabResult, Prediction, ClinicalDocument, AuditLog

FIRST_NAMES = ["Eleanor", "Marcus", "Sophia", "David", "Amina", "Chen", "Carlos", "Sarah", "Vikram", "Elena", "James", "Fatima", "Liam", "Zoe", "Alexander", "Maya", "Gabriel", "Olivia", "Tariq", "Chloe", "Daniel", "Amara"]
LAST_NAMES = ["Vance", "Sterling", "Rodriguez", "Chen", "Al-Mansoor", "Sharma", "O'Connor", "Patel", "Novak", "Kowalski", "Kim", "Gupta", "Dubois", "Zhang", "Jackson", "Takahashi", "Moreno", "Nakamura"]

DIAGNOSIS_CODES = [
    ("E11.9", "Type 2 diabetes mellitus without complications"),
    ("I10", "Essential (primary) hypertension"),
    ("I25.10", "Atherosclerotic heart disease of native coronary artery"),
    ("E66.9", "Obesity, unspecified"),
    ("E78.5", "Hyperlipidemia, unspecified"),
    ("J44.9", "Chronic obstructive pulmonary disease, unspecified"),
    ("N18.9", "Chronic kidney disease, unspecified")
]

CHIEF_COMPLAINTS = [
    "Patient reports persistent fatigue, excessive thirst, and frequent urination.",
    "Routine follow-up for blood pressure monitoring and lipid panel review.",
    "Complaining of mild shortness of breath during light physical exertion.",
    "Post-operative evaluation and medication adjustment.",
    "Reporting elevated home fasting blood glucose readings over the past two weeks.",
    "Dizziness and recurring morning headaches over the past 10 days.",
    "Bilateral lower extremity edema and gradual weight gain."
]

DOCTOR_NOTES = [
    "Vitals stable. Counselled patient on low-sodium diet and daily exercise regimen.",
    "Elevated HbA1c observed. Initiated medication review and referred to endocrinology.",
    "Patient exhibits moderate cardiovascular risk factors. Advised lifestyle modifications.",
    "Readmission risk evaluated as moderate due to recent hospital stay and age profile.",
    "Blood pressure poorly controlled on current monotherapy. Added secondary antihypertensive.",
    "Routine screening within normal parameters. Scheduled 6-month clinical follow-up."
]

def generate_synthetic_patients(count=500, seed=42):
    """Generate realistic synthetic clinical patient dataset as a Pandas DataFrame."""
    np.random.seed(seed)
    random.seed(seed)

    data = []
    for i in range(1, count + 1):
        patient_id = f"PAT-{10400 + i}"
        name = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
        age = int(np.clip(np.random.normal(56, 14), 18, 90))
        gender = random.choice(["Male", "Female"])
        
        # Physical stats
        height_cm = round(float(np.random.normal(175 if gender == "Male" else 162, 8)), 1)
        weight_kg = round(float(np.random.normal(83 if gender == "Male" else 71, 15)), 1)
        
        # Calculate BMI
        bmi = round(weight_kg / ((height_cm / 100) ** 2), 1)

        # Correlated vitals & labs
        glucose_base = 85 + (bmi - 22) * 2.3 + (age - 30) * 0.45
        glucose = round(float(np.clip(np.random.normal(glucose_base, 26), 70, 310)), 1)

        # Blood pressure
        bp_sys = int(np.clip(np.random.normal(120 + (age - 40) * 0.5 + (bmi - 25) * 0.85, 14), 95, 195))
        bp_dia = int(np.clip(np.random.normal(78 + (age - 40) * 0.2 + (bmi - 25) * 0.4, 9), 60, 118))

        # Lipids & HbA1c
        hba1c = round(float(np.clip(glucose / 28.7 + np.random.normal(1.2, 0.4), 4.5, 13.8)), 1)
        cholesterol = round(float(np.clip(np.random.normal(190 + (bmi - 24) * 2.1, 36), 130, 350)), 1)
        hdl = round(float(np.clip(np.random.normal(50 if gender == "Female" else 44, 10), 25, 90)), 1)
        ldl = round(max(50.0, cholesterol - hdl - float(np.random.uniform(20, 45))), 1)
        triglycerides = round(float(np.clip(np.random.normal(150 + (bmi - 25) * 4, 52), 60, 480)), 1)
        insulin = round(float(np.clip(np.random.normal(12 + (glucose - 100) * 0.16, 8), 2, 65)), 1)
        creatinine = round(float(np.clip(np.random.normal(0.9 + (age - 40) * 0.008, 0.25), 0.5, 3.8)), 2)

        smoking_status = random.choice(["Never", "Former", "Current"])
        physical_activity = random.choice(["Low", "Moderate", "High"])
        family_history = 1 if (random.random() < 0.35 or glucose > 140) else 0

        # Hospital admission info
        length_of_stay = int(np.random.exponential(scale=3.5)) + 1
        prior_admissions = int(np.random.poisson(lam=1.3 if age > 60 else 0.4))

        # Ground truth risk indicators (for ML model training)
        diabetes_score = (glucose > 125) * 0.35 + (hba1c > 6.4) * 0.35 + (bmi > 30) * 0.15 + (family_history == 1) * 0.15 + (age > 45) * 0.1
        has_diabetes = 1 if (diabetes_score + np.random.normal(0, 0.08) > 0.45) else 0

        cardiac_score = (bp_sys > 140) * 0.3 + (ldl > 130) * 0.25 + (smoking_status == "Current") * 0.2 + (age > 55) * 0.15 + (bmi > 30) * 0.1
        has_cardiac_risk = 1 if (cardiac_score + np.random.normal(0, 0.08) > 0.45) else 0

        readmission_score = (prior_admissions > 1) * 0.4 + (length_of_stay > 5) * 0.25 + (age > 65) * 0.2 + (has_diabetes or has_cardiac_risk) * 0.15
        is_readmitted = 1 if (readmission_score + np.random.normal(0, 0.08) > 0.4) else 0

        data.append({
            "patient_id": patient_id,
            "name": name,
            "age": age,
            "gender": gender,
            "height_cm": height_cm,
            "weight_kg": weight_kg,
            "bmi": bmi,
            "glucose": glucose,
            "blood_pressure_sys": bp_sys,
            "blood_pressure_dia": bp_dia,
            "hba1c": hba1c,
            "cholesterol": cholesterol,
            "hdl": hdl,
            "ldl": ldl,
            "triglycerides": triglycerides,
            "insulin": insulin,
            "creatinine": creatinine,
            "smoking_status": smoking_status,
            "physical_activity": physical_activity,
            "family_history_diabetes": family_history,
            "length_of_stay": length_of_stay,
            "prior_admissions": prior_admissions,
            "target_diabetes": has_diabetes,
            "target_cardiac": has_cardiac_risk,
            "target_readmission": is_readmitted
        })

    return pd.DataFrame(data)

def seed_database(count=500):
    """Seed SQLite database with synthetic clinical patient records."""
    init_db()
    session = SessionLocal()

    # Clear existing data
    session.query(Prediction).delete()
    session.query(LabResult).delete()
    session.query(MedicalRecord).delete()
    session.query(Patient).delete()
    session.query(AuditLog).delete()
    session.commit()

    df = generate_synthetic_patients(count=count)

    for idx, row in df.iterrows():
        patient = Patient(
            patient_id=row['patient_id'],
            name=row['name'],
            age=row['age'],
            gender=row['gender'],
            height_cm=row['height_cm'],
            weight_kg=row['weight_kg'],
            blood_pressure_sys=row['blood_pressure_sys'],
            blood_pressure_dia=row['blood_pressure_dia'],
            smoking_status=row['smoking_status'],
            physical_activity=row['physical_activity'],
            family_history_diabetes=row['family_history_diabetes'],
            created_at=datetime.datetime.utcnow() - datetime.timedelta(days=random.randint(1, 180))
        )
        session.add(patient)

        diag_code, diag_desc = random.choice(DIAGNOSIS_CODES)
        record = MedicalRecord(
            patient_id=row['patient_id'],
            visit_date=patient.created_at,
            diagnosis_code=f"{diag_code} ({diag_desc})",
            chief_complaint=random.choice(CHIEF_COMPLAINTS),
            doctor_notes=random.choice(DOCTOR_NOTES),
            length_of_stay_days=row['length_of_stay'],
            prior_admissions=row['prior_admissions']
        )
        session.add(record)

        lab = LabResult(
            patient_id=row['patient_id'],
            glucose=row['glucose'],
            cholesterol=row['cholesterol'],
            hdl=row['hdl'],
            ldl=row['ldl'],
            triglycerides=row['triglycerides'],
            hemoglobin_a1c=row['hba1c'],
            creatinine=row['creatinine'],
            insulin=row['insulin'],
            bmi=row['bmi'],
            tested_at=patient.created_at
        )
        session.add(lab)

    session.add(AuditLog(
        user_role="Admin",
        user_name="System Initializer",
        action="DATASET_SEED",
        resource_accessed=f"patients_table ({count} records seeded)"
    ))

    session.commit()
    session.close()
    print(f"[Synthetic Generator] Database populated with {count} clinical patient records!")

if __name__ == "__main__":
    seed_database(500)
