import io
import csv
from typing import Optional, List
from fastapi import APIRouter, Depends, Query, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, aliased
from sqlalchemy import func, desc, asc
import pandas as pd
import openpyxl

from backend.app.core.database import get_db
from backend.app.core.config import settings
from backend.app.models.models import State, Institution, RankingEdition, RankingResult, ImportBatch
from backend.app.schemas.schemas import (
    YearItem, CategoryItem, AvailabilityItem, StateCount,
    DistributionResponse, StateDetailResponse, InstitutionInRanking,
    ImportBatchResponse
)

router = APIRouter()

# 1. GET /api/v1/years
@router.get("/years", response_model=List[YearItem])
def get_years(db: Session = Depends(get_db)):
    editions = db.query(RankingEdition.ranking_year).distinct().order_by(desc(RankingEdition.ranking_year)).all()
    years = [e[0] for e in editions] if editions else settings.SUPPORTED_YEARS
    return [
        YearItem(
            year=y,
            is_default=(y == settings.DEFAULT_YEAR),
            is_available=True
        ) for y in sorted(years, reverse=True)
    ]

# 2. GET /api/v1/categories
@router.get("/categories", response_model=List[CategoryItem])
def get_categories(db: Session = Depends(get_db)):
    editions = db.query(RankingEdition.category, RankingEdition.category_slug, RankingEdition.maximum_rank)\
                 .distinct().all()
    if editions:
        return [CategoryItem(name=e[0], slug=e[1], max_rank=e[2] or 100) for e in editions]
    return [CategoryItem(name=c["name"], slug=c["slug"], max_rank=c["max_rank"]) for c in settings.SUPPORTED_CATEGORIES]

# 2b. GET /api/v1/states
@router.get("/states")
def get_states(db: Session = Depends(get_db)):
    states = db.query(State).order_by(State.state_name).all()
    return [{"id": s.id, "name": s.state_name, "code": s.state_code} for s in states]

# 3. GET /api/v1/availability
@router.get("/availability", response_model=List[AvailabilityItem])
def get_availability(db: Session = Depends(get_db)):
    editions = db.query(RankingEdition).order_by(desc(RankingEdition.ranking_year), RankingEdition.id).all()
    result = []
    for ed in editions:
        total = db.query(RankingResult).filter_by(ranking_edition_id=ed.id).count()
        top_res = db.query(RankingResult).join(Institution)\
                    .filter(RankingResult.ranking_edition_id == ed.id, RankingResult.nirf_rank == 1)\
                    .first()
        is_avail = (ed.data_status == "verified" and total > 0)
        note = "Category introduced in NIRF 2024" if (ed.ranking_year == 2023 and ed.category_slug == "state_public_university") else ("Verified and available" if is_avail else "Data Not Available")

        result.append(AvailabilityItem(
            year=ed.ranking_year,
            category=ed.category,
            category_slug=ed.category_slug,
            is_available=is_avail,
            data_status=ed.data_status,
            total_records=total,
            top_score=top_res.nirf_score if top_res else None,
            rank_1_institution=top_res.institution.institution_name if top_res else None,
            note=note
        ))
    return result

def get_top_100_filter():
    return (
        (RankingResult.nirf_rank.isnot(None) & (RankingResult.nirf_rank <= 100) & (RankingResult.is_rank_band == False)) |
        (RankingResult.rank_display == "51-100")
    )

def get_ownership_filter(ownership: Optional[str]):
    if not ownership or ownership.lower() == "all":
        return None
    o = ownership.lower().strip()
    if o == "central":
        return Institution.institution_type == "Central"
    elif o in ["state_public", "state public"]:
        return Institution.institution_type == "State Public"
    elif o in ["private_deemed", "private", "deemed", "private / deemed"]:
        return Institution.institution_type == "Private / Deemed"
    return None

