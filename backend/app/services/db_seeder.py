import os
import re
import pandas as pd
from datetime import datetime
from sqlalchemy.orm import Session
from backend.app.core.database import engine, Base, SessionLocal
from backend.app.models.models import State, Institution, RankingEdition, RankingResult, ImportBatch
from backend.app.core.config import settings

CANONICAL_STATES = [
    ("Andaman & Nicobar", "AN", "Andaman & Nicobar", "Union Territory"),
    ("Andhra Pradesh", "AP", "Andhra Pradesh", "State"),
    ("Arunachal Pradesh", "AR", "Arunachal Pradesh", "State"),
    ("Assam", "AS", "Assam", "State"),
    ("Bihar", "BR", "Bihar", "State"),
    ("Chandigarh", "CH", "Chandigarh", "Union Territory"),
    ("Chhattisgarh", "CG", "Chhattisgarh", "State"),
    ("Dadra and Nagar Haveli and Daman and Diu", "DN", "Dadra and Nagar Haveli and Daman and Diu", "Union Territory"),
    ("Delhi", "DL", "Delhi", "Union Territory"),
    ("Goa", "GA", "Goa", "State"),
    ("Gujarat", "GJ", "Gujarat", "State"),
    ("Haryana", "HR", "Haryana", "State"),
    ("Himachal Pradesh", "HP", "Himachal Pradesh", "State"),
    ("Jammu & Kashmir", "JK", "Jammu & Kashmir", "Union Territory"),
    ("Jharkhand", "JH", "Jharkhand", "State"),
    ("Karnataka", "KA", "Karnataka", "State"),
    ("Kerala", "KL", "Kerala", "State"),
    ("Ladakh", "LA", "Ladakh", "Union Territory"),
    ("Lakshadweep", "LD", "Lakshadweep", "Union Territory"),
    ("Madhya Pradesh", "MP", "Madhya Pradesh", "State"),
    ("Maharashtra", "MH", "Maharashtra", "State"),
    ("Manipur", "MN", "Manipur", "State"),
    ("Meghalaya", "ML", "Meghalaya", "State"),
    ("Mizoram", "MZ", "Mizoram", "State"),
    ("Nagaland", "NL", "Nagaland", "State"),
    ("Odisha", "OD", "Odisha", "State"),
    ("Puducherry", "PY", "Puducherry", "Union Territory"),
    ("Punjab", "PB", "Punjab", "State"),
    ("Rajasthan", "RJ", "Rajasthan", "State"),
    ("Sikkim", "SK", "Sikkim", "State"),
    ("Tamil Nadu", "TN", "Tamil Nadu", "State"),
    ("Telangana", "TS", "Telangana", "State"),
    ("Tripura", "TR", "Tripura", "State"),
    ("Uttar Pradesh", "UP", "Uttar Pradesh", "State"),
    ("Uttarakhand", "UK", "Uttarakhand", "State"),
    ("West Bengal", "WB", "West Bengal", "State")
]

STATE_NORM_MAP = {
    'tamil nadu': 'Tamil Nadu',
    'tamilnadu': 'Tamil Nadu',
    'delhi': 'Delhi',
    'new delhi': 'Delhi',
    'nct of delhi': 'Delhi',
    'karnataka': 'Karnataka',
    'maharashtra': 'Maharashtra',
    'telangana': 'Telangana',
    'telengana': 'Telangana',
    'andhra pradesh': 'Andhra Pradesh',
    'uttar pradesh': 'Uttar Pradesh',
    'west bengal': 'West Bengal',
    'kerala': 'Kerala',
    'gujarat': 'Gujarat',
    'punjab': 'Punjab',
    'haryana': 'Haryana',
    'rajasthan': 'Rajasthan',
    'odisha': 'Odisha',
    'orissa': 'Odisha',
    'madhya pradesh': 'Madhya Pradesh',
    'assam': 'Assam',
    'bihar': 'Bihar',
    'jharkhand': 'Jharkhand',
    'chhattisgarh': 'Chhattisgarh',
    'chattisgarh': 'Chhattisgarh',
    'uttarakhand': 'Uttarakhand',
    'uttaranchal': 'Uttarakhand',
    'himachal pradesh': 'Himachal Pradesh',
    'jammu and kashmir': 'Jammu & Kashmir',
    'jammu & kashmir': 'Jammu & Kashmir',
    'chandigarh': 'Chandigarh',
    'goa': 'Goa',
    'puducherry': 'Puducherry',
    'pondicherry': 'Puducherry',
    'manipur': 'Manipur',
    'meghalaya': 'Meghalaya',
    'mizoram': 'Mizoram',
    'nagaland': 'Nagaland',
    'tripura': 'Tripura',
    'arunachal pradesh': 'Arunachal Pradesh',
    'sikkim': 'Sikkim',
    'andaman and nicobar islands': 'Andaman & Nicobar',
    'andaman & nicobar': 'Andaman & Nicobar',
    'dadra and nagar haveli and daman and diu': 'Dadra and Nagar Haveli and Daman and Diu',
    'daman and diu': 'Dadra and Nagar Haveli and Daman and Diu',
    'dadra and nagar haveli': 'Dadra and Nagar Haveli and Daman and Diu',
    'ladakh': 'Ladakh',
    'lakshadweep': 'Lakshadweep'
}

