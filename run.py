import os
import sys

from src.database.db import init_db
from src.data.synthetic_generator import seed_database
from src.ml.trainer import train_and_evaluate_all
from src.rag.vector_store import get_vector_store
from src.app import app

def startup():
    print("=" * 70)
    print("🏥 MedIntel AI — Healthcare Analytics & Clinical Intelligence Platform")
    print("=" * 70)

    print("\n[Step 1/3] Initializing Database & Seeding Synthetic Patient Data...")
    seed_database(count=500)

    print("\n[Step 2/3] Retraining ML Risk Prediction Models & Computing Metrics...")
    train_and_evaluate_all()

    print("\n[Step 3/3] Building Local SentenceTransformer + FAISS Clinical Vector Index...")
    store = get_vector_store()
    store.build_index()

    print("\n" + "=" * 70)
    print("🚀 MedIntel AI Server is READY!")
    print("🌐 Dashboard URL: http://127.0.0.1:5000")
    print("=" * 70 + "\n")

    app.run(host='0.0.0.0', port=5000, debug=False)

if __name__ == "__main__":
    startup()
