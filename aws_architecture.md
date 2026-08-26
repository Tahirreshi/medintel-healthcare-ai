# AWS Enterprise Cloud Architecture: MedIntel AI Platform

This document outlines the production-grade AWS cloud deployment strategy for the **MedIntel AI — Healthcare Analytics & Clinical Intelligence Platform**.

```
                  ┌─────────────────────────────────────────────────────────┐
                  │                      AWS Cloud                          │
                  │                                                         │
  ┌───────────┐   │   ┌──────────────┐      ┌──────────────┐   ┌─────────┐  │
  │ Clinician │───┼──▶│ AWS ALB / WAF│─────▶│  AWS ECS     │──▶│ AWS RDS │  │
  │ / Analyst │   │   └──────────────┘      │  (Fargate)   │   │ (Postgre│  │
  └───────────┘   │                         └──────┬───────┘   │  SQL)   │  │
                  │                                │           └─────────┘  │
                  │                                ▼                        │
                  │                         ┌──────────────┐                │
                  │                         │   AWS S3     │                │
                  │                         │  (Docs/ML)   │                │
                  │                         └──────────────┘                │
                  └─────────────────────────────────────────────────────────┘
```

---

## 1. AWS S3 (Simple Storage Service)
- **Bucket 1**: `medintel-clinical-documents-prod`
  - Stores unstructured clinical PDFs, ADA/JNC-8 guidelines, and medical literature.
  - Server-Side Encryption (SSE-KMS) enforced for HIPAA compliance.
- **Bucket 2**: `medintel-ml-artifacts-prod`
  - Stores serialized trained ML models (`joblib`), FAISS vector index files (`faiss_index.bin`), and evaluation metrics logs.

---

## 2. AWS RDS (Relational Database Service)
- **Engine**: PostgreSQL 15.x Multi-AZ deployment.
- **Tables**: `patients`, `medical_records`, `lab_results`, `predictions`, `documents`, `audit_logs`.
- **Database Security**:
  - Private subnet isolation (no public IP exposure).
  - Encrypted at rest via AWS KMS.
  - Automated snapshot backups with 30-day retention.

---

## 3. AWS ECR (Elastic Container Registry) & ECS (Elastic Container Service)
- **ECR Registry**: Container registry hosting tagged Docker images (`medintel-app:latest`, `medintel-app:v2.4.0`).
- **ECS Fargate Cluster**:
  - Serverless container orchestration with auto-scaling based on CPU (>70%) and Memory (>80%).
  - Tasks distributed across 2 Availability Zones (AZs) behind an Application Load Balancer (ALB).

---

## 4. AWS IAM & Role-Based Security Governance
- **ECS Task Execution Role**: Grants minimal permission to fetch secrets from AWS Secrets Manager (`GEMINI_API_KEY`, DB passwords) and write to CloudWatch.
- **Data Anonymization Policy**: Enforces strict separation between clinical user roles (`Clinician` views full PHI, `Analyst` accesses de-identified/anonymized data views).

---

## 5. AWS CloudWatch & Observability
- **Log Groups**: `/ecs/medintel-platform` logs application stack traces and HTTP access metrics.
- **HIPAA Audit Alarms**: CloudWatch Metric Filters trigger SNS notifications upon unauthorized data access attempts or failed login spikes.
