# NIRF Insight – India State-wise Distribution Dashboard
## Technical Specification & Architecture Manual

**Version:** 2.0.0  
**Ranking Editions Supported:** 2023, 2024, 2025  
**Default Year:** 2025  
**Supported Categories (6):** Overall, Universities, Engineering, Management, Medical, State Public University  

---

### 1. Executive Summary

The **NIRF Insight India State-wise Distribution Dashboard** is an enterprise-grade full-stack data analytics platform designed to analyze, visualize, and benchmark higher education institutional performance across all Indian States and Union Territories.

The platform provides a dual-database architecture (SQLite for instant zero-dependency execution + full PostgreSQL 13+ production DDL and data seed scripts), an interactive India choropleth map powered by Leaflet.js and Survey of India standard boundaries, state-wise leaderboards, parameter score breakdown analytics (TLR, RPC, GO, OI, PR), multi-year rank trajectory tracking, and instant Excel/CSV data exports.

---

### 2. File & Directory Structure

```text
NIRF MAP/
├── app.py                         # Production FastAPI Backend & REST API Server
├── index.html                     # Responsive Frontend Dashboard UI
├── app.js                         # Dynamic Frontend Controller & Reactive State Manager
├── style.css                      # Custom Theme, Tooltip, and Table Styling
├── india_states.geojson           # Canonical 36 States/UTs GeoJSON Boundary File
├── pipeline.py                    # Multi-Year Ingestion, Validation & Harmonization Pipeline
├── test_app.py                    # Automated Backend API Test Suite
├── nirf_insights.db               # Embedded Normalized SQLite Database
├── nirf_schema_postgres.sql       # Production PostgreSQL DDL Schema Specification
├── nirf_seed_postgres.sql         # Production PostgreSQL Data Insert & Seed Script (1.26 MB)
├── DATA_VALIDATION_REPORT.md      # Comprehensive Multi-Year Audit & Validation Log
├── NIRF_India_Rankings_2025.xlsx  # Multi-sheet Excel Dataset (975 records)
├── NIRF_India_Rankings_2024.xlsx  # Multi-sheet Excel Dataset (975 records)
└── NIRF_India_Rankings_2023.xlsx  # Multi-sheet Excel Dataset (777 records)
```

---

### 3. Database Architecture & Schema Specification

The platform utilizes a normalized relational database schema designed for multi-year institutional ranking analytics:

#### Core Tables:
1. `categories`: Database-driven category definitions (`code`, `name`, `display_order`, `description`, `icon`). Allows adding new NIRF categories dynamically without modifying application code.
2. `ranking_years`: Available ranking cycles (`year`, `is_default`, `is_available`).
3. `category_coverage`: Tracks institutional coverage and availability matrix per category-year pair. Identifies categories not yet introduced (e.g. State Public University in 2023).
4. `institutions`: Master institutional registry (`institute_id`, `canonical_name`, `city`, `state_canonical`).
5. `rankings`: Fact table storing ranking instances (`year`, `category_code`, `rank_num`, `rank_display`, `is_rank_band`, `is_tied`, `score`, `tlr`, `rpc`, `go`, `oi`, `perception`, `report_pdf`, `source_file`, `validation_status`).
6. `validation_logs`: Audit log storing anomalies, state harmonizations, ties preserved, and data actions.

---

### 4. REST API Endpoint Reference

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/` | Serves the interactive dashboard user interface |
| `GET` | `/api/categories` | Returns all database-driven categories |
| `GET` | `/api/years` | Returns available ranking years (2023–2025) and default flag |
| `GET` | `/api/coverage` | Returns availability matrix and institution count across all years |
| `GET` | `/api/stats?year=2025&category=overall` | KPI cards (total ranked, states count, leading state, top institute) |
| `GET` | `/api/map-data?year=2025&category=overall` | State-wise institution count & top institution for choropleth |
| `GET` | `/api/leaderboard?year=2025&category=overall` | Ranked table of states with percentage share & leading institutions |
| `GET` | `/api/institutions?year=...&category=...` | Filterable and searchable institution directory |
| `GET` | `/api/institution-detail?name=...` | Multi-year historical score trajectory and parameter cards |
| `GET` | `/api/charts/top-parameters` | Top 5 institutions parameter breakdown for comparison chart |
| `GET` | `/api/validation-report` | Summary of data integrity checks and audit issues |
| `GET` | `/api/export?format=csv&year=...` | Instant download of filtered dataset as CSV or Excel |
| `GET` | `/india_states.geojson` | Serves boundary polygon data for India choropleth map |

---

### 5. Running the Application

To start the dashboard server:
```powershell
python -m uvicorn app:app --host 127.0.0.1 --port 8000
```
Open **[http://127.0.0.1:8000](http://127.0.0.1:8000)** in any web browser.

To run the automated test suite:
```powershell
python test_app.py
```
