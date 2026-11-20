-- ====================================================================
-- NIRF INSIGHT: POSTGRESQL SCHEMA SPECIFICATION
-- Database Schema for NIRF India State-wise Distribution Dashboard
-- ====================================================================

DROP TABLE IF EXISTS validation_logs CASCADE;
DROP TABLE IF EXISTS rankings CASCADE;
DROP TABLE IF EXISTS institutions CASCADE;
DROP TABLE IF EXISTS category_coverage CASCADE;
DROP TABLE IF EXISTS ranking_years CASCADE;
DROP TABLE IF EXISTS categories CASCADE;

CREATE TABLE categories (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    display_order INTEGER NOT NULL,
    description TEXT,
    icon VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE ranking_years (
    id SERIAL PRIMARY KEY,
    year INTEGER UNIQUE NOT NULL,
    is_default BOOLEAN DEFAULT FALSE,
    is_available BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE category_coverage (
    id SERIAL PRIMARY KEY,
    category_code VARCHAR(50) NOT NULL REFERENCES categories(code) ON DELETE CASCADE,
    year INTEGER NOT NULL,
    is_available BOOLEAN DEFAULT TRUE,
    top_ranked_count INTEGER DEFAULT 0,
    rank_bands_count INTEGER DEFAULT 0,
    total_institutions INTEGER DEFAULT 0,
    highest_score NUMERIC(5, 2),
    rank_1_institution TEXT,
    note TEXT,
    CONSTRAINT uq_cat_year UNIQUE(category_code, year)
);

CREATE TABLE institutions (
    id SERIAL PRIMARY KEY,
    institute_id VARCHAR(50),
    canonical_name VARCHAR(255) NOT NULL,
    city VARCHAR(100),
    state_canonical VARCHAR(100) NOT NULL,
    CONSTRAINT uq_inst_state UNIQUE(canonical_name, state_canonical)
);

CREATE TABLE rankings (
    id SERIAL PRIMARY KEY,
    year INTEGER NOT NULL,
    category_code VARCHAR(50) NOT NULL REFERENCES categories(code) ON DELETE CASCADE,
    institute_id VARCHAR(50),
    institute_name VARCHAR(255) NOT NULL,
    city VARCHAR(100),
    state VARCHAR(100) NOT NULL,
    state_raw VARCHAR(100),
    rank_num INTEGER,
    rank_display VARCHAR(50) NOT NULL,
    is_rank_band BOOLEAN DEFAULT FALSE,
    is_tied BOOLEAN DEFAULT FALSE,
    score NUMERIC(5, 2),
    tlr NUMERIC(5, 2),
    rpc NUMERIC(5, 2),
    go NUMERIC(5, 2),
    oi NUMERIC(5, 2),
    perception NUMERIC(5, 2),
    report_pdf TEXT,
    source_file VARCHAR(255),
    validation_status VARCHAR(50) DEFAULT 'VALID',
    validation_notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE validation_logs (
    id SERIAL PRIMARY KEY,
    year INTEGER,
    category_code VARCHAR(50),
    record_identifier TEXT,
    issue_type VARCHAR(100) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    issue_detail TEXT,
    action_taken TEXT,
    logged_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_rankings_year_cat ON rankings (year, category_code);
CREATE INDEX idx_rankings_state ON rankings (state);
CREATE INDEX idx_rankings_score ON rankings (score DESC NULLS LAST);
CREATE INDEX idx_rankings_rank ON rankings (rank_num ASC NULLS LAST);
CREATE INDEX idx_institutions_name ON institutions (canonical_name);
