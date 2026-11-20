import os
import sqlite3
import io
import csv
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import openpyxl

DB_PATH = os.path.join(os.path.dirname(__file__), "nirf_insights.db")

app = FastAPI(
    title="NIRF Insight: India State-wise Distribution Dashboard API",
    description="Full-Stack Backend API for NIRF 2023-2025 Rankings Analytics",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@app.get("/api/categories")
def get_categories():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT code, name, display_order, description, icon FROM categories ORDER BY display_order ASC;")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows

@app.get("/api/years")
def get_years():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT year, is_default, is_available FROM ranking_years ORDER BY year DESC;")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows

@app.get("/api/coverage")
def get_coverage():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT category_code, year, is_available, top_ranked_count, rank_bands_count,
               total_institutions, highest_score, rank_1_institution, note
        FROM category_coverage
        ORDER BY year DESC, category_code;
    """)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows

@app.get("/api/stats")
def get_stats(year: int = Query(2025), category: str = Query("overall")):
    conn = get_db()
    cur = conn.cursor()
    
    # Check coverage
    cur.execute("""
        SELECT is_available, note FROM category_coverage
        WHERE category_code = ? AND year = ?;
    """, (category, year))
    cov = cur.fetchone()
    if cov and not cov['is_available']:
        conn.close()
        return {
            'is_available': False,
            'note': cov['note'],
            'total_institutions': 0,
            'top_ranked_count': 0,
            'rank_bands_count': 0,
            'states_represented': 0,
            'leading_state': 'N/A',
            'leading_state_count': 0,
            'highest_ranked_institution': 'N/A',
            'highest_score': None
        }
        
    # Total institutions & breakdown
    cur.execute("""
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN is_rank_band = 0 THEN 1 ELSE 0 END) as top_ranked,
            SUM(CASE WHEN is_rank_band = 1 THEN 1 ELSE 0 END) as rank_bands,
            COUNT(DISTINCT state) as states_count
        FROM rankings
        WHERE year = ? AND category_code = ?;
    """, (year, category))
    counts = dict(cur.fetchone())
    
    # Leading State
    cur.execute("""
        SELECT state, COUNT(*) as cnt
        FROM rankings
        WHERE year = ? AND category_code = ?
        GROUP BY state
        ORDER BY cnt DESC
        LIMIT 1;
    """, (year, category))
    leading = cur.fetchone()
    leading_state = leading['state'] if leading else 'N/A'
    leading_count = leading['cnt'] if leading else 0
    
    # Highest ranked institution
    cur.execute("""
        SELECT institute_name, score, rank_display
        FROM rankings
        WHERE year = ? AND category_code = ? AND rank_num = 1
        LIMIT 1;
    """, (year, category))
    top_inst = cur.fetchone()
    
    conn.close()
    return {
        'is_available': True,
        'note': cov['note'] if cov else '',
        'total_institutions': counts['total'] or 0,
        'top_ranked_count': counts['top_ranked'] or 0,
        'rank_bands_count': counts['rank_bands'] or 0,
        'states_represented': counts['states_count'] or 0,
        'leading_state': leading_state,
        'leading_state_count': leading_count,
        'highest_ranked_institution': top_inst['institute_name'] if top_inst else 'N/A',
        'highest_score': top_inst['score'] if top_inst else None
    }

@app.get("/api/map-data")
def get_map_data(year: int = Query(2025), category: str = Query("overall")):
    conn = get_db()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT state, COUNT(*) as count,
               SUM(CASE WHEN is_rank_band = 0 THEN 1 ELSE 0 END) as top_count,
               SUM(CASE WHEN is_rank_band = 1 THEN 1 ELSE 0 END) as band_count,
               AVG(score) as avg_score,
               MAX(score) as max_score
        FROM rankings
        WHERE year = ? AND category_code = ?
        GROUP BY state
        ORDER BY count DESC;
    """, (year, category))
    rows = cur.fetchall()
    
    result = {}
    for r in rows:
        st = r['state']
        # Top institution in this state
        cur.execute("""
            SELECT institute_name, rank_display, score
            FROM rankings
            WHERE year = ? AND category_code = ? AND state = ?
            ORDER BY CASE WHEN rank_num IS NULL THEN 9999 ELSE rank_num END ASC, score DESC
            LIMIT 1;
        """, (year, category, st))
        top_inst = cur.fetchone()
        
        result[st] = {
            'count': r['count'],
            'top_count': r['top_count'],
            'band_count': r['band_count'],
            'avg_score': round(r['avg_score'], 2) if r['avg_score'] else None,
            'max_score': round(r['max_score'], 2) if r['max_score'] else None,
            'top_institution': top_inst['institute_name'] if top_inst else 'N/A',
            'top_institution_rank': top_inst['rank_display'] if top_inst else 'N/A',
            'top_institution_score': top_inst['score'] if top_inst else None
        }
        
    conn.close()
    return result

