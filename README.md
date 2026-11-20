# NIRF INSIGHT: INDIA STATE-WISE RANKING DISTRIBUTION DASHBOARD

An institutional ranking intelligence and geospatial analytics platform developed for **ICARE** under the **MITRA Project**. 

NIRF Insight visualizes the geographical distribution, regional concentration, and comparative performance of institutions ranked by the Ministry of Education's National Institutional Ranking Framework (NIRF) across Indian States and Union Territories for **2023**, **2024**, and **2025**.

---

## 🌟 Key Capabilities

* **6 Supported NIRF Categories:**
  1. Overall
  2. Universities
  3. Engineering
  4. Management
  5. Medical
  6. State Public University
* **3 Ranking Editions:** 2023, 2024, 2025 (Default: **2025**).
* **Interactive India Choropleth Map:** Powered by Apache ECharts and Survey of India boundary GeoJSON (`india_states.geojson`) with sequential blue density scale, interactive hover tooltips, and click-to-drill-down.
* **State Information Drawer & Leaderboard:** Instant inspection of state-specific institutional concentrations, percentage of national share, and ranked institution listings.
* **Institution Scorecard Drill-Down:** Detailed inspection modal displaying evaluation parameter scores (Teaching, Learning & Resources [TLR], Research & Professional Practice [RPC], Graduation Outcomes [GO], Outreach & Inclusivity [OI], Peer Perception [PR]) and multi-year historical trajectories.
* **Data Management & Ingestion Portal:** Administrative upload system supporting `.xlsx` and `.csv` files with automatic column detection, validation checks, and audit logging.
* **Dual Database Architecture:** Zero-dependency embedded SQLite for instant local execution, plus production-grade PostgreSQL 13+ DDL schema and complete data seed scripts.
* **Excel & CSV Export:** One-click data download for any category, year, or state-filtered view.

---

## 🚀 Quick Start Guide

### 1. Requirements
* Python 3.10 or higher
* Recommended: Virtual environment (`venv`)

### 2. Setup & Execution
```powershell
# Navigate to project directory
cd "c:\Users\vaibh\Desktop\NIRF MAP"

# Install requirements
python -m pip install -r requirements.txt

# Start backend server
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```
Open **[http://127.0.0.1:8000](http://127.0.0.1:8000)** in any modern web browser.

### 3. Run Automated API Tests
```powershell
python -m backend.tests.test_v1_api
```

---

## 📂 Project Architecture

```text
NIRF MAP/
├── backend/
│   ├── app/
│   │   ├── api/            # FastAPI REST API Endpoints (/api/v1/*)
│   │   ├── core/           # Config & Database Session Management
│   │   ├── models/         # SQLAlchemy Relational Models
│   │   ├── schemas/        # Pydantic Request & Response Schemas
│   │   ├── services/       # Database Seeder & Aggregation Services
│   │   └── main.py         # Application Entry Point & Route Mounting
│   └── tests/              # Automated Test Suite (test_v1_api.py)
├── data/
│   ├── raw/                # Original Excel Datasets (2023, 2024, 2025)
│   ├── processed/          # Cleaned & Processed Data
│   └── templates/          # Standard Ingestion Templates
├── documentation/
│   ├── DATA_INVENTORY.md   # Dataset Inventory & Ingestion Audit
│   ├── DATABASE_SCHEMA.md  # PostgreSQL Relational Schema Documentation
│   ├── API_DOCUMENTATION.md# REST API Endpoints Specification
│   └── DEPLOYMENT_GUIDE.md # Production & Docker Deployment Manual
├── public/
│   └── geojson/            # Canonical India State Boundaries GeoJSON
├── index.html              # Responsive Dashboard User Interface
├── app.js                  # Frontend State & Apache ECharts Controller
├── style.css               # Design System Stylesheet
├── nirf_schema_postgres.sql# Production PostgreSQL DDL Script
├── nirf_seed_postgres.sql  # Production PostgreSQL 1.26MB Seed Script
├── docker-compose.yml      # Multi-container PostgreSQL + API Definition
├── Dockerfile              # Container Build Instructions
├── .env.example            # Environment Configuration Variables
└── requirements.txt        # Python Dependency Manifest
```

---

## 📊 Dataset Ingestion Inventory Summary

| Year | Overall | Universities | Engineering | Management | Medical | State Public University | Total Records |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **2025** | 200 | 200 | 300 | 125 | 50 | 100 | **975** |
| **2024** | 200 | 200 | 300 | 125 | 50 | 100 | **975** |
| **2023** | 200 | 200 | 200 | 125 | 50 | *N/A\** | **777** |
| **Total** | **600** | **600** | **800** | **375** | **150** | **200** | **2,727** |

*\*Note: State Public University was introduced by the Ministry of Education in 2024. For 2023, the platform displays an informative "Data Not Available" badge.*

---

## 🏛️ License & Credits

Managed by **ICARE** under the **MITRA Project**. Ranking datasets sourced from the [National Institutional Ranking Framework (NIRF)](https://www.nirfindia.org), Ministry of Education, Government of India.
