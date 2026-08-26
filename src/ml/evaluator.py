import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score,
    f1_score, roc_auc_score, confusion_matrix, roc_curve
)

def evaluate_model_performance(model, X_test, y_test, model_name="Model"):
    """
    Computes comprehensive healthcare ML performance metrics:
    Accuracy, Precision, Recall (Sensitivity), F1-Score, ROC-AUC score,
    Confusion Matrix, and ROC Curve points.
    """
    y_pred = model.predict(X_test)
    
    if hasattr(model, "predict_proba"):
        y_prob = model.predict_proba(X_test)[:, 1]
    elif hasattr(model, "decision_function"):
        y_prob = model.decision_function(X_test)
    else:
        y_prob = y_pred

    acc = float(accuracy_score(y_test, y_pred))
    prec = float(precision_score(y_test, y_pred, zero_division=0))
    rec = float(recall_score(y_test, y_pred, zero_division=0))
    f1 = float(f1_score(y_test, y_pred, zero_division=0))
    
    try:
        auc = float(roc_auc_score(y_test, y_prob))
    except Exception:
        auc = 0.5

    cm = confusion_matrix(y_test, y_pred)
    tn, fp, fn, tp = cm.ravel() if cm.shape == (2, 2) else (0, 0, 0, 0)

    # ROC curve points for dashboard visualization
    try:
        fpr, tpr, thresholds = roc_curve(y_test, y_prob)
        roc_points = [{"fpr": round(float(f), 3), "tpr": round(float(t), 3)} for f, t in zip(fpr[::max(1, len(fpr)//10)], tpr[::max(1, len(tpr)//10)])]
    except Exception:
        roc_points = []

    return {
        "model_name": model_name,
        "accuracy": round(acc, 4),
        "precision": round(prec, 4),
        "recall": round(rec, 4),
        "f1_score": round(f1, 4),
        "roc_auc": round(auc, 4),
        "confusion_matrix": {
            "true_negatives": int(tn),
            "false_positives": int(fp),
            "false_negatives": int(fn),
            "true_positives": int(tp),
            "matrix": cm.tolist()
        },
        "roc_curve": roc_points
    }

def extract_feature_importance(model, feature_names):
    """Extract normalized feature importances or coefficient weights."""
    importances = {}
    if hasattr(model, "feature_importances_"):
        fi = model.feature_importances_
        importances = {name: float(imp) for name, imp in zip(feature_names, fi)}
    elif hasattr(model, "coef_"):
        coef = np.abs(model.coef_[0])
        total = np.sum(coef) + 1e-9
        importances = {name: float(c / total) for name, c in zip(feature_names, coef)}

    # Sort descending
    sorted_imp = dict(sorted(importances.items(), key=lambda item: item[1], reverse=True))
    return sorted_imp
