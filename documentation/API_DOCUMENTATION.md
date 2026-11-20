# NIRF INSIGHT: REST API SPECIFICATION (V1)

**Base URL:** `/api/v1`  
**Interactive Swagger Docs:** `http://127.0.0.1:8000/docs`  
**OpenAPI Specification:** `http://127.0.0.1:8000/openapi.json`  

---

## 1. Endpoints Overview

| Method | Endpoint | Query Parameters | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/years` | — | Returns available ranking years with default flag |
| `GET` | `/categories` | — | Returns all 6 supported NIRF categories |
| `GET` | `/availability` | — | Returns edition availability matrix across all years |
| `GET` | `/distribution` | `year`, `category` | State-wise aggregation & choropleth metrics |
| `GET` | `/distribution/states/{state_id}` | `year`, `category` | Ranked institutions within a specific state |
| `GET` | `/institutions` | `year`, `category`, `state_id`, `search`, `rank_type` | Filterable institutional directory |
| `GET` | `/institutions/{institution_id}` | — | Multi-year historical profile for a single institution |
| `GET` | `/comparison` | `year` | Category distribution & multi-year trends |
| `GET` | `/export` | `format`, `year`, `category`, `state_id` | Streamed CSV or Excel dataset download |
| `GET` | `/admin/imports` | — | Historical list of all import batches |
| `POST` | `/admin/import` | `file`, `category`, `ranking_year` | Multipart form upload for Excel/CSV ingestion |

---

## 2. Sample Request & Response

### 2.1 State-wise Distribution Query
`GET /api/v1/distribution?year=2025&category=engineering`

**Response (`200 OK`):**
```json
{
  "year": 2025,
  "category": "Engineering",
  "category_slug": "engineering",
  "ranked_institutions": 300,
  "states_represented": 32,
  "data_status": "verified",
  "leading_state": "Tamil Nadu",
  "leading_state_count": 58,
  "highest_ranked_institution": "Indian Institute of Technology Madras",
  "highest_score": 88.72,
  "note": null,
  "state_counts": [
    {
      "state_id": 30,
      "state_name": "Tamil Nadu",
      "institution_count": 58,
      "best_rank": 1,
      "best_rank_display": "1",
      "top_institution": "Indian Institute of Technology Madras"
    },
    {
      "state_id": 19,
      "state_name": "Maharashtra",
      "institution_count": 31,
      "best_rank": 3,
      "best_rank_display": "3",
      "top_institution": "Indian Institute of Technology Bombay"
    }
  ]
}
```

### 2.2 Missing Dataset Handling (2023 State Public University)
`GET /api/v1/distribution?year=2023&category=state_public_university`

**Response (`200 OK`):**
```json
{
  "year": 2023,
  "category": "State Public University",
  "category_slug": "state_public_university",
  "ranked_institutions": 0,
  "states_represented": 0,
  "data_status": "not_available",
  "leading_state": "N/A",
  "leading_state_count": 0,
  "highest_ranked_institution": "N/A",
  "highest_score": null,
  "note": "Data Not Available: State Public University was introduced in NIRF 2024.",
  "state_counts": []
}
```
