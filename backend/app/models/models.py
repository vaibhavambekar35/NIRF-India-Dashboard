from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, Text, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from backend.app.core.database import Base

class State(Base):
    __tablename__ = "states"

    id = Column(Integer, primary_key=True, index=True)
    state_name = Column(String(100), unique=True, nullable=False, index=True)
    state_code = Column(String(10), nullable=True)
    geojson_key = Column(String(100), nullable=False, index=True)
    region_type = Column(String(20), default="State")  # "State" or "Union Territory"

    institutions = relationship("Institution", back_populates="state")

class Institution(Base):
    __tablename__ = "institutions"

    id = Column(Integer, primary_key=True, index=True)
    nirf_institute_id = Column(String(50), nullable=True, index=True)
    institution_name = Column(String(255), nullable=False, index=True)
    city = Column(String(100), nullable=True)
    state_id = Column(Integer, ForeignKey("states.id"), nullable=False)
    institution_type = Column(String(50), default="Private / Deemed")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    state = relationship("State", back_populates="institutions")
    rankings = relationship("RankingResult", back_populates="institution")

    __table_args__ = (
        UniqueConstraint("institution_name", "state_id", name="uq_inst_name_state"),
    )

class RankingEdition(Base):
    __tablename__ = "ranking_editions"

    id = Column(Integer, primary_key=True, index=True)
    ranking_year = Column(Integer, nullable=False, index=True)
    category = Column(String(100), nullable=False)
    category_slug = Column(String(100), nullable=False, index=True)
    maximum_rank = Column(Integer, nullable=True)
    data_status = Column(String(50), default="verified")  # "verified", "not_available"

    ranking_results = relationship("RankingResult", back_populates="edition")

    __table_args__ = (
        UniqueConstraint("ranking_year", "category_slug", name="uq_year_cat_edition"),
    )

class RankingResult(Base):
    __tablename__ = "ranking_results"

    id = Column(Integer, primary_key=True, index=True)
    institution_id = Column(Integer, ForeignKey("institutions.id"), nullable=False)
    ranking_edition_id = Column(Integer, ForeignKey("ranking_editions.id"), nullable=False)
    nirf_rank = Column(Integer, nullable=True, index=True)
    rank_display = Column(String(50), nullable=False)
    is_rank_band = Column(Boolean, default=False)
    is_tied = Column(Boolean, default=False)
    nirf_score = Column(Float, nullable=True, index=True)
    tlr = Column(Float, nullable=True)
    rpc = Column(Float, nullable=True)
    go = Column(Float, nullable=True)
    oi = Column(Float, nullable=True)
    perception = Column(Float, nullable=True)
    source_url = Column(Text, nullable=True)
    verification_status = Column(String(50), default="verified")
    imported_at = Column(DateTime, default=datetime.utcnow)

    institution = relationship("Institution", back_populates="rankings")
    edition = relationship("RankingEdition", back_populates="ranking_results")

class ImportBatch(Base):
    __tablename__ = "import_batches"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    category = Column(String(100), nullable=False)
    ranking_year = Column(Integer, nullable=False)
    records_imported = Column(Integer, default=0)
    records_rejected = Column(Integer, default=0)
    import_status = Column(String(50), default="completed")  # "completed", "failed", "pending"
    created_at = Column(DateTime, default=datetime.utcnow)