# 4. GET /api/v1/distribution
@router.get("/distribution", response_model=DistributionResponse)
def get_distribution(
    year: int = Query(settings.DEFAULT_YEAR),
    category: str = Query("overall"),
    scope: str = Query("top_100"),
    ownership: str = Query("all"),
    top_100_only: Optional[bool] = Query(None),
    db: Session = Depends(get_db)
):
    use_top_100 = True
    if (scope and scope.lower() == "all") or top_100_only is False:
        use_top_100 = False

    own_filter = get_ownership_filter(ownership)

    # Lookup Edition
    cat_slug = category.lower().strip().replace(" ", "_")
    edition = db.query(RankingEdition).filter(
        RankingEdition.ranking_year == year,
        (RankingEdition.category_slug == cat_slug) | (func.lower(RankingEdition.category) == category.lower().strip())
    ).first()

    if not edition or edition.data_status != "verified":
        note = "Data Not Available: State Public University was introduced in NIRF 2024." if (year == 2023 and cat_slug == "state_public_university") else "Data Not Available for selected category and year."
        return DistributionResponse(
            year=year,
            category=category.title(),
            category_slug=cat_slug,
            ranked_institutions=0,
            states_represented=0,
            data_status="not_available",
            leading_state="N/A",
            leading_state_count=0,
            highest_ranked_institution="N/A",
            highest_score=None,
            note=note,
            state_counts=[]
        )

    # State counts aggregation from PostgreSQL / SQLite
    st_q = db.query(
        State.id.label("state_id"),
        State.state_name.label("state_name"),
        func.count(RankingResult.id).label("inst_count"),
        func.min(RankingResult.nirf_rank).label("best_rank")
    ).join(Institution, Institution.state_id == State.id)\
     .join(RankingResult, RankingResult.institution_id == Institution.id)\
     .filter(RankingResult.ranking_edition_id == edition.id)

    if use_top_100:
        st_q = st_q.filter(get_top_100_filter())
    if own_filter is not None:
        st_q = st_q.filter(own_filter)

    st_counts_query = st_q.group_by(State.id, State.state_name)\
     .order_by(desc("inst_count"), desc(func.max(RankingResult.nirf_score)))\
     .all()

    state_counts = []
    for r in st_counts_query:
        # Top institution in state
        top_in_state_q = db.query(Institution.institution_name, RankingResult.rank_display)\
                         .join(RankingResult, RankingResult.institution_id == Institution.id)\
                         .filter(RankingResult.ranking_edition_id == edition.id, Institution.state_id == r.state_id)
        if use_top_100:
            top_in_state_q = top_in_state_q.filter(get_top_100_filter())
        if own_filter is not None:
            top_in_state_q = top_in_state_q.filter(own_filter)

        top_in_state = top_in_state_q.order_by(
            func.coalesce(RankingResult.nirf_rank, 9999).asc(),
            RankingResult.nirf_score.desc().nullslast()
        ).first()

        state_counts.append(StateCount(
            state_id=r.state_id,
            state_name=r.state_name,
            institution_count=r.inst_count,
            best_rank=r.best_rank,
            best_rank_display=top_in_state[1] if top_in_state else None,
            top_institution=top_in_state[0] if top_in_state else None
        ))

    total_q = db.query(RankingResult).join(Institution, Institution.id == RankingResult.institution_id)\
                .filter(RankingResult.ranking_edition_id == edition.id)
    if use_top_100:
        total_q = total_q.filter(get_top_100_filter())
    if own_filter is not None:
        total_q = total_q.filter(own_filter)
    total_insts = total_q.count()

    states_rep = len(state_counts)
    leading_st = state_counts[0].state_name if state_counts else "N/A"
    leading_cnt = state_counts[0].institution_count if state_counts else 0

    top_overall_q = db.query(Institution.institution_name, RankingResult.nirf_score)\
                      .join(RankingResult, RankingResult.institution_id == Institution.id)\
                      .filter(RankingResult.ranking_edition_id == edition.id)
    if use_top_100:
        top_overall_q = top_overall_q.filter(get_top_100_filter())
    if own_filter is not None:
        top_overall_q = top_overall_q.filter(own_filter)

    top_overall = top_overall_q.order_by(
        func.coalesce(RankingResult.nirf_rank, 9999).asc(),
        RankingResult.nirf_score.desc().nullslast()
    ).first()

    return DistributionResponse(
        year=year,
        category=edition.category,
        category_slug=edition.category_slug,
        ranked_institutions=total_insts,
        states_represented=states_rep,
        data_status="verified",
        leading_state=leading_st,
        leading_state_count=leading_cnt,
        highest_ranked_institution=top_overall[0] if top_overall else "N/A",
        highest_score=top_overall[1] if top_overall else None,
        note=None,
        state_counts=state_counts
    )

