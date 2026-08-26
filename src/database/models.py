import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class Patient(Base):
    __tablename__ = 'patients'

    patient_id = Column(String(50), primary_key=True)
    name = Column(String(100), nullable=False)
    age = Column(Integer, nullable=False)
    gender = Column(String(20), nullable=False)
    height_cm = Column(Float, nullable=False)
    weight_kg = Column(Float, nullable=False)
    blood_pressure_sys = Column(Integer, nullable=False)
    blood_pressure_dia = Column(Integer, nullable=False)
    smoking_status = Column(String(30), nullable=False, default="Never")
    physical_activity = Column(String(30), nullable=False, default="Moderate")
    family_history_diabetes = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    medical_records = relationship("MedicalRecord", back_populates="patient", cascade="all, delete-orphan")
    lab_results = relationship("LabResult", back_populates="patient", cascade="all, delete-orphan")
    predictions = relationship("Prediction", back_populates="patient", cascade="all, delete-orphan")

    def to_dict(self, anonymize=False):
        return {
            "patient_id": self.patient_id,
            "name": "ANONYMIZED PATIENT" if anonymize else self.name,
            "age": self.age,
            "gender": self.gender,
            "height_cm": self.height_cm,
            "weight_kg": self.weight_kg,
            "blood_pressure_sys": self.blood_pressure_sys,
            "blood_pressure_dia": self.blood_pressure_dia,
            "blood_pressure_formatted": f"{self.blood_pressure_sys}/{self.blood_pressure_dia}",
            "smoking_status": self.smoking_status,
            "physical_activity": self.physical_activity,
            "family_history_diabetes": bool(self.family_history_diabetes),
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

class MedicalRecord(Base):
    __tablename__ = 'medical_records'

    record_id = Column(Integer, primary_key=True, autoincrement=True)
    patient_id = Column(String(50), ForeignKey('patients.patient_id'), nullable=False)
    visit_date = Column(DateTime, default=datetime.datetime.utcnow)
    diagnosis_code = Column(String(50), nullable=False)
    chief_complaint = Column(Text, nullable=True)
    doctor_notes = Column(Text, nullable=True)
    length_of_stay_days = Column(Integer, default=1)
    prior_admissions = Column(Integer, default=0)

    patient = relationship("Patient", back_populates="medical_records")

    def to_dict(self):
        return {
            "record_id": self.record_id,
            "patient_id": self.patient_id,
            "visit_date": self.visit_date.isoformat() if self.visit_date else None,
            "diagnosis_code": self.diagnosis_code,
            "chief_complaint": self.chief_complaint,
            "doctor_notes": self.doctor_notes,
            "length_of_stay_days": self.length_of_stay_days,
            "prior_admissions": self.prior_admissions
        }

class LabResult(Base):
    __tablename__ = 'lab_results'

    result_id = Column(Integer, primary_key=True, autoincrement=True)
    patient_id = Column(String(50), ForeignKey('patients.patient_id'), nullable=False)
    glucose = Column(Float, nullable=False) # mg/dL
    cholesterol = Column(Float, nullable=False) # mg/dL
    hdl = Column(Float, nullable=False)
    ldl = Column(Float, nullable=False)
    triglycerides = Column(Float, nullable=False)
    hemoglobin_a1c = Column(Float, nullable=False) # %
    creatinine = Column(Float, nullable=False) # mg/dL
    insulin = Column(Float, nullable=False) # uIU/mL
    bmi = Column(Float, nullable=False)
    tested_at = Column(DateTime, default=datetime.datetime.utcnow)

    patient = relationship("Patient", back_populates="lab_results")

    def to_dict(self):
        return {
            "result_id": self.result_id,
            "patient_id": self.patient_id,
            "glucose": self.glucose,
            "cholesterol": self.cholesterol,
            "hdl": self.hdl,
            "ldl": self.ldl,
            "triglycerides": self.triglycerides,
            "hemoglobin_a1c": self.hemoglobin_a1c,
            "creatinine": self.creatinine,
            "insulin": self.insulin,
            "bmi": self.bmi,
            "tested_at": self.tested_at.isoformat() if self.tested_at else None
        }

class Prediction(Base):
    __tablename__ = 'predictions'

    prediction_id = Column(Integer, primary_key=True, autoincrement=True)
    patient_id = Column(String(50), ForeignKey('patients.patient_id'), nullable=False)
    model_name = Column(String(50), nullable=False) # e.g., 'diabetes_risk', 'cardiac_risk', 'readmission_risk'
    risk_score = Column(Float, nullable=False) # 0.0 to 1.0
    risk_category = Column(String(20), nullable=False) # 'LOW', 'MODERATE', 'HIGH'
    contributing_factors = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    patient = relationship("Patient", back_populates="predictions")

    def to_dict(self):
        return {
            "prediction_id": self.prediction_id,
            "patient_id": self.patient_id,
            "model_name": self.model_name,
            "risk_score": round(self.risk_score * 100, 1), # percentage
            "raw_score": round(self.risk_score, 4),
            "risk_category": self.risk_category,
            "contributing_factors": self.contributing_factors,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

class ClinicalDocument(Base):
    __tablename__ = 'documents'

    document_id = Column(Integer, primary_key=True, autoincrement=True)
    filename = Column(String(255), nullable=False)
    document_type = Column(String(50), nullable=False) # Guideline, Protocol, Clinical Paper
    file_size_bytes = Column(Integer, default=0)
    chunk_count = Column(Integer, default=0)
    uploaded_at = Column(DateTime, default=datetime.datetime.utcnow)

    def to_dict(self):
        return {
            "document_id": self.document_id,
            "filename": self.filename,
            "document_type": self.document_type,
            "file_size_bytes": self.file_size_bytes,
            "chunk_count": self.chunk_count,
            "uploaded_at": self.uploaded_at.isoformat() if self.uploaded_at else None
        }

class AuditLog(Base):
    __tablename__ = 'audit_logs'

    log_id = Column(Integer, primary_key=True, autoincrement=True)
    user_role = Column(String(50), nullable=False) # Admin, Clinician, Analyst
    user_name = Column(String(100), nullable=False)
    action = Column(String(100), nullable=False)
    resource_accessed = Column(String(255), nullable=False)
    ip_address = Column(String(50), default="127.0.0.1")
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

    def to_dict(self):
        return {
            "log_id": self.log_id,
            "user_role": self.user_role,
            "user_name": self.user_name,
            "action": self.action,
            "resource_accessed": self.resource_accessed,
            "ip_address": self.ip_address,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
        }
