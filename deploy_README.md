# VideoResearch Deployment & CI/CD

This project uses Flask + SQLAlchemy with AWS RDS (MySQL) in production. We support two deployment modes:

- **Local / dev** (uses SQLite by default)
- **Containerized / prod** (uses MySQL via `DATABASE_URL` on EC2)

We also provide a manual CI/CD “fresh‐start” workflow so you can re‐seed your RDS database on demand without touching data on every code push.

---

## 1. Prerequisites

- Python 3.10+, pip, virtualenv
- Docker & Docker Compose
- AWS CLI & ECR repo (for CI)
- EC2 instance (t3.micro or larger) in same VPC/AZ as your RDS
- RDS MySQL endpoint, credentials

---

## 2. Local Development

1. Clone the repo
   ```bash
   git clone https://github.com/your-org/VideoProject.git
   cd VideoProject/NewPortal
   ```