# 5. GET /api/v1/distribution/states/{state_id}
@router.get("/distribution/states/{state_id}", response_model=StateDetailResponse)
def get_state_distribution(
    state_id: int,
    year: int = Query(settings.DEFAULT_YEAR),
    category: str = Query("overall"),
    scope: str = Query("top_100"),
    ownership: str = Query("all"),
    top_100_only: Optional[bool] = Query(None),
    db: Session = Depends(get_db)
):
    use_top_100 = True
    if (scope and scope.lower() == "all") or top_100_only is False:
        use_top_100 = False

    state = db.query(State).filter_by(id=state_id).first()
    if not state:
        raise HTTPException(status_code=404, detail=f"State with id {state_id} not found")

    cat_slug = category.lower().strip().replace(" ", "_")
    edition = db.query(RankingEdition).filter(
        RankingEdition.ranking_year == year,
        (RankingEdition.category_slug == cat_slug) | (func.lower(RankingEdition.category) == category.lower().strip())
    ).first()

    if not edition:
        raise HTTPException(status_code=404, detail="Ranking edition not found")

    q = db.query(RankingResult, Institution)\
          .join(Institution, Institution.id == RankingResult.institution_id)\
          .filter(RankingResult.ranking_edition_id == edition.id, Institution.state_id == state_id)

    if use_top_100:
        q = q.filter(get_top_100_filter())
    
    own_filter = get_ownership_filter(ownership)
    if own_filter is not None:
        q = q.filter(own_filter)

    results = q.order_by(
        func.coalesce(RankingResult.nirf_rank, 9999).asc(),
        RankingResult.nirf_score.desc().nullslast()
    ).all()

    inst_list = []
    for rr, inst in results:
        inst_list.append(InstitutionInRanking(
            rank=rr.rank_display,
            rank_num=rr.nirf_rank,
            is_rank_band=rr.is_rank_band,
            is_tied=rr.is_tied,
            institution_name=inst.institution_name,
            institute_id=inst.nirf_institute_id,
            city=inst.city,
            state_name=state.state_name,
            institution_type=inst.institution_type or "Private / Deemed",
            score=rr.nirf_score,
            tlr=rr.tlr,
            rpc=rr.rpc,
            go=rr.go,
            oi=rr.oi,
            perception=rr.perception,
            source_url=rr.source_url
        ))

    best_r = inst_list[0].rank if inst_list else None

    return StateDetailResponse(
        state_id=state.id,
        state_name=state.state_name,
        year=year,
        category=edition.category,
        institution_count=len(inst_list),
        best_rank=best_r,
        institutions=inst_list
    )

# 6. GET /api/v1/institutions
@router.get("/institutions")
def get_institutions(
    year: int = Query(settings.DEFAULT_YEAR),
    category: str = Query("overall"),
    state_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    ownership: str = Query("all"),
    rank_type: Optional[str] = Query("all"), # "all", "top", "band"
    db: Session = Depends(get_db)
):
    cat_slug = category.lower().strip().replace(" ", "_")
    edition = db.query(RankingEdition).filter(
        RankingEdition.ranking_year == year,
        (RankingEdition.category_slug == cat_slug) | (func.lower(RankingEdition.category) == category.lower().strip())
    ).first()

    if not edition:
        return []

    q = db.query(RankingResult, Institution, State)\
          .join(Institution, Institution.id == RankingResult.institution_id)\
          .join(State, State.id == Institution.state_id)\
          .filter(RankingResult.ranking_edition_id == edition.id)

    if state_id:
        q = q.filter(Institution.state_id == state_id)

    own_filter = get_ownership_filter(ownership)
    if own_filter is not None:
        q = q.filter(own_filter)

    if rank_type == "top":
        q = q.filter(get_top_100_filter())
    elif rank_type == "band":
        q = q.filter(~get_top_100_filter())

    if search and search.strip():
        s_clean = search.strip().lower()
        term = f"%{s_clean}%"
        
        # Smart acronym alias expansions for intuitive institution search
        acronym_aliases = {
            "iit": "%indian institute of technology%",
            "nit": "%national institute of technology%",
            "iim": "%indian institute of management%",
            "aiims": "%all india institute of medical sciences%",
            "iisc": "%indian institute of science%",
            "bits": "%birla institute of technology%",
            "jnu": "%jawaharlal nehru university%",
            "bhu": "%banaras hindu university%",
            "amu": "%aligarh muslim university%"
        }
        alias_filter = None
        if s_clean in acronym_aliases:
            alias_filter = func.lower(Institution.institution_name).like(acronym_aliases[s_clean])
        
        base_filter = (
            func.lower(Institution.institution_name).like(term) |
            func.lower(Institution.city).like(term) |
            func.lower(State.state_name).like(term) |
            func.lower(Institution.nirf_institute_id).like(term)
        )
        if alias_filter is not None:
            q = q.filter(base_filter | alias_filter)
        else:
            q = q.filter(base_filter)

    q = q.order_by(
        func.coalesce(RankingResult.nirf_rank, 9999).asc(),
        RankingResult.nirf_score.desc().nullslast(),
        Institution.institution_name.asc()
    )

    rows = q.all()
    return [
        {
            "id": inst.id,
            "rank": rr.rank_display,
            "rank_num": rr.nirf_rank,
            "is_rank_band": rr.is_rank_band,
            "is_tied": rr.is_tied,
            "institution_name": inst.institution_name,
            "institution_type": inst.institution_type or "Private / Deemed",
            "institute_id": inst.nirf_institute_id,
            "city": inst.city,
            "state_id": st.id,
            "state_name": st.state_name,
            "score": rr.nirf_score,
            "tlr": rr.tlr,
            "rpc": rr.rpc,
            "go": rr.go,
            "oi": rr.oi,
            "perception": rr.perception,
            "source_url": rr.source_url
        } for rr, inst, st in rows
    ]