@app.get("/api/leaderboard")
def get_leaderboard(year: int = Query(2025), category: str = Query("overall")):
    conn = get_db()
    cur = conn.cursor()
    
    # Total count for percentage
    cur.execute("SELECT COUNT(*) FROM rankings WHERE year = ? AND category_code = ?;", (year, category))
    total = cur.fetchone()[0] or 1
    
    cur.execute("""
        SELECT state, COUNT(*) as total_institutions,
               SUM(CASE WHEN is_rank_band = 0 THEN 1 ELSE 0 END) as top_tier_count,
               SUM(CASE WHEN is_rank_band = 1 THEN 1 ELSE 0 END) as band_tier_count,
               AVG(score) as avg_score,
               MAX(score) as top_score
        FROM rankings
        WHERE year = ? AND category_code = ?
        GROUP BY state
        ORDER BY total_institutions DESC, top_score DESC;
    """, (year, category))
    state_rows = cur.fetchall()
    
    leaderboard = []
    for rank_idx, r in enumerate(state_rows, 1):
        st = r['state']
        # Top institution in state
        cur.execute("""
            SELECT institute_name, rank_display, score
            FROM rankings
            WHERE year = ? AND category_code = ? AND state = ?
            ORDER BY CASE WHEN rank_num IS NULL THEN 9999 ELSE rank_num END ASC, score DESC
            LIMIT 1;
        """, (year, category, st))
        top_inst = cur.fetchone()
        
        cnt = r['total_institutions']
        share_pct = round((cnt / total) * 100, 1)
        
        leaderboard.append({
            'state_rank': rank_idx,
            'state': st,
            'count': cnt,
            'top_count': r['top_tier_count'],
            'band_count': r['band_tier_count'],
            'share_pct': share_pct,
            'avg_score': round(r['avg_score'], 2) if r['avg_score'] else None,
            'top_score': round(r['top_score'], 2) if r['top_score'] else None,
            'top_institution': top_inst['institute_name'] if top_inst else 'N/A',
            'top_rank': top_inst['rank_display'] if top_inst else 'N/A'
        })
        
    conn.close()
    return leaderboard

@app.get("/api/institutions")
def get_institutions(
    year: int = Query(2025),
    category: str = Query("overall"),
    state: str = Query(None),
    search: str = Query(None),
    tier: str = Query("all") # "all", "top", "band"
):
    conn = get_db()
    cur = conn.cursor()
    
    query = """
        SELECT id, year, category_code, institute_id, institute_name, city, state,
               rank_num, rank_display, is_rank_band, is_tied, score, tlr, rpc, go, oi, perception, report_pdf
        FROM rankings
        WHERE year = ? AND category_code = ?
    """
    params = [year, category]
    
    if state and state.lower() != 'all':
        query += " AND state = ?"
        params.append(state)
        
    if tier == "top":
        query += " AND is_rank_band = 0"
    elif tier == "band":
        query += " AND is_rank_band = 1"
        
    if search and search.strip():
        term = f"%{search.strip().lower()}%"
        query += " AND (LOWER(institute_name) LIKE ? OR LOWER(city) LIKE ? OR LOWER(state) LIKE ? OR LOWER(institute_id) LIKE ?)"
        params.extend([term, term, term, term])
        
    query += " ORDER BY CASE WHEN rank_num IS NULL THEN 9999 ELSE rank_num END ASC, score DESC, institute_name ASC;"
    
    cur.execute(query, params)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows

@app.get("/api/institution-detail")
def get_institution_detail(name: str = Query(...)):
    conn = get_db()
    cur = conn.cursor()
    
    # Get multi-year records for this institution across categories
    cur.execute("""
        SELECT year, category_code, institute_id, institute_name, city, state,
               rank_num, rank_display, is_rank_band, score, tlr, rpc, go, oi, perception, report_pdf
        FROM rankings
        WHERE LOWER(institute_name) = LOWER(?)
        ORDER BY year DESC, category_code ASC;
    """, (name.strip(),))
    history = [dict(r) for r in cur.fetchall()]
    
    if not history:
        # Partial fallback match
        cur.execute("""
            SELECT year, category_code, institute_id, institute_name, city, state,
                   rank_num, rank_display, is_rank_band, score, tlr, rpc, go, oi, perception, report_pdf
            FROM rankings
            WHERE LOWER(institute_name) LIKE ?
            ORDER BY year DESC, category_code ASC;
        """, (f"%{name.strip().lower()}%",))
        history = [dict(r) for r in cur.fetchall()]
        
    conn.close()
    if not history:
        raise HTTPException(status_code=404, detail="Institution not found")
        
    return {
        'name': history[0]['institute_name'],
        'city': history[0]['city'],
        'state': history[0]['state'],
        'institute_id': history[0]['institute_id'],
        'records': history
    }

