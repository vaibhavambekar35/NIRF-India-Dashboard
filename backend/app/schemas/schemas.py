from typing import Optional, List, Any
from pydantic import BaseModel
from datetime import datetime

class YearItem(BaseModel):
    year: int
    is_default: bool
    is_available: bool

class CategoryItem(BaseModel):
    name: str
    slug: str
    max_rank: int

class AvailabilityItem(BaseModel):
    year: int
    category: str
    category_slug: str
    is_available: bool
    data_status: str
    total_records: int
    top_score: Optional[float] = None
    rank_1_institution: Optional[str] = None
    note: Optional[str] = None

class StateCount(BaseModel):
    state_id: int
    state_name: str
    institution_count: int
    best_rank: Optional[int] = None
    best_rank_display: Optional[str] = None
    top_institution: Optional[str] = None

class DistributionResponse(BaseModel):
    year: int
    category: str
    category_slug: str
    ranked_institutions: int
    states_represented: int
    data_status: str
    leading_state: Optional[str] = None
    leading_state_count: Optional[int] = None
    highest_ranked_institution: Optional[str] = None
    highest_score: Optional[float] = None
    note: Optional[str] = None
    state_counts: List[StateCount]

class InstitutionInRanking(BaseModel):
    rank: str
    rank_num: Optional[int] = None
    is_rank_band: bool
    is_tied: bool
    institution_name: str
    institute_id: Optional[str] = None
    city: Optional[str] = None
    state_name: str
    institution_type: Optional[str] = None
    score: Optional[float] = None
    tlr: Optional[float] = None
    rpc: Optional[float] = None
    go: Optional[float] = None
    oi: Optional[float] = None
    perception: Optional[float] = None
    source_url: Optional[str] = None

class StateDetailResponse(BaseModel):
    state_id: int
    state_name: str
    year: int
    category: str
    institution_count: int
    best_rank: Optional[str] = None
    institutions: List[InstitutionInRanking]

class ImportBatchResponse(BaseModel):
    id: int
    filename: str
    category: str
    ranking_year: int
    records_imported: int
    records_rejected: int
    import_status: str
    created_at: datetime
