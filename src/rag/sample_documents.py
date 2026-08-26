import os
from src.database.db import SessionLocal, init_db
from src.database.models import ClinicalDocument

SAMPLE_CLINICAL_DOCUMENTS = [
    {
        "filename": "ADA_Diabetes_Clinical_Guidelines_2024.pdf",
        "document_type": "Clinical Guideline",
        "content": """
AMERICAN DIABETES ASSOCIATION (ADA) STANDARDS OF CARE IN DIABETES 2024

SECTION 1: DIAGNOSTIC CRITERIA & RISK ASSESSMENT
- Fasting Plasma Glucose (FPG) >= 126 mg/dL (7.0 mmol/L) indicates diabetes. Normal is < 100 mg/dL. Impaired Fasting Glucose (Prediabetes) is 100 - 125 mg/dL.
- Hemoglobin A1c (HbA1c) >= 6.5% is diagnostic of Diabetes Mellitus. Target A1c for most non-pregnant adults is < 7.0%.
- Prediabetes HbA1c threshold: 5.7% to 6.4%.
- Body Mass Index (BMI) >= 25 kg/m2 (or >= 23 kg/m2 in Asian Americans) combined with risk factors (family history, age > 45, physical inactivity) warrants annual screening.

SECTION 2: GLYCOSYLATED HEMOGLOBIN & CLINICAL INTERVENTION
- Lifestyle modifications including 150 minutes/week of moderate-intensity aerobic physical activity and 5-10% body weight loss reduce Type 2 Diabetes conversion by 58%.
- First-line pharmacotherapy: Metformin combined with comprehensive lifestyle management.
- If HbA1c remains > 1.5% above target at diagnosis, consider dual combination therapy (Metformin + SGLT2 inhibitor or GLP-1 receptor agonist).
- Elevated fasting glucose and high BMI correlate strongly with microvascular and macrovascular complications including diabetic nephropathy and retinopathy.
"""
    },
    {
        "filename": "JNC8_Hypertension_Management_Guidelines.pdf",
        "document_type": "Clinical Guideline",
        "content": """
JNC-8 EVIDENCE-BASED GUIDELINES FOR MANAGEMENT OF HIGH BLOOD PRESSURE

SECTION 1: BLOOD PRESSURE CLASSIFICATION & THRESHOLDS
- Normal Blood Pressure: Systolic < 120 mmHg and Diastolic < 80 mmHg.
- Elevated Blood Pressure: Systolic 120-129 mmHg and Diastolic < 80 mmHg.
- Stage 1 Hypertension: Systolic 130-139 mmHg OR Diastolic 80-89 mmHg.
- Stage 2 Hypertension: Systolic >= 140 mmHg OR Diastolic >= 90 mmHg.
- Hypertensive Crisis: Systolic > 180 mmHg and/or Diastolic > 120 mmHg.

SECTION 2: TREATMENT GOALS & PHARMACOTHERAPY
- In the general population aged >= 60 years, initiate pharmacotherapy at Systolic >= 150 mmHg or Diastolic >= 90 mmHg and treat to target < 150/90 mmHg.
- In patients aged < 60 years, or those with Diabetes or Chronic Kidney Disease (CKD), target BP is < 140/90 mmHg.
- Initial therapy options: Thiazide-type diuretic, Calcium Channel Blocker (CCB), ACE Inhibitor (ACEi), or Angiotensin Receptor Blocker (ARB).
- Non-pharmacologic interventions: Dietary Sodium restriction (< 2,000 mg/day), DASH diet rich in potassium and fiber, weight management, and moderation of alcohol intake.
"""
    },
    {
        "filename": "Hospital_Readmission_Reduction_Protocol.pdf",
        "document_type": "Hospital Protocol",
        "content": """
CMS HOSPITAL READMISSIONS REDUCTION PROGRAM (HRRP) CLINICAL PROTOCOL

SECTION 1: HIGH-RISK READMISSION FACTORS
- 30-Day Hospital Readmission is significantly predicted by:
  1. Multiple prior hospital admissions within the preceding 12 months (Count > 1).
  2. Length of Initial Inpatient Stay > 4 days.
  3. Multimorbidity (Polypharmacy >= 5 active medications, concurrent Heart Failure, COPD, or Diabetes).
  4. Advanced Age (> 65 years) combined with functional impairment.
  5. Impaired renal function (Serum Creatinine > 1.3 mg/dL).

SECTION 2: DISCHARGE INTERVENTIONS & CARE TRANSITION
- Mandatory post-discharge follow-up appointment scheduled within 7 to 14 days of discharge.
- Comprehensive Medication Reconciliation completed prior to patient departure.
- Structured patient education on red flag symptoms requiring emergency contact.
- Telephonic outreach by care coordinator within 48-72 hours post-discharge to verify medication adherence and clinical stability.
"""
    },
    {
        "filename": "ACC_AHA_Cardiovascular_Risk_Prevention.pdf",
        "document_type": "Clinical Guideline",
        "content": """
ACC/AHA GUIDELINE ON THE PRIMARY PREVENTION OF CARDIOVASCULAR DISEASE

SECTION 1: LIPID MANAGEMENT & ATHEROSCLEROTIC CARDIOVASCULAR DISEASE (ASCVD)
- Primary prevention targets: LDL Cholesterol < 100 mg/dL for moderate risk, and < 70 mg/dL for high risk patients.
- Elevated LDL Cholesterol (>= 190 mg/dL) is a primary indication for high-intensity Statin therapy regardless of 10-year ASCVD score.
- Hypertriglyceridemia (> 150 mg/dL) combined with low HDL (< 40 mg/dL in men, < 50 mg/dL in women) increases atherogenic risk.

SECTION 2: LIFESTYLE & SMOKING CESSATION
- Tobacco smoking is an independent primary risk factor for myocardial infarction and stroke. Absolute smoking cessation is required.
- Maintain BMI between 18.5 and 24.9 kg/m2. Obesity (BMI >= 30) correlates with systemic inflammation and endothelial dysfunction.
- Regular moderate physical exercise (150 min/week) improves lipid profiles and blood pressure control.
"""
    }
]

def seed_clinical_documents():
    """Seed SQLite documents table with metadata."""
    init_db()
    session = SessionLocal()

    # Clear old documents metadata
    session.query(ClinicalDocument).delete()
    session.commit()

    docs_dir = os.path.join(os.path.dirname(__file__), "..", "..", "data", "clinical_literature")
    os.makedirs(docs_dir, exist_ok=True)

    for doc in SAMPLE_CLINICAL_DOCUMENTS:
        # Write text file to disk
        file_path = os.path.join(docs_dir, doc["filename"].replace(".pdf", ".txt"))
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(doc["content"])

        c_doc = ClinicalDocument(
            filename=doc["filename"],
            document_type=doc["document_type"],
            file_size_bytes=len(doc["content"]),
            chunk_count=len(doc["content"].split("\n\n"))
        )
        session.add(c_doc)

    session.commit()
    session.close()
    print(f"[RAG Seed] Successfully seeded {len(SAMPLE_CLINICAL_DOCUMENTS)} clinical guideline documents!")

if __name__ == "__main__":
    seed_clinical_documents()