@app.get("/api/charts/category-comparison")
def get_category_comparison(year: int = Query(2025)):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT c.code, c.name,
               COALESCE(cov.total_institutions, 0) as total,
               COALESCE(cov.top_ranked_count, 0) as top_ranked,
               COALESCE(cov.rank_bands_count, 0) as rank_bands,
               COALESCE(cov.highest_score, 0) as highest_score,
               cov.is_available,
               cov.rank_1_institution
        FROM categories c
        LEFT JOIN category_coverage cov ON c.code = cov.category_code AND cov.year = ?
        ORDER BY c.display_order;
    """, (year,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows

@app.get("/api/charts/top-parameters")
def get_top_parameters(year: int = Query(2025), category: str = Query("overall"), limit: int = Query(5)):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT institute_name, rank_display, score, tlr, rpc, go, oi, perception
        FROM rankings
        WHERE year = ? AND category_code = ? AND rank_num IS NOT NULL AND tlr IS NOT NULL
        ORDER BY rank_num ASC
        LIMIT ?;
    """, (year, category, limit))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows

@app.get("/api/validation-report")
def get_validation_report_api():
    conn = get_db()
    cur = conn.cursor()
    
    cur.execute("SELECT COUNT(*) FROM rankings;")
    total_ranks = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(*) FROM institutions;")
    total_insts = cur.fetchone()[0]
    
    cur.execute("SELECT severity, COUNT(*) FROM validation_logs GROUP BY severity;")
    severities = dict(cur.fetchall())
    
    cur.execute("SELECT issue_type, COUNT(*) FROM validation_logs GROUP BY issue_type ORDER BY COUNT(*) DESC;")
    issue_types = dict(cur.fetchall())
    
    cur.execute("""
        SELECT year, category_code, record_identifier, issue_type, severity, issue_detail, action_taken
        FROM validation_logs
        ORDER BY id ASC;
    """)
    logs = [dict(r) for r in cur.fetchall()]
    
    conn.close()
    return {
        'total_rankings': total_ranks,
        'unique_institutions': total_insts,
        'total_logs': len(logs),
        'severity_counts': severities,
        'issue_type_counts': issue_types,
        'recent_logs': logs[:50]
    }

@app.get("/api/export")
def export_data(
    format: str = Query("csv"), # "csv" or "xlsx"
    year: int = Query(2025),
    category: str = Query("overall"),
    state: str = Query(None)
):
    conn = get_db()
    cur = conn.cursor()
    
    query = """
        SELECT year, category_code, rank_display, institute_id, institute_name, city, state,
               score, tlr, rpc, go, oi, perception, report_pdf
        FROM rankings
        WHERE year = ? AND category_code = ?
    """
    params = [year, category]
    if state and state.lower() != 'all':
        query += " AND state = ?"
        params.append(state)
        
    query += " ORDER BY CASE WHEN rank_num IS NULL THEN 9999 ELSE rank_num END ASC, score DESC;"
    cur.execute(query, params)
    rows = cur.fetchall()
    conn.close()
    
    headers = [
        "Year", "Category", "Rank", "Institute ID", "Institute Name", "City", "State",
        "Overall Score", "TLR (100)", "RPC (100)", "GO (100)", "OI (100)", "Perception (100)", "Report PDF"
    ]
    
    filename_base = f"NIRF_{year}_{category}"
    if state and state.lower() != 'all':
        filename_base += f"_{state.replace(' ', '_')}"
        
    if format.lower() == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(headers)
        for r in rows:
            writer.writerow(list(r))
        output.seek(0)
        return StreamingResponse(
            io.BytesIO(output.getvalue().encode('utf-8-sig')),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename_base}.csv"}
        )
    else:
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = f"{category[:25]}"
        ws.append(headers)
        for r in rows:
            ws.append(list(r))
        out_stream = io.BytesIO()
        wb.save(out_stream)
        out_stream.seek(0)
        return StreamingResponse(
            out_stream,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename_base}.xlsx"}
        )

@app.get("/india_states.geojson")
def get_india_geojson():
    geojson_path = os.path.join(os.path.dirname(__file__), "india_states.geojson")
    if os.path.exists(geojson_path):
        return FileResponse(geojson_path, media_type="application/json")
    raise HTTPException(status_code=404, detail="GeoJSON not found")

# Serve frontend static assets from current directory
app.mount("/static", StaticFiles(directory=os.path.dirname(__file__)), name="static")

@app.get("/")
def serve_dashboard():
    index_path = os.path.join(os.path.dirname(__file__), "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path, media_type="text/html")
    return HTMLResponse("<h1>Dashboard index.html not found</h1>", status_code=404)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
