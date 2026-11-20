# NIRF INSIGHT: PRODUCTION DEPLOYMENT & SETUP GUIDE

**Project:** NIRF Insight – India State-wise Ranking Distribution Dashboard  
**Platform:** FastAPI Backend + Apache ECharts / Tailwind CSS Frontend + PostgreSQL Database  

---

## 1. Local Development Setup (Quick Start)

### Prerequisites:
* Python 3.10+
* Windows, macOS, or Linux

### Installation Steps:
```powershell
# 1. Clone or navigate to the project directory
cd "c:\Users\vaibh\Desktop\NIRF MAP"

# 2. Install required Python packages
python -m pip install -r requirements.txt

# 3. Seed the relational database (if not already seeded)
python -m backend.app.services.db_seeder

# 4. Start the development server
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

Open your browser to: **`http://127.0.0.1:8000`**

---

## 2. PostgreSQL Production Deployment

### Option A: Running with Docker Compose
The project includes a ready-to-use `docker-compose.yml` that automatically provisions PostgreSQL 15 and initializes the schema and seed data:

```bash
# Start PostgreSQL and API service
docker compose up -d

# Check service logs
docker compose logs -f api
```

The database will be initialized automatically from `nirf_schema_postgres.sql` and `nirf_seed_postgres.sql`.

### Option B: Connecting to an External Managed PostgreSQL Instance
1. Set the `DATABASE_URL` environment variable:
```bash
export DATABASE_URL="postgresql://nirf_admin:SecretPassword@your-db-host.rds.amazonaws.com:5432/nirf_production"
```
2. Initialize schema:
```bash
psql $DATABASE_URL -f nirf_schema_postgres.sql
psql $DATABASE_URL -f nirf_seed_postgres.sql
```
3. Start the application:
```bash
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```

---

## 3. Running Automated Tests
Run the comprehensive test suite verifying all 10 V1 REST API endpoints:
```powershell
python -m backend.tests.test_v1_api
```
Expected output:
```text
ALL V1 ENDPOINTS TESTED AND VERIFIED SUCCESSFULLY!
```
