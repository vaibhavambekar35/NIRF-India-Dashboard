import requests
from bs4 import BeautifulSoup
import copy
import re
import os
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Referer': 'https://www.nirfindia.org/',
}

# State name canonical normalization dictionary mapping to India GeoJSON ST_NM
STATE_NORMALIZATION = {
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

def normalize_state_name(raw_state):
    if not raw_state:
        return 'Unknown'
    cleaned = raw_state.strip().lower()
    return STATE_NORMALIZATION.get(cleaned, raw_state.strip())

YEAR_CONFIGS = {
    2024: [
        {
            'category': 'Overall',
            'sheet_name': 'Overall',
            'main_url': 'https://www.nirfindia.org/Rankings/2024/OverallRanking.html',
            'bands': [
                ('101-150', 'https://www.nirfindia.org/Rankings/2024/OverallRanking150.html'),
                ('151-200', 'https://www.nirfindia.org/Rankings/2024/OverallRanking200.html')
            ]
        },
        {
            'category': 'Universities',
            'sheet_name': 'Universities',
            'main_url': 'https://www.nirfindia.org/Rankings/2024/UniversityRanking.html',
            'bands': [
                ('101-150', 'https://www.nirfindia.org/Rankings/2024/UniversityRanking150.html'),
                ('151-200', 'https://www.nirfindia.org/Rankings/2024/UniversityRanking200.html')
            ]
        },
        {
            'category': 'Engineering',
            'sheet_name': 'Engineering',
            'main_url': 'https://www.nirfindia.org/Rankings/2024/EngineeringRanking.html',
            'bands': [
                ('101-150', 'https://www.nirfindia.org/Rankings/2024/EngineeringRanking150.html'),
                ('151-200', 'https://www.nirfindia.org/Rankings/2024/EngineeringRanking200.html'),
                ('201-300', 'https://www.nirfindia.org/Rankings/2024/EngineeringRanking300.html')
            ]
        },
        {
            'category': 'Management',
            'sheet_name': 'Management',
            'main_url': 'https://www.nirfindia.org/Rankings/2024/ManagementRanking.html',
            'bands': [
                ('101-125', 'https://www.nirfindia.org/Rankings/2024/ManagementRanking150.html')
            ]
        },
        {
            'category': 'Medical',
            'sheet_name': 'Medical',
            'main_url': 'https://www.nirfindia.org/Rankings/2024/MedicalRanking.html',
            'bands': []
        },
        {
            'category': 'State Public University',
            'sheet_name': 'State Public University',
            'main_url': 'https://www.nirfindia.org/Rankings/2024/STATEPUBLICUNIVERSITYRanking.html',
            'bands': [
                ('51-100', 'https://www.nirfindia.org/Rankings/2024/STATEPUBLICUNIVERSITYRanking100.html')
            ]
        }
    ],
    2023: [
        {
            'category': 'Overall',
            'sheet_name': 'Overall',
            'main_url': 'https://www.nirfindia.org/Rankings/2023/OverallRanking.html',
            'bands': [
                ('101-150', 'https://www.nirfindia.org/Rankings/2023/OverallRanking150.html'),
                ('151-200', 'https://www.nirfindia.org/Rankings/2023/OverallRanking200.html')
            ]
        },
        {
            'category': 'Universities',
            'sheet_name': 'Universities',
            'main_url': 'https://www.nirfindia.org/Rankings/2023/UniversityRanking.html',
            'bands': [
                ('101-150', 'https://www.nirfindia.org/Rankings/2023/UniversityRanking150.html'),
                ('151-200', 'https://www.nirfindia.org/Rankings/2023/UniversityRanking200.html')
            ]
        },
        {
            'category': 'Engineering',
            'sheet_name': 'Engineering',
            'main_url': 'https://www.nirfindia.org/Rankings/2023/EngineeringRanking.html',
            'bands': [
                ('101-150', 'https://www.nirfindia.org/Rankings/2023/EngineeringRanking150.html'),
                ('151-200', 'https://www.nirfindia.org/Rankings/2023/EngineeringRanking200.html')
            ]
        },
        {
            'category': 'Management',
            'sheet_name': 'Management',
            'main_url': 'https://www.nirfindia.org/Rankings/2023/ManagementRanking.html',
            'bands': [
                ('101-125', 'https://www.nirfindia.org/Rankings/2023/ManagementRanking150.html')
            ]
        },
        {
            'category': 'Medical',
            'sheet_name': 'Medical',
            'main_url': 'https://www.nirfindia.org/Rankings/2023/MedicalRanking.html',
            'bands': []
        }
        # Note: State Public University did not exist in 2023 NIRF
    ]
}

def scrape_main_table(url, category, year):
    print(f"Scraping [{year}] {category} from {url}...")
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        if r.status_code != 200:
            print(f"  Status {r.status_code} for {url}")
            return []
    except Exception as e:
        print(f"  Error fetching {url}: {e}")
        return []
        
    soup = BeautifulSoup(r.text, 'html.parser')
    tbl = soup.find('table', {'id': 'tbl_overall'})
    if not tbl:
        tbl = soup.find('table')
    if not tbl:
        return []
    
    tbody = tbl.find('tbody')
    trs = tbody.find_all('tr', recursive=False) if tbody else []
    records = []
    
    for tr in trs:
        tds = tr.find_all('td', recursive=False)
        if len(tds) < 6:
            continue
        
        inst_id = tds[0].get_text(strip=True)
        td1 = tds[1]
        
        # Sub-parameter scores
        hidden = td1.find('div', class_='tbl_hidden')
        params = {}
        if hidden:
            th_cells = [th.get_text(strip=True) for th in hidden.find_all('th')]
            td_cells = [td.get_text(strip=True) for td in hidden.find_all('td')]
            params = dict(zip(th_cells, td_cells))
            
        pdf_a = td1.find('a', href=lambda h: h and h.endswith('.pdf'))
        pdf_url = pdf_a['href'] if pdf_a else ''
        
        td1_clone = copy.copy(td1)
        for div in td1_clone.find_all('div'):
            div.decompose()
        name = td1_clone.get_text(' ', strip=True)
        name = re.sub(r'\s+', ' ', name).strip()
        
        city = re.sub(r'\s+', ' ', tds[2].get_text(strip=True))
        state_raw = re.sub(r'\s+', ' ', tds[3].get_text(strip=True))
        state_norm = normalize_state_name(state_raw)
        
        score_str = tds[4].get_text(strip=True)
        rank_str = tds[5].get_text(strip=True)
        
        try:
            score_val = float(score_str)
        except:
            score_val = score_str
            
        def parse_float(val):
            try:
                return float(val)
            except:
                return None

        records.append({
            'Year': year,
            'Category': category,
            'Rank': int(rank_str) if rank_str.isdigit() else rank_str,
            'Rank Display': rank_str,
            'Is Rank Band': False,
            'Institute ID': inst_id,
            'Name': name,
            'City': city,
            'State': state_norm,
            'State Raw': state_raw,
            'Score': score_val,
            'TLR (100)': parse_float(params.get('TLR (100)')),
            'RPC (100)': parse_float(params.get('RPC (100)')),
            'GO (100)': parse_float(params.get('GO (100)')),
            'OI (100)': parse_float(params.get('OI (100)')),
            'Perception (100)': parse_float(params.get('PERCEPTION (100)')),
            'Report PDF': pdf_url,
            'Source File': f'NIRF_{year}_{category.replace(" ", "_")}.html'
        })
    return records

def scrape_rank_band(url, category, year, band_name):
    print(f"Scraping [{year}] {category} band {band_name} from {url}...")
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        if r.status_code != 200:
            return []
    except Exception as e:
        print(f"  Error fetching band {url}: {e}")
        return []
        
    soup = BeautifulSoup(r.text, 'html.parser')
    tbl = soup.find('table')
    if not tbl:
        return []
    
    tbody = tbl.find('tbody')
    trs = tbody.find_all('tr', recursive=False) if tbody else tbl.find_all('tr')
    records = []
    
    for tr in trs:
        tds = tr.find_all(['td', 'th'], recursive=False)
        if len(tds) < 3:
            continue
        
        name = re.sub(r'\s+', ' ', tds[0].get_text(strip=True))
        city = re.sub(r'\s+', ' ', tds[1].get_text(strip=True))
        state_raw = re.sub(r'\s+', ' ', tds[2].get_text(strip=True))
        state_norm = normalize_state_name(state_raw)
        
        records.append({
            'Year': year,
            'Category': category,
            'Rank': band_name,
            'Rank Display': band_name,
            'Is Rank Band': True,
            'Institute ID': '',
            'Name': name,
            'City': city,
            'State': state_norm,
            'State Raw': state_raw,
            'Score': None,
            'TLR (100)': None,
            'RPC (100)': None,
            'GO (100)': None,
            'OI (100)': None,
            'Perception (100)': None,
            'Report PDF': '',
            'Source File': f'NIRF_{year}_{category.replace(" ", "_")}_{band_name}.html'
        })
    return records

def build_excel_for_year(year):
    configs = YEAR_CONFIGS[year]
    output_filename = f"NIRF_India_Rankings_{year}.xlsx"
    print(f"\n==========================================")
    print(f"Building Excel for Year {year}: {output_filename}")
    print(f"==========================================")
    
    wb = openpyxl.Workbook()
    default_sheet = wb.active
    
    header_fill = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    subhead_fill = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
    subhead_font = Font(name="Calibri", size=11, bold=True, color="000000")
    band_row_fill = PatternFill(start_color="F2F4F7", end_color="F2F4F7", fill_type="solid")
    title_fill = PatternFill(start_color="0D233A", end_color="0D233A", fill_type="solid")
    title_font = Font(name="Calibri", size=15, bold=True, color="FFFFFF")
    regular_font = Font(name="Calibri", size=10)
    bold_font = Font(name="Calibri", size=10, bold=True)
    link_font = Font(name="Calibri", size=10, color="0563C1", underline="single")
    thin_border_side = Side(border_style="thin", color="D9D9D9")
    thin_border = Border(left=thin_border_side, right=thin_border_side, top=thin_border_side, bottom=thin_border_side)
    
    align_center = Alignment(horizontal="center", vertical="center")
    align_left = Alignment(horizontal="left", vertical="center")
    align_right = Alignment(horizontal="right", vertical="center")
    
    all_combined = []
    category_data = {}
    summary_stats = []
    
    for cfg in configs:
        cat = cfg['category']
        main_recs = scrape_main_table(cfg['main_url'], cat, year)
        band_recs = []
        for b_name, b_url in cfg['bands']:
            band_recs.extend(scrape_rank_band(b_url, cat, year, b_name))
            
        full = main_recs + band_recs
        category_data[cat] = full
        all_combined.extend(full)
        
        summary_stats.append({
            'Category': cat,
            'Top Ranked': len(main_recs),
            'Rank Bands': len(band_recs),
            'Total': len(full),
            'Rank 1': main_recs[0]['Name'] if main_recs else 'N/A',
            'Top Score': main_recs[0]['Score'] if main_recs else 'N/A'
        })
        
    # Summary Sheet
    ws_sum = wb.create_sheet(title="Overview & Summary")
    ws_sum.views.sheetView[0].showGridLines = True
    ws_sum.merge_cells("A1:F2")
    ws_sum["A1"].value = f"NATIONAL INSTITUTIONAL RANKING FRAMEWORK (NIRF) {year}"
    ws_sum["A1"].font = title_font
    ws_sum["A1"].fill = title_fill
    ws_sum["A1"].alignment = align_center
    ws_sum["A3"].value = f"Official Portal Data: https://www.nirfindia.org/Rankings/{year}/Ranking.html"
    ws_sum["A3"].font = Font(name="Calibri", size=10, italic=True, color="595959")
    
    headers_sum = ["Category", "Top Ranked (1-100/50)", "Rank Bands", "Total Institutes", "Rank #1 Institution", "Top Score"]
    r_idx = 5
    for c_i, h in enumerate(headers_sum, 1):
        c = ws_sum.cell(row=r_idx, column=c_i, value=h)
        c.font = header_font
        c.fill = header_fill
        c.alignment = align_center
        c.border = thin_border
        
    for s in summary_stats:
        r_idx += 1
        ws_sum.cell(row=r_idx, column=1, value=s['Category']).alignment = align_left
        ws_sum.cell(row=r_idx, column=2, value=s['Top Ranked']).alignment = align_center
        ws_sum.cell(row=r_idx, column=3, value=s['Rank Bands']).alignment = align_center
        ws_sum.cell(row=r_idx, column=4, value=s['Total']).alignment = align_center
        ws_sum.cell(row=r_idx, column=5, value=s['Rank 1']).alignment = align_left
        sc = ws_sum.cell(row=r_idx, column=6, value=s['Top Score'])
        sc.alignment = align_center
        if isinstance(s['Top Score'], (int, float)):
            sc.number_format = "0.00"
        for c_i in range(1, 7):
            c = ws_sum.cell(row=r_idx, column=c_i)
            c.font = regular_font
            c.border = thin_border
            
    # If 2023, add note that State Public University was not yet introduced
    if year == 2023:
        r_idx += 1
        ws_sum.cell(row=r_idx, column=1, value="State Public University").alignment = align_left
        ws_sum.cell(row=r_idx, column=2, value="N/A").alignment = align_center
        ws_sum.cell(row=r_idx, column=3, value="N/A").alignment = align_center
        ws_sum.cell(row=r_idx, column=4, value="N/A").alignment = align_center
        ws_sum.cell(row=r_idx, column=5, value="Category not introduced until 2024").alignment = align_left
        ws_sum.cell(row=r_idx, column=6, value="N/A").alignment = align_center
        for c_i in range(1, 7):
            c = ws_sum.cell(row=r_idx, column=c_i)
            c.font = Font(name="Calibri", size=10, italic=True, color="7F7F7F")
            c.border = thin_border
            
    ws_sum.column_dimensions['A'].width = 28
    ws_sum.column_dimensions['B'].width = 30
    ws_sum.column_dimensions['C'].width = 16
    ws_sum.column_dimensions['D'].width = 18
    ws_sum.column_dimensions['E'].width = 46
    ws_sum.column_dimensions['F'].width = 14
    
    # Populate function
    def populate(ws, records, include_cat=False):
        ws.views.sheetView[0].showGridLines = True
        cols = []
        if include_cat:
            cols.append("Category")
        cols.extend([
            "Rank", "Institute ID", "Institute Name", "City", "State",
            "Score", "TLR (100)", "RPC (100)", "GO (100)", "OI (100)", "Perception (100)", "Report PDF"
        ])
        for c_i, h in enumerate(cols, 1):
            c = ws.cell(row=1, column=c_i, value=h)
            c.font = header_font
            c.fill = header_fill
            c.alignment = align_center
            c.border = thin_border
            
        for r_i, r in enumerate(records, 2):
            pos = 1
            if include_cat:
                ws.cell(row=r_i, column=pos, value=r['Category']).alignment = align_left
                pos += 1
            ws.cell(row=r_i, column=pos, value=r['Rank']).alignment = align_center
            pos += 1
            ws.cell(row=r_i, column=pos, value=r['Institute ID']).alignment = align_center
            pos += 1
            ws.cell(row=r_i, column=pos, value=r['Name']).alignment = align_left
            pos += 1
            ws.cell(row=r_i, column=pos, value=r['City']).alignment = align_left
            pos += 1
            ws.cell(row=r_i, column=pos, value=r['State']).alignment = align_left
            pos += 1
            for m in ['Score', 'TLR (100)', 'RPC (100)', 'GO (100)', 'OI (100)', 'Perception (100)']:
                val = r[m]
                cell = ws.cell(row=r_i, column=pos, value=val)
                cell.alignment = align_right
                if isinstance(val, (int, float)):
                    cell.number_format = "0.00"
                pos += 1
            pdf_c = ws.cell(row=r_i, column=pos)
            if r['Report PDF']:
                pdf_c.value = "View PDF"
                pdf_c.hyperlink = r['Report PDF']
                pdf_c.font = link_font
                pdf_c.alignment = align_center
            else:
                pdf_c.value = ""
                pdf_c.alignment = align_center
                
            is_band = r['Is Rank Band']
            for c_i in range(1, len(cols) + 1):
                cell = ws.cell(row=r_i, column=c_i)
                if not (c_i == len(cols) and r['Report PDF']):
                    cell.font = regular_font
                if is_band:
                    cell.fill = band_row_fill
                cell.border = thin_border
                
        last_letter = get_column_letter(len(cols))
        ws.auto_filter.ref = f"A1:{last_letter}{len(records) + 1}"
        ws.freeze_panes = "A2"
        for col in ws.columns:
            max_len = 0
            col_letter = get_column_letter(col[0].column)
            col_name = str(col[0].value or '')
            for cell in col:
                if cell.value:
                    max_len = max(max_len, len(str(cell.value)))
            if 'Name' in col_name:
                ws.column_dimensions[col_letter].width = min(max(max_len + 3, 30), 65)
            elif 'PDF' in col_name or 'Score' in col_name or 'TLR' in col_name:
                ws.column_dimensions[col_letter].width = 14
            else:
                ws.column_dimensions[col_letter].width = max(max_len + 4, 12)
                
    for cfg in configs:
        cat = cfg['category']
        ws = wb.create_sheet(title=cfg['sheet_name'])
        populate(ws, category_data[cat], include_cat=False)
        
    ws_comb = wb.create_sheet(title="All Categories Combined")
    populate(ws_comb, all_combined, include_cat=True)
    
    if default_sheet in wb.worksheets:
        wb.remove(default_sheet)
        
    wb.save(output_filename)
    print(f"Saved {output_filename} with {len(all_combined)} total records!")
    return all_combined

if __name__ == '__main__':
    for y in [2024, 2023]:
        build_excel_for_year(y)