# 7. GET /api/v1/institutions/{institution_id}
@router.get("/institutions/{institution_id}")
def get_institution_by_id(
    institution_id: int,
    category: Optional[str] = Query(None),
    year: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    inst = db.query(Institution).filter_by(id=institution_id).first()
    if not inst:
        raise HTTPException(status_code=404, detail="Institution not found")

    rankings = db.query(RankingResult, RankingEdition)\
                 .join(RankingEdition, RankingEdition.id == RankingResult.ranking_edition_id)\
                 .filter(RankingResult.institution_id == institution_id)\
                 .order_by(desc(RankingEdition.ranking_year), desc(RankingResult.nirf_score))\
                 .all()

    history = []
    for rr, ed in rankings:
        history.append({
            "year": ed.ranking_year,
            "category": ed.category,
            "category_slug": ed.category_slug,
            "rank": rr.rank_display,
            "score": rr.nirf_score,
            "tlr": rr.tlr,
            "rpc": rr.rpc,
            "go": rr.go,
            "oi": rr.oi,
            "perception": rr.perception,
            "source_url": rr.source_url
        })

    # Prioritize requested category and year if provided
    radar_data = None
    scored_ranking = None
    if category or year:
        for rr, ed in rankings:
            match_cat = (not category) or (ed.category_slug == category.lower().strip().replace(" ", "_") or ed.category.lower() == category.lower().strip())
            match_yr = (not year) or (ed.ranking_year == year)
            if match_cat and match_yr and rr.tlr is not None and rr.rpc is not None:
                scored_ranking = rr
                break

    if not scored_ranking:
        scored_ranking = next((rr for rr, ed in rankings if rr.tlr is not None and rr.rpc is not None), None)

    if scored_ranking:
        ed_id = scored_ranking.ranking_edition_id
        cat_bench = db.query(
            func.avg(RankingResult.tlr),
            func.avg(RankingResult.rpc),
            func.avg(RankingResult.go),
            func.avg(RankingResult.oi),
            func.avg(RankingResult.perception)
        ).filter(RankingResult.ranking_edition_id == ed_id, RankingResult.nirf_rank <= 100).first()

        top10_bench = db.query(
            func.avg(RankingResult.tlr),
            func.avg(RankingResult.rpc),
            func.avg(RankingResult.go),
            func.avg(RankingResult.oi),
            func.avg(RankingResult.perception)
        ).filter(RankingResult.ranking_edition_id == ed_id, RankingResult.nirf_rank <= 10).first()

        radar_data = {
            "category": scored_ranking.ranking_edition.category if hasattr(scored_ranking, 'ranking_edition') and scored_ranking.ranking_edition else None,
            "labels": ["Teaching (TLR)", "Research (RPC)", "Graduation (GO)", "Outreach (OI)", "Perception (PR)"],
            "institution_scores": [
                round(scored_ranking.tlr or 0, 1),
                round(scored_ranking.rpc or 0, 1),
                round(scored_ranking.go or 0, 1),
                round(scored_ranking.oi or 0, 1),
                round(scored_ranking.perception or 0, 1)
            ],
            "category_averages": [
                round(cat_bench[0] or 0, 1) if cat_bench and cat_bench[0] else 0,
                round(cat_bench[1] or 0, 1) if cat_bench and cat_bench[1] else 0,
                round(cat_bench[2] or 0, 1) if cat_bench and cat_bench[2] else 0,
                round(cat_bench[3] or 0, 1) if cat_bench and cat_bench[3] else 0,
                round(cat_bench[4] or 0, 1) if cat_bench and cat_bench[4] else 0
            ],
            "top10_benchmarks": [
                round(top10_bench[0] or 0, 1) if top10_bench and top10_bench[0] else 0,
                round(top10_bench[1] or 0, 1) if top10_bench and top10_bench[1] else 0,
                round(top10_bench[2] or 0, 1) if top10_bench and top10_bench[2] else 0,
                round(top10_bench[3] or 0, 1) if top10_bench and top10_bench[3] else 0,
                round(top10_bench[4] or 0, 1) if top10_bench and top10_bench[4] else 0
            ]
        }

    return {
        "id": inst.id,
        "nirf_institute_id": inst.nirf_institute_id,
        "institution_name": inst.institution_name,
        "institution_type": inst.institution_type or "Private / Deemed",
        "city": inst.city,
        "state_id": inst.state_id,
        "state_name": inst.state.state_name,
        "radar": radar_data,
        "rankings_history": history
    }

# 8. GET /api/v1/comparison
@router.get("/comparison")
def get_comparison(
    year: int = Query(settings.DEFAULT_YEAR),
    scope: str = Query("top_100"),
    top_100_only: Optional[bool] = Query(None),
    db: Session = Depends(get_db)
):
    use_top_100 = True
    if (scope and scope.lower() == "all") or top_100_only is False:
        use_top_100 = False

    editions = db.query(RankingEdition).filter_by(ranking_year=year).all()
    comparison_data = []

    for ed in editions:
        total_q = db.query(RankingResult).filter_by(ranking_edition_id=ed.id)
        if use_top_100:
            total_q = total_q.filter(get_top_100_filter())
        total = total_q.count()

        states_q = db.query(State.state_name, func.count(RankingResult.id).label("count"))\
                       .join(Institution, Institution.state_id == State.id)\
                       .join(RankingResult, RankingResult.institution_id == Institution.id)\
                       .filter(RankingResult.ranking_edition_id == ed.id)
        if use_top_100:
            states_q = states_q.filter(get_top_100_filter())

        top_states = states_q.group_by(State.state_name)\
                             .order_by(desc("count"))\
                             .limit(5).all()

        comparison_data.append({
            "category": ed.category,
            "category_slug": ed.category_slug,
            "total_institutions": total,
            "data_status": ed.data_status,
            "top_states": [{"state": s[0], "count": s[1]} for s in top_states]
        })

    # Year over year total trends across all categories
    yoy_query = db.query(RankingEdition.ranking_year, func.count(RankingResult.id))\
                  .join(RankingResult, RankingResult.ranking_edition_id == RankingEdition.id)\
                  .group_by(RankingEdition.ranking_year)\
                  .order_by(RankingEdition.ranking_year)\
                  .all()
    yoy_trend = [{"year": y[0], "total_rankings": y[1]} for y in yoy_query]

    return {
        "selected_year": year,
        "categories_comparison": comparison_data,
        "year_over_year_trend": yoy_trend
    }

# 9. GET /api/v1/benchmarking/compare-states
@router.get("/benchmarking/compare-states")
def compare_states(
    state_a_id: int = Query(...),
    state_b_id: int = Query(...),
    year: int = Query(settings.DEFAULT_YEAR),
    category: Optional[str] = Query(None),
    scope: str = Query("top_100"),
    ownership: str = Query("all"),
    db: Session = Depends(get_db)
):
    use_top_100 = (scope.lower() != "all")

    # Find category name
    cat_meta = next((c for c in settings.SUPPORTED_CATEGORIES if c["slug"] == category), None) if category else None
    cat_display_name = cat_meta["name"] if cat_meta else (category.title() if category else "All Disciplines")

    def get_state_metrics(st_id: int):
        st = db.query(State).filter_by(id=st_id).first()
        if not st:
            return None
        
        q = db.query(RankingResult, RankingEdition, Institution)\
              .join(Institution, Institution.id == RankingResult.institution_id)\
              .join(RankingEdition, RankingEdition.id == RankingResult.ranking_edition_id)\
              .filter(Institution.state_id == st_id, RankingEdition.ranking_year == year)
        
        if use_top_100:
            q = q.filter(get_top_100_filter())

        if ownership and ownership.lower() != "all":
            q = q.filter(Institution.institution_type == ownership)
            
        results = q.all()
        
        # 1. Total category distribution across all 6 disciplines (for the grouped bar chart)
        cat_counts = {c["slug"]: 0 for c in settings.SUPPORTED_CATEGORIES}
        for rr, ed, inst in results:
            cat_counts[ed.category_slug] = cat_counts.get(ed.category_slug, 0) + 1

        # 2. Filter for active category diagnostic (radar, card counts, avg score, RPC, TLR, governance)
        if category and category.lower() not in ["all", "combined", ""]:
            scoped_results = [r for r in results if r[1].category_slug == category.lower()]
        else:
            scoped_results = results

        own_counts = {"Central": 0, "State Public": 0, "Private / Deemed": 0}
        scores, tlrs, rpcs, gos, ois, perceptions = [], [], [], [], [], []
        best_rank = None
        top_inst_name = "None in Top 100" if use_top_100 else "None Ranked"
        
        for rr, ed, inst in scoped_results:
            itype = inst.institution_type or "Private / Deemed"
            own_counts[itype] = own_counts.get(itype, 0) + 1
            if rr.nirf_score: scores.append(rr.nirf_score)
            if rr.tlr: tlrs.append(rr.tlr)
            if rr.rpc: rpcs.append(rr.rpc)
            if rr.go: gos.append(rr.go)
            if rr.oi: ois.append(rr.oi)
            if rr.perception: perceptions.append(rr.perception)
            
            if rr.nirf_rank and (best_rank is None or rr.nirf_rank < best_rank):
                best_rank = rr.nirf_rank
                top_inst_name = inst.institution_name

        avg_score = round(sum(scores) / len(scores), 2) if scores else 0
        avg_tlr = round(sum(tlrs) / len(tlrs), 1) if tlrs else 0
        avg_rpc = round(sum(rpcs) / len(rpcs), 1) if rpcs else 0
        avg_go = round(sum(gos) / len(gos), 1) if gos else 0
        avg_oi = round(sum(ois) / len(ois), 1) if ois else 0
        avg_pr = round(sum(perceptions) / len(perceptions), 1) if perceptions else 0
        
        return {
            "state_id": st.id,
            "state_name": st.state_name,
            "total_placements": len(scoped_results),
            "all_disciplines_count": len(results),
            "category_distribution": cat_counts,
            "ownership_breakdown": own_counts,
            "avg_score": avg_score,
            "avg_tlr": avg_tlr,
            "avg_rpc": avg_rpc,
            "avg_go": avg_go,
            "avg_oi": avg_oi,
            "avg_pr": avg_pr,
            "radar_scores": [avg_tlr, avg_rpc, avg_go, avg_oi, avg_pr],
            "best_rank": best_rank,
            "top_institution": top_inst_name
        }

    return {
        "year": year,
        "scope": scope,
        "category": category,
        "category_name": cat_display_name,
        "radar_labels": ["Teaching (TLR)", "Research (RPC)", "Graduation (GO)", "Outreach (OI)", "Perception (PR)"],
        "state_a": get_state_metrics(state_a_id),
        "state_b": get_state_metrics(state_b_id)
    }

# 10. GET /api/v1/benchmarking/movers
@router.get("/benchmarking/movers")
def get_movers(
    base_year: int = Query(2023),
    target_year: int = Query(2025),
    category: Optional[str] = Query(None),
    scope: str = Query("top_100"),
    db: Session = Depends(get_db)
):
    use_top_100 = (scope.lower() != "all")
    
    # State gains / losses
    all_states = db.query(State).order_by(State.state_name).all()
    state_changes = []
    
    for st in all_states:
        def count_for_year(y):
            q = db.query(RankingResult)\
                  .join(Institution, Institution.id == RankingResult.institution_id)\
                  .join(RankingEdition, RankingEdition.id == RankingResult.ranking_edition_id)\
                  .filter(Institution.state_id == st.id, RankingEdition.ranking_year == y)
            if use_top_100:
                q = q.filter(get_top_100_filter())
            if category and category.lower() not in ["all", "combined", ""]:
                q = q.filter(RankingEdition.category_slug == category.lower())
            return q.count()
            
        cnt_base = count_for_year(base_year)
        cnt_target = count_for_year(target_year)
        diff = cnt_target - cnt_base
        if cnt_base > 0 or cnt_target > 0:
            state_changes.append({
                "state_id": st.id,
                "state_name": st.state_name,
                "base_count": cnt_base,
                "target_count": cnt_target,
                "net_change": diff
            })
            
    state_changes.sort(key=lambda x: x["net_change"], reverse=True)
    
    # Fastest rising & drop-off institutions
    r_base = aliased(RankingResult)
    r_target = aliased(RankingResult)
    ed_base = aliased(RankingEdition)
    ed_target = aliased(RankingEdition)
    
    q_pairs = db.query(
        Institution.institution_name,
        State.state_name,
        ed_target.category,
        r_base.nirf_rank.label("base_rank"),
        r_target.nirf_rank.label("target_rank"),
        (r_base.nirf_rank - r_target.nirf_rank).label("jump")
    ).join(r_base, r_base.institution_id == Institution.id)\
     .join(r_target, r_target.institution_id == Institution.id)\
     .join(State, State.id == Institution.state_id)\
     .join(ed_base, ed_base.id == r_base.ranking_edition_id)\
     .join(ed_target, ed_target.id == r_target.ranking_edition_id)\
     .filter(
         ed_base.ranking_year == base_year,
         ed_target.ranking_year == target_year,
         ed_base.category_slug == ed_target.category_slug,
         r_base.nirf_rank.isnot(None),
         r_target.nirf_rank.isnot(None),
         r_base.nirf_rank <= 100,
         r_target.nirf_rank <= 100
     )

    if category and category.lower() not in ["all", "combined", ""]:
        q_pairs = q_pairs.filter(ed_target.category_slug == category.lower())

    risers_rows = q_pairs.filter((r_base.nirf_rank - r_target.nirf_rank) > 0)\
                         .order_by(desc("jump"))\
                         .limit(6).all()
                         
    dropoffs_rows = q_pairs.filter((r_base.nirf_rank - r_target.nirf_rank) < 0)\
                           .order_by("jump")\
                           .limit(6).all()

    return {
        "base_year": base_year,
        "target_year": target_year,
        "state_changes": state_changes,
        "fastest_risers": [
            {
                "institution_name": r[0],
                "state_name": r[1],
                "category": r[2],
                "base_rank": r[3],
                "target_rank": r[4],
                "jump": r[5]
            } for r in risers_rows
        ],
        "fastest_dropoffs": [
            {
                "institution_name": r[0],
                "state_name": r[1],
                "category": r[2],
                "base_rank": r[3],
                "target_rank": r[4],
                "jump": abs(r[5])
            } for r in dropoffs_rows
        ]
    }

# 11. GET /api/v1/export/state-brief
@router.get("/export/state-brief")
def get_state_brief(
    state_id: int = Query(...),
    year: int = Query(settings.DEFAULT_YEAR),
    scope: str = Query("top_100"),
    db: Session = Depends(get_db)
):
    use_top_100 = (scope.lower() != "all")
    st = db.query(State).filter_by(id=state_id).first()
    if not st:
        raise HTTPException(status_code=404, detail="State not found")

    q = db.query(RankingResult, RankingEdition, Institution)\
          .join(Institution, Institution.id == RankingResult.institution_id)\
          .join(RankingEdition, RankingEdition.id == RankingResult.ranking_edition_id)\
          .filter(Institution.state_id == state_id, RankingEdition.ranking_year == year)

    if use_top_100:
        q = q.filter(get_top_100_filter())

    results = q.order_by(
        func.coalesce(RankingResult.nirf_rank, 9999).asc(),
        RankingResult.nirf_score.desc().nullslast()
    ).all()

    inst_data = []
    own_counts = {"Central": 0, "State Public": 0, "Private / Deemed": 0}
    cat_counts = {c["name"]: 0 for c in settings.SUPPORTED_CATEGORIES}
    scores, tlrs, rpcs = [], [], []

    for rr, ed, inst in results:
        itype = inst.institution_type or "Private / Deemed"
        own_counts[itype] = own_counts.get(itype, 0) + 1
        cat_counts[ed.category] = cat_counts.get(ed.category, 0) + 1
        if rr.nirf_score: scores.append(rr.nirf_score)
        if rr.tlr: tlrs.append(rr.tlr)
        if rr.rpc: rpcs.append(rr.rpc)

        inst_data.append({
            "institution_name": inst.institution_name,
            "category": ed.category,
            "rank": rr.rank_display,
            "score": rr.nirf_score,
            "city": inst.city or "—",
            "institution_type": itype,
            "tlr": rr.tlr,
            "rpc": rr.rpc,
            "go": rr.go,
            "oi": rr.oi,
            "perception": rr.perception,
            "source_url": rr.source_url
        })

    return {
        "state_id": st.id,
        "state_name": st.state_name,
        "year": year,
        "scope": scope,
        "summary": {
            "total_institutions": len(inst_data),
            "best_rank": inst_data[0]["rank"] if inst_data else "N/A",
            "top_institution": inst_data[0]["institution_name"] if inst_data else "N/A",
            "avg_score": round(sum(scores) / len(scores), 2) if scores else 0,
            "avg_tlr": round(sum(tlrs) / len(tlrs), 2) if tlrs else 0,
            "avg_rpc": round(sum(rpcs) / len(rpcs), 2) if rpcs else 0,
        },
        "category_breakdown": cat_counts,
        "ownership_breakdown": own_counts,
        "institutions": inst_data
    }

# 9. GET /api/v1/admin/imports
@router.get("/admin/imports", response_model=List[ImportBatchResponse])
def get_import_batches(db: Session = Depends(get_db)):
    batches = db.query(ImportBatch).order_by(desc(ImportBatch.created_at)).all()
    return batches

# 10. POST /api/v1/admin/import
@router.post("/admin/import")
async def import_dataset(
    file: UploadFile = File(...),
    category: str = Form(...),
    ranking_year: int = Form(...),
    db: Session = Depends(get_db)
):
    contents = await file.read()
    filename = file.filename

    try:
        if filename.endswith(".csv"):
            df = pd.read_csv(io.BytesIO(contents))
        elif filename.endswith(".xlsx") or filename.endswith(".xls"):
            df = pd.read_excel(io.BytesIO(contents))
        else:
            raise HTTPException(status_code=400, detail="Only .xlsx, .xls and .csv files are supported")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read file: {str(e)}")

    # Column detection
    col_map = {}
    for c in df.columns:
        cl = str(c).lower().strip()
        if 'rank' in cl and 'band' not in cl: col_map['rank'] = c
        elif 'name' in cl: col_map['name'] = c
        elif 'city' in cl: col_map['city'] = c
        elif 'state' in cl: col_map['state'] = c
        elif 'score' in cl and 'tlr' not in cl: col_map['score'] = c
        elif 'id' in cl: col_map['id'] = c

    if 'name' not in col_map:
        raise HTTPException(status_code=400, detail="Required column 'Institute Name' could not be automatically detected")

    # Lookup or create edition
    cat_slug = category.lower().strip().replace(" ", "_")
    edition = db.query(RankingEdition).filter_by(ranking_year=ranking_year, category_slug=cat_slug).first()
    if not edition:
        edition = RankingEdition(
            ranking_year=ranking_year,
            category=category.title(),
            category_slug=cat_slug,
            maximum_rank=200,
            data_status="verified"
        )
        db.add(edition)
        db.flush()

    imported_cnt = 0
    rejected_cnt = 0

    state_cache = {s.state_name.lower(): s.id for s in db.query(State).all()}
    unknown_state_id = state_cache.get("unknown", 1)

    for _, row in df.iterrows():
        name_val = str(row[col_map['name']]).strip() if pd.notna(row[col_map['name']]) else ''
        if not name_val or name_val.lower() == 'nan':
            rejected_cnt += 1
            continue

        st_val = str(row[col_map.get('state')]).strip() if col_map.get('state') and pd.notna(row[col_map.get('state')]) else ''
        st_id = state_cache.get(st_val.lower(), unknown_state_id)

        city_val = str(row[col_map.get('city')]).strip() if col_map.get('city') and pd.notna(row[col_map.get('city')]) else ''
        id_val = str(row[col_map.get('id')]).strip() if col_map.get('id') and pd.notna(row[col_map.get('id')]) else ''
        rank_val = str(row[col_map.get('rank')]).strip() if col_map.get('rank') and pd.notna(row[col_map.get('rank')]) else 'N/A'

        is_band = ('-' in rank_val) or not rank_val.isdigit()
        rn = int(rank_val) if (not is_band and rank_val.isdigit()) else None

        score_val = None
        if col_map.get('score') and pd.notna(row[col_map.get('score')]):
            try:
                score_val = float(row[col_map.get('score')])
            except:
                pass

        # Upsert institution
        inst = db.query(Institution).filter_by(institution_name=name_val, state_id=st_id).first()
        if not inst:
            inst = Institution(institution_name=name_val, nirf_institute_id=id_val, city=city_val, state_id=st_id)
            db.add(inst)
            db.flush()

        rr = RankingResult(
            institution_id=inst.id,
            ranking_edition_id=edition.id,
            nirf_rank=rn,
            rank_display=rank_val,
            is_rank_band=is_band,
            nirf_score=score_val,
            verification_status="verified"
        )
        db.add(rr)
        imported_cnt += 1

    batch = ImportBatch(
        filename=filename,
        category=category,
        ranking_year=ranking_year,
        records_imported=imported_cnt,
        records_rejected=rejected_cnt,
        import_status="completed"
    )
    db.add(batch)
    db.commit()

    return {
        "status": "success",
        "message": f"Successfully imported {imported_cnt} records into {category} ({ranking_year})",
        "records_imported": imported_cnt,
        "records_rejected": rejected_cnt
    }

# Export helper
@router.get("/export")
def export_dataset(
    format: str = Query("csv"), # "csv" or "xlsx"
    year: int = Query(settings.DEFAULT_YEAR),
    category: str = Query("overall"),
    state_id: Optional[int] = Query(None),
    scope: str = Query("top_100"),
    top_100_only: Optional[bool] = Query(None),
    db: Session = Depends(get_db)
):
    use_top_100 = True
    if (scope and scope.lower() == "all") or top_100_only is False:
        use_top_100 = False

    cat_slug = category.lower().strip().replace(" ", "_")
    edition = db.query(RankingEdition).filter(
        RankingEdition.ranking_year == year,
        (RankingEdition.category_slug == cat_slug) | (func.lower(RankingEdition.category) == category.lower().strip())
    ).first()

    if not edition:
        raise HTTPException(status_code=404, detail="Edition not found")

    q = db.query(RankingResult, Institution, State)\
          .join(Institution, Institution.id == RankingResult.institution_id)\
          .join(State, State.id == Institution.state_id)\
          .filter(RankingResult.ranking_edition_id == edition.id)

    if use_top_100:
        q = q.filter(get_top_100_filter())

    if state_id:
        q = q.filter(Institution.state_id == state_id)

    results = q.order_by(
        func.coalesce(RankingResult.nirf_rank, 9999).asc(),
        RankingResult.nirf_score.desc().nullslast()
    ).all()

    headers = ["Year", "Category", "Rank", "Institute ID", "Institution Name", "City", "State", "Score", "TLR", "RPC", "GO", "OI", "Perception"]
    rows = []
    for rr, inst, st in results:
        rows.append([
            edition.ranking_year,
            edition.category,
            rr.rank_display,
            inst.nirf_institute_id or "",
            inst.institution_name,
            inst.city or "",
            st.state_name,
            rr.nirf_score or "",
            rr.tlr or "",
            rr.rpc or "",
            rr.go or "",
            rr.oi or "",
            rr.perception or ""
        ])

    filename_base = f"NIRF_{year}_{cat_slug}"
    if format.lower() == "csv":
        out = io.StringIO()
        w = csv.writer(out)
        w.writerow(headers)
        w.writerows(rows)
        return StreamingResponse(
            io.BytesIO(out.getvalue().encode('utf-8-sig')),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename_base}.csv"}
        )
    else:
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = cat_slug[:25]
        ws.append(headers)
        for r in rows:
            ws.append(r)
        out_stream = io.BytesIO()
        wb.save(out_stream)
        out_stream.seek(0)
        return StreamingResponse(
            out_stream,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename_base}.xlsx"}
        )
