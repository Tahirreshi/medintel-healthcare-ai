import datetime
from functools import wraps
from flask import request, jsonify
from src.database.db import SessionLocal
from src.database.models import AuditLog

ROLES = {
    "Admin": {
        "description": "Full System Administrator",
        "can_view_patients": True,
        "can_anonymize": False,
        "can_run_ml": True,
        "can_upload_docs": True,
        "can_execute_sql": True,
        "can_view_audit": True
    },
    "Clinician": {
        "description": "Attending Physician / Care Manager",
        "can_view_patients": True,
        "can_anonymize": False,
        "can_run_ml": True,
        "can_upload_docs": False,
        "can_execute_sql": False,
        "can_view_audit": False
    },
    "Analyst": {
        "description": "Healthcare Data Science Analyst",
        "can_view_patients": True,
        "can_anonymize": True,
        "can_run_ml": False,
        "can_upload_docs": False,
        "can_execute_sql": True,
        "can_view_audit": False
    }
}

def log_audit_action(user_role, user_name, action, resource, ip_address="127.0.0.1"):
    """Record access or modification events into AuditLog table."""
    try:
        session = SessionLocal()
        audit = AuditLog(
            user_role=user_role,
            user_name=user_name,
            action=action,
            resource_accessed=resource,
            ip_address=ip_address,
            timestamp=datetime.datetime.utcnow()
        )
        session.add(audit)
        session.commit()
        session.close()
    except Exception as e:
        print(f"[Audit Security] Failed to log action: {e}")

def get_current_user_context(req):
    """Extract user role and name from HTTP headers or default to Clinician."""
    role = req.headers.get("X-User-Role", "Clinician")
    name = req.headers.get("X-User-Name", "Dr. Sarah Sterling")
    if role not in ROLES:
        role = "Clinician"
    return role, name
