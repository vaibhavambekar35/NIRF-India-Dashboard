import os
import shutil

def get_database_url() -> str:
    env_url = os.getenv("DATABASE_URL")
    if env_url:
        return env_url

    # Check candidates for sqlite db
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    candidates = [
        os.path.join(base_dir, "nirf_v2.db"),
        os.path.join(base_dir, "api", "nirf_v2.db"),
        os.path.abspath("nirf_v2.db"),
        os.path.abspath(os.path.join("api", "nirf_v2.db")),
        "/var/task/nirf_v2.db",
        "/var/task/api/nirf_v2.db"
    ]

    found_path = None
    for cand in candidates:
        if os.path.exists(cand):
            found_path = cand
            break

    if not found_path:
        found_path = candidates[0]

    # In Vercel / serverless environment, copy to /tmp for writable SQLite operations
    if os.getenv("VERCEL") or os.getenv("AWS_LAMBDA_FUNCTION_NAME"):
        tmp_db = "/tmp/nirf_v2.db"
        if found_path and os.path.exists(found_path) and not os.path.exists(tmp_db):
            try:
                shutil.copy2(found_path, tmp_db)
            except Exception as e:
                print(f"Serverless warning: Could not copy db to /tmp: {e}")
        if os.path.exists(tmp_db):
            return f"sqlite:///{tmp_db}"

    return f"sqlite:///{found_path}"


class Settings:
    PROJECT_NAME: str = "NIRF Insight: India State-wise Ranking Distribution Dashboard"
    PROJECT_VERSION: str = "2.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Dual database support: PostgreSQL if DATABASE_URL is set, otherwise embedded SQLite
    DATABASE_URL: str = get_database_url()
    
    # Supported Ranking Years
    SUPPORTED_YEARS: list = [2023, 2024, 2025]
    DEFAULT_YEAR: int = 2025
    
    # 6 NIRF Categories
    SUPPORTED_CATEGORIES: list = [
        {"name": "Overall", "slug": "overall", "max_rank": 200},
        {"name": "Universities", "slug": "universities", "max_rank": 200},
        {"name": "Engineering", "slug": "engineering", "max_rank": 300},
        {"name": "Management", "slug": "management", "max_rank": 125},
        {"name": "Medical", "slug": "medical", "max_rank": 50},
        {"name": "State Public University", "slug": "state_public_university", "max_rank": 100}
    ]

settings = Settings()
