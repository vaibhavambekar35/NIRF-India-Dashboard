# NIRF INSIGHT: DATA IMPORT & VALIDATION REPORT

**Generated At:** 2026-11-17 15:25:00  
**Target Database:** PostgreSQL 13+ / SQLite 3  
**Audited Ranking Years:** 2023, 2024, 2025  
**Audited Categories:** 6 Categories (Overall, Universities, Engineering, Management, Medical, State Public University)

---

## 1. Executive Ingestion Summary

* **Total Ranking Records Ingested:** 2,727
* **Unique Institutions Identified:** 720
* **Validation Issues Logged:** 125
  * **Critical:** 0
  * **Warnings:** 0
  * **Informational / Normalization:** 125

---

## 2. Category & Year Coverage Matrix

| Year | Category | Status | Top Ranks (Scores) | Rank Bands | Total Records | Leading Institution (#1) | Top Score |
| :--- | :--- | :---: | :---: | :---: | :---: | :--- | :---: |
| 2025 | **Engineering** | ✅ Available | 100 | 200 | **300** | Indian Institute of Technology Madras | 88.72 |
| 2025 | **Management** | ✅ Available | 100 | 25 | **125** | Indian Institute of Management Ahmedabad | 83.29 |
| 2025 | **Medical** | ✅ Available | 50 | 0 | **50** | All India Institute of Medical Sciences, Delhi | 91.80 |
| 2025 | **Overall** | ✅ Available | 100 | 100 | **200** | Indian Institute of Technology Madras | 87.31 |
| 2025 | **State Public University** | ✅ Available | 50 | 50 | **100** | Jadavpur University | 76.08 |
| 2025 | **Universities** | ✅ Available | 100 | 100 | **200** | Indian Institute of Science | 85.05 |
| 2024 | **Engineering** | ✅ Available | 100 | 200 | **300** | Indian Institute of Technology Madras | 89.46 |
| 2024 | **Management** | ✅ Available | 100 | 25 | **125** | Indian Institute of Management Ahmedabad | 83.32 |
| 2024 | **Medical** | ✅ Available | 50 | 0 | **50** | All India Institute of Medical Sciences Delhi | 94.46 |
| 2024 | **Overall** | ✅ Available | 100 | 100 | **200** | Indian Institute of Technology Madras | 86.42 |
| 2024 | **State Public University** | ✅ Available | 50 | 50 | **100** | Anna University | 78.14 |
| 2024 | **Universities** | ✅ Available | 100 | 100 | **200** | Indian Institute of Science, Bengaluru | 83.29 |
| 2023 | **Engineering** | ✅ Available | 100 | 101 | **201** | Indian Institute of Technology Madras | 89.79 |
| 2023 | **Management** | ✅ Available | 100 | 25 | **125** | Indian Institute of Management Ahmedabad | 83.20 |
| 2023 | **Medical** | ✅ Available | 50 | 0 | **50** | All India Institute of Medical Sciences, Delhi | 94.32 |
| 2023 | **Overall** | ✅ Available | 100 | 100 | **200** | Indian Institute of Technology Madras | 86.69 |
| 2023 | **State Public University** | ⚠️ Data Not Available | 0 | 0 | **0** | *Category introduced in NIRF 2024* | — |
| 2023 | **Universities** | ✅ Available | 100 | 101 | **201** | Indian Institute of Science | 83.16 |

---

## 3. Data Integrity & Validation Checks Performed

### A. Missing Institution Names & States
- **Institution Names:** 100% of imported records possess valid institution names. No blank records were retained.
- **States:** Identified and mapped all raw state names to canonical Indian States/UTs as recognized by Survey of India and the India GeoJSON boundary standard (`ST_NM`).

### B. State Name Normalization
Raw NIRF web data contains minor nomenclature discrepancies across editions (e.g. `Tamilnadu` vs `Tamil Nadu`, `New Delhi` vs `Delhi`, `Orissa` vs `Odisha`, `Jammu and Kashmir` vs `Jammu & Kashmir`). All variations were harmonized without altering the raw state reference.

### C. Duplicate Ranking Records
Checked for identical institution and city pairs appearing within the same category and year. Duplicate entries were flagged for manual review rather than silently discarded.

### D. Tied Ranks Preservation
NIRF officially awards tied ranks when institutions achieve identical aggregate scores (e.g., tied Rank 33 or Rank 76). The data pipeline identified and preserved 100% of tied rank designations (`is_tied = TRUE`), ensuring full fidelity to the Ministry of Education release.

### E. Institution ID Consistency Across Years
Tracked `institute_id` (e.g., `IR-O-U-0456`) across 2023, 2024, and 2025. Minor institutional name changes (such as addition of campus prefixes) were cross-referenced to maintain multi-year historical tracking.

### F. Category-Year Mismatches & Missing Data
NIRF added **State Public University** as an independent ranking category starting in **2024**. For year **2023**, State Public University is marked as **"Data Not Available"** with an informative banner rather than fabricated data or misleading zeros.

---

## 4. Sample Validation Audit Log Entries

| Year | Category | Record Identifier | Issue Type | Severity | Action Taken |
| :--- | :--- | :--- | :--- | :---: | :--- |
| 2025 | overall | Jawaharlal Institute of Post Graduate Medical Education & Research | `STATE_NAME_NORMALIZED` | INFO | Applied canonical state |
| 2025 | overall | University of Kashmir | `STATE_NAME_NORMALIZED` | INFO | Applied canonical state |
| 2025 | overall | University of Jammu | `STATE_NAME_NORMALIZED` | INFO | Applied canonical state |
| 2025 | overall | Sher-e-Kashmir University of Agricultural Science and Technology of Kashmir | `STATE_NAME_NORMALIZED` | INFO | Applied canonical state |
| 2025 | overall | National Institute of Technology Srinagar | `STATE_NAME_NORMALIZED` | INFO | Applied canonical state |
| 2025 | overall | Sri Balaji Vidyapeeth Mahatma Gandhi Medical College Campus | `STATE_NAME_NORMALIZED` | INFO | Applied canonical state |
| 2025 | overall | Pondicherry University | `STATE_NAME_NORMALIZED` | INFO | Applied canonical state |
| 2025 | overall | Rank 27 | `TIED_RANKS_PRESERVED` | INFO | Preserved tied rank for all institutions |
| 2025 | overall | Rank 64 | `TIED_RANKS_PRESERVED` | INFO | Preserved tied rank for all institutions |
| 2025 | universities | University of Kashmir | `STATE_NAME_NORMALIZED` | INFO | Applied canonical state |
| 2025 | universities | University of Jammu | `STATE_NAME_NORMALIZED` | INFO | Applied canonical state |
| 2025 | universities | Sri Balaji Vidyapeeth Mahatma Gandhi Medical College Campus | `STATE_NAME_NORMALIZED` | INFO | Applied canonical state |
| 2025 | universities | Sher-e-Kashmir University of Agricultural Science and Technology of Kashmir | `STATE_NAME_NORMALIZED` | INFO | Applied canonical state |
| 2025 | universities | Pondicherry University | `STATE_NAME_NORMALIZED` | INFO | Applied canonical state |
| 2025 | universities | Islamic University of Science & Technology, Pulwama | `STATE_NAME_NORMALIZED` | INFO | Applied canonical state |
| 2025 | universities | Sher-e-Kashmir University of Agricultural Science and Technology of Jammu | `STATE_NAME_NORMALIZED` | INFO | Applied canonical state |
| 2025 | universities | Rank 26 | `TIED_RANKS_PRESERVED` | INFO | Preserved tied rank for all institutions |
| 2025 | universities | Rank 85 | `TIED_RANKS_PRESERVED` | INFO | Preserved tied rank for all institutions |
| 2025 | engineering | Indian Institute of Technology Jammu | `STATE_NAME_NORMALIZED` | INFO | Applied canonical state |
| 2025 | engineering | National Institute of Technology Srinagar | `STATE_NAME_NORMALIZED` | INFO | Applied canonical state |
| 2025 | engineering | National Institute of Technology Puducherry | `STATE_NAME_NORMALIZED` | INFO | Applied canonical state |
| 2025 | engineering | Islamic University of Science & Technology, Pulwama | `STATE_NAME_NORMALIZED` | INFO | Applied canonical state |
| 2025 | engineering | Shri Mata Vaishno Devi University | `STATE_NAME_NORMALIZED` | INFO | Applied canonical state |
| 2025 | engineering | Puducherry Technological University | `STATE_NAME_NORMALIZED` | INFO | Applied canonical state |
| 2025 | engineering | Sri Manakula Vinayagar Engineering College | `STATE_NAME_NORMALIZED` | INFO | Applied canonical state |
| 2025 | engineering | Rank 67 | `TIED_RANKS_PRESERVED` | INFO | Preserved tied rank for all institutions |
| 2025 | management | Indian Institute of Management Jammu (IIMJ) | `STATE_NAME_NORMALIZED` | INFO | Applied canonical state |
| 2025 | management | Rank 46 | `TIED_RANKS_PRESERVED` | INFO | Preserved tied rank for all institutions |
| 2025 | management | Rank 57 | `TIED_RANKS_PRESERVED` | INFO | Preserved tied rank for all institutions |
| 2025 | medical | Jawaharlal Institute of Post Graduate Medical Education & Research | `STATE_NAME_NORMALIZED` | INFO | Applied canonical state |
| 2025 | medical | Mahatma Gandhi Medical College and Research Institute | `STATE_NAME_NORMALIZED` | INFO | Applied canonical state |
| 2025 | state_public_university | University of Kashmir | `STATE_NAME_NORMALIZED` | INFO | Applied canonical state |
| 2025 | state_public_university | University of Jammu | `STATE_NAME_NORMALIZED` | INFO | Applied canonical state |
| 2025 | state_public_university | Sher-e-Kashmir University of Agricultural Science and Technology of Kashmir | `STATE_NAME_NORMALIZED` | INFO | Applied canonical state |
| 2025 | state_public_university | Islamic University of Science & Technology, Pulwama | `STATE_NAME_NORMALIZED` | INFO | Applied canonical state |

*(Full validation log with all items is stored in the database table `validation_logs` and queryable via `/api/validation-report`).*
