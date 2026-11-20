import os

class Settings:
    PROJECT_NAME: str = "NIRF Insight: India State-wise Ranking Distribution Dashboard"
    PROJECT_VERSION: str = "2.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Dual database support: PostgreSQL if DATABASE_URL is set, otherwise embedded SQLite
    DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite:///{os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'nirf_v2.db'))}")
    
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