def normalize_state(val: str) -> str:
    if not val:
        return "Unknown"
    return STATE_NORM_MAP.get(str(val).strip().lower(), str(val).strip())

def seed_database():
    print("=" * 60)
    print("SEEDING NIRF INSIGHT RELATIONAL DATABASE")
    print("=" * 60)

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db: Session = SessionLocal()

    # 1. Seed States
    print("Seeding 36 Indian States and Union Territories...")
    state_lookup = {}
    for name, code, geo_key, r_type in CANONICAL_STATES:
        st = State(state_name=name, state_code=code, geojson_key=geo_key, region_type=r_type)
        db.add(st)
        db.flush()
        state_lookup[name] = st.id
        
    # Add Unknown fallback state
    unknown_state = State(state_name="Unknown", state_code="UNK", geojson_key="Unknown", region_type="Other")
    db.add(unknown_state)
    db.flush()
    state_lookup["Unknown"] = unknown_state.id
    db.commit()

    # 2. Seed Ranking Editions
    print("Seeding Ranking Editions (2023–2025 across 6 categories)...")
    edition_lookup = {}
    for y in settings.SUPPORTED_YEARS:
        for cat in settings.SUPPORTED_CATEGORIES:
            slug = cat["slug"]
            name = cat["name"]
            max_r = cat["max_rank"]
            
            # Special case: State Public University was introduced in 2024
            status = "not_available" if (y == 2023 and slug == "state_public_university") else "verified"
            ed = RankingEdition(
                ranking_year=y,
                category=name,
                category_slug=slug,
                maximum_rank=max_r,
                data_status=status
            )
            db.add(ed)
            db.flush()
            edition_lookup[(y, slug)] = ed.id
    db.commit()

    # 3. Ingest Data from Raw Excel Files
    raw_dir = os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "raw")
    category_slug_map = {
        'Overall': 'overall',
        'Universities': 'universities',
        'Engineering': 'engineering',
        'Management': 'management',
        'Medical': 'medical',
        'State Public University': 'state_public_university'
    }

    institution_lookup = {}
    total_records_ingested = 0

    for year in [2025, 2024, 2023]:
        filename = f"NIRF_India_Rankings_{year}.xlsx"
        filepath = os.path.join(raw_dir, filename)
        if not os.path.exists(filepath):
            print(f"Warning: {filepath} not found!")
            continue

        print(f"\nProcessing {filename} (Year {year})...")
        xl = pd.ExcelFile(filepath)

        for sheet_name in xl.sheet_names:
            if sheet_name in ['Overview & Summary', 'All Categories Combined']:
                continue

            slug = category_slug_map.get(sheet_name)
            if not slug or (year, slug) not in edition_lookup:
                continue

            ed_id = edition_lookup[(year, slug)]
            df = xl.parse(sheet_name)

            col_map = {}
            for col in df.columns:
                c_low = col.lower().strip()
                if 'rank' in c_low and 'band' not in c_low:
                    col_map['rank'] = col
                elif 'institute id' in c_low or 'id' == c_low:
                    col_map['institute_id'] = col
                elif 'name' in c_low:
                    col_map['name'] = col
                elif 'city' in c_low:
                    col_map['city'] = col
                elif 'state' in c_low:
                    col_map['state'] = col
                elif 'score' in c_low and 'tlr' not in c_low and 'rpc' not in c_low:
                    col_map['score'] = col
                elif 'tlr' in c_low:
                    col_map['tlr'] = col
                elif 'rpc' in c_low:
                    col_map['rpc'] = col
                elif 'go' in c_low and '100' in c_low:
                    col_map['go'] = col
                elif 'oi' in c_low:
                    col_map['oi'] = col
                elif 'perception' in c_low:
                    col_map['perception'] = col
                elif 'pdf' in c_low or 'report' in c_low:
                    col_map['pdf'] = col

            batch_count = 0
            rank_counts = {}

            # First pass: check rank counts for tied ranks
            for _, row in df.iterrows():
                r_str = str(row[col_map['rank']]).strip() if col_map.get('rank') and pd.notna(row[col_map['rank']]) else ''
                if r_str.isdigit():
                    rn = int(r_str)
                    rank_counts[rn] = rank_counts.get(rn, 0) + 1

            for _, row in df.iterrows():
                name_val = str(row[col_map['name']]).strip() if pd.notna(row[col_map['name']]) else ''
                if not name_val or name_val.lower() == 'nan':
                    continue

                raw_state = str(row[col_map.get('state')]).strip() if col_map.get('state') and pd.notna(row[col_map.get('state')]) else ''
                norm_state = normalize_state(raw_state)
                st_id = state_lookup.get(norm_state, state_lookup["Unknown"])

                city_val = str(row[col_map.get('city')]).strip() if col_map.get('city') and pd.notna(row[col_map.get('city')]) else ''
                if city_val.lower() == 'nan': city_val = ''

                inst_id_val = str(row[col_map.get('institute_id')]).strip() if col_map.get('institute_id') and pd.notna(row[col_map.get('institute_id')]) else ''
                if inst_id_val.lower() == 'nan': inst_id_val = ''

                # Upsert Institution
                inst_key = (name_val.lower(), st_id)
                if inst_key not in institution_lookup:
                    inst = Institution(
                        nirf_institute_id=inst_id_val,
                        institution_name=name_val,
                        city=city_val,
                        state_id=st_id
                    )
                    db.add(inst)
                    db.flush()
                    institution_lookup[inst_key] = inst.id
                else:
                    if inst_id_val:
                        # update ID if newly present
                        inst = db.query(Institution).filter_by(id=institution_lookup[inst_key]).first()
                        if inst and not inst.nirf_institute_id:
                            inst.nirf_institute_id = inst_id_val

                real_inst_id = institution_lookup[inst_key]

                rank_raw = str(row[col_map.get('rank')]).strip() if col_map.get('rank') and pd.notna(row[col_map.get('rank')]) else ''
                is_band = ('-' in rank_raw) or any(c.isalpha() for c in rank_raw) or not rank_raw.isdigit()
                rank_num = int(rank_raw) if (not is_band and rank_raw.isdigit()) else None
                is_tied = (rank_num is not None and rank_counts.get(rank_num, 0) > 1)

                def get_float(k):
                    if col_map.get(k) and pd.notna(row[col_map.get(k)]):
                        try:
                            return round(float(row[col_map.get(k)]), 2)
                        except:
                            return None
                    return None

                score_val = get_float('score')
                tlr_val = get_float('tlr')
                rpc_val = get_float('rpc')
                go_val = get_float('go')
                oi_val = get_float('oi')
                perc_val = get_float('perception')
                pdf_val = str(row[col_map.get('pdf')]).strip() if col_map.get('pdf') and pd.notna(row[col_map.get('pdf')]) else ''
                if pdf_val.lower() == 'nan': pdf_val = ''

                # Add Ranking Result
                rr = RankingResult(
                    institution_id=real_inst_id,
                    ranking_edition_id=ed_id,
                    nirf_rank=rank_num,
                    rank_display=rank_raw if rank_raw else 'N/A',
                    is_rank_band=is_band,
                    is_tied=is_tied,
                    nirf_score=score_val,
                    tlr=tlr_val,
                    rpc=rpc_val,
                    go=go_val,
                    oi=oi_val,
                    perception=perc_val,
                    source_url=pdf_val,
                    verification_status="verified"
                )
                db.add(rr)
                batch_count += 1
                total_records_ingested += 1

            # Log Import Batch
            ib = ImportBatch(
                filename=filename,
                category=sheet_name,
                ranking_year=year,
                records_imported=batch_count,
                records_rejected=0,
                import_status="completed"
            )
            db.add(ib)
            db.commit()

    print(f"\nDatabase seeding complete!")
    print(f"Total Ranking Records: {total_records_ingested}")
    print(f"Unique Institutions:   {len(institution_lookup)}")
    db.close()

if __name__ == "__main__":
    seed_database()
