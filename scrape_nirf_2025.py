import requests
from bs4 import BeautifulSoup
import copy
import re
import os
import pandas as pd
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Referer': 'https://www.nirfindia.org/Rankings/2025/Ranking.html',
}

CONFIGS = [
    {
        'category': 'Overall',
        'sheet_name': 'Overall',
        'main_url': 'https://www.nirfindia.org/Rankings/2025/OverallRanking.html',
        'bands': [
            ('101-150', 'https://www.nirfindia.org/Rankings/2025/OverallRanking150.html'),
            ('151-200', 'https://www.nirfindia.org/Rankings/2025/OverallRanking200.html')
        ]
    },
    {
        'category': 'Universities',
        'sheet_name': 'Universities',
        'main_url': 'https://www.nirfindia.org/Rankings/2025/UniversityRanking.html',
        'bands': [
            ('101-150', 'https://www.nirfindia.org/Rankings/2025/UniversityRanking150.html'),
            ('151-200', 'https://www.nirfindia.org/Rankings/2025/UniversityRanking200.html')
        ]
    },
    {
        'category': 'Engineering',
        'sheet_name': 'Engineering',
        'main_url': 'https://www.nirfindia.org/Rankings/2025/EngineeringRanking.html',
        'bands': [
            ('101-150', 'https://www.nirfindia.org/Rankings/2025/EngineeringRanking150.html'),
            ('151-200', 'https://www.nirfindia.org/Rankings/2025/EngineeringRanking200.html'),
            ('201-300', 'https://www.nirfindia.org/Rankings/2025/EngineeringRanking300.html')
        ]
    },
    {
        'category': 'Management',
        'sheet_name': 'Management',
        'main_url': 'https://www.nirfindia.org/Rankings/2025/ManagementRanking.html',
        'bands': [
            ('101-125', 'https://www.nirfindia.org/Rankings/2025/ManagementRanking150.html')
        ]
    },
    {
        'category': 'Medical',
        'sheet_name': 'Medical',
        'main_url': 'https://www.nirfindia.org/Rankings/2025/MedicalRanking.html',
        'bands': []
    },
    {
        'category': 'State Public University',
        'sheet_name': 'State Public University',
        'main_url': 'https://www.nirfindia.org/Rankings/2025/STATEPUBLICUNIVERSITYRanking.html',
        'bands': [
            ('51-100', 'https://www.nirfindia.org/Rankings/2025/STATEPUBLICUNIVERSITYRanking100.html')
        ]
    }
]

def scrape_main_table(url, category):
    print(f"Scraping top ranks for {category} from {url}...")
    r = requests.get(url, headers=HEADERS, timeout=20)
    soup = BeautifulSoup(r.text, 'html.parser')
    tbl = soup.find('table', {'id': 'tbl_overall'})
    if not tbl:
        print(f"Warning: No table 'tbl_overall' found for {category}")
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
            
        # PDF Link
        pdf_a = td1.find('a', href=lambda h: h and h.endswith('.pdf'))
        pdf_url = pdf_a['href'] if pdf_a else ''
        
        # Institution Name
        td1_clone = copy.copy(td1)
        for div in td1_clone.find_all('div'):
            div.decompose()
        name = td1_clone.get_text(' ', strip=True)
        name = re.sub(r'\s+', ' ', name).strip()
        
        city = re.sub(r'\s+', ' ', tds[2].get_text(strip=True))
        state = re.sub(r'\s+', ' ', tds[3].get_text(strip=True))
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
                return val if val else None

        records.append({
            'Category': category,
            'Rank': int(rank_str) if rank_str.isdigit() else rank_str,
            'Institute ID': inst_id,
            'Name': name,
            'City': city,
            'State': state,
            'Score': score_val,
            'TLR (100)': parse_float(params.get('TLR (100)')),
            'RPC (100)': parse_float(params.get('RPC (100)')),
            'GO (100)': parse_float(params.get('GO (100)')),
            'OI (100)': parse_float(params.get('OI (100)')),
            'Perception (100)': parse_float(params.get('PERCEPTION (100)')),
            'Report PDF': pdf_url
        })
    return records

def scrape_rank_band(url, category, band_name):
    print(f"Scraping rank band {band_name} for {category} from {url}...")
    r = requests.get(url, headers=HEADERS, timeout=20)
    soup = BeautifulSoup(r.text, 'html.parser')
    tbl = soup.find('table')
    if not tbl:
        print(f"Warning: No table found for {category} band {band_name}")
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
        state = re.sub(r'\s+', ' ', tds[2].get_text(strip=True))
        
        # In rank band, NIRF does not provide Score or Institute ID
        records.append({
            'Category': category,
            'Rank': band_name,
            'Institute ID': '',
            'Name': name,
            'City': city,
            'State': state,
            'Score': None,
            'TLR (100)': None,
            'RPC (100)': None,
            'GO (100)': None,
            'OI (100)': None,
            'Perception (100)': None,
            'Report PDF': ''
        })
    return records

def build_excel():
    all_combined_data = []
    category_data = {}
    summary_stats = []
    
    for cfg in CONFIGS:
        cat = cfg['category']
        main_records = scrape_main_table(cfg['main_url'], cat)
        band_records = []
        for band_name, band_url in cfg['bands']:
            b_recs = scrape_rank_band(band_url, cat, band_name)
            band_records.extend(b_recs)
            
        full_cat_records = main_records + band_records
        category_data[cat] = {
            'records': full_cat_records,
            'sheet_name': cfg['sheet_name'],
            'top_count': len(main_records),
            'band_count': len(band_records),
            'top_score': main_records[0]['Score'] if main_records else None,
            'rank_1_name': main_records[0]['Name'] if main_records else None,
        }
        all_combined_data.extend(full_cat_records)
        
        summary_stats.append({
            'Category': cat,
            'Top Ranked Institutes': len(main_records),
            'Rank Band Institutes': len(band_records),
            'Total Scraped': len(full_cat_records),
            'Rank 1 Institution': main_records[0]['Name'] if main_records else 'N/A',
            'Rank 1 Score': main_records[0]['Score'] if main_records else 'N/A'
        })
        print(f"Completed {cat}: {len(main_records)} top ranks + {len(band_records)} in bands = {len(full_cat_records)} total.")
        
    output_filename = "NIRF_India_Rankings_2025.xlsx"
    print(f"\nWriting results to Excel file: {output_filename}...")
    
    wb = openpyxl.Workbook()
    # Remove default sheet
    default_sheet = wb.active
    
    # ------------------ Styling Definitions ------------------
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
    
    # ------------------ 1. Summary Sheet ------------------
    ws_summary = wb.create_sheet(title="Overview & Summary")
    ws_summary.views.sheetView[0].showGridLines = True
    
    # Title Banner
    ws_summary.merge_cells("A1:F2")
    title_cell = ws_summary["A1"]
    title_cell.value = "NATIONAL INSTITUTIONAL RANKING FRAMEWORK (NIRF) 2025"
    title_cell.font = title_font
    title_cell.fill = title_fill
    title_cell.alignment = align_center
    
    ws_summary["A3"].value = "Data Scraped from Official Portal: https://www.nirfindia.org/Rankings/2025/Ranking.html"
    ws_summary["A3"].font = Font(name="Calibri", size=10, italic=True, color="595959")
    
    # Statistics Table
    summary_headers = ["Category", "Top Ranked (1-100/50)", "Rank Bands", "Total Institutes", "Rank #1 Institution", "Top Score"]
    row_idx = 5
    for col_idx, h in enumerate(summary_headers, 1):
        c = ws_summary.cell(row=row_idx, column=col_idx, value=h)
        c.font = header_font
        c.fill = header_fill
        c.alignment = align_center
        c.border = thin_border
        
    for stat in summary_stats:
        row_idx += 1
        ws_summary.cell(row=row_idx, column=1, value=stat['Category']).alignment = align_left
        ws_summary.cell(row=row_idx, column=2, value=stat['Top Ranked Institutes']).alignment = align_center
        ws_summary.cell(row=row_idx, column=3, value=stat['Rank Band Institutes']).alignment = align_center
        ws_summary.cell(row=row_idx, column=4, value=stat['Total Scraped']).alignment = align_center
        ws_summary.cell(row=row_idx, column=5, value=stat['Rank 1 Institution']).alignment = align_left
        score_c = ws_summary.cell(row=row_idx, column=6, value=stat['Rank 1 Score'])
        score_c.alignment = align_center
        if isinstance(stat['Rank 1 Score'], (int, float)):
            score_c.number_format = "0.00"
            
        for col_idx in range(1, 7):
            c = ws_summary.cell(row=row_idx, column=col_idx)
            c.font = regular_font
            c.border = thin_border
            
    # Total row
    row_idx += 1
    ws_summary.cell(row=row_idx, column=1, value="TOTAL ACROSS 6 CATEGORIES").font = bold_font
    ws_summary.cell(row=row_idx, column=2, value=sum(s['Top Ranked Institutes'] for s in summary_stats)).font = bold_font
    ws_summary.cell(row=row_idx, column=2).alignment = align_center
    ws_summary.cell(row=row_idx, column=3, value=sum(s['Rank Band Institutes'] for s in summary_stats)).font = bold_font
    ws_summary.cell(row=row_idx, column=3).alignment = align_center
    ws_summary.cell(row=row_idx, column=4, value=sum(s['Total Scraped'] for s in summary_stats)).font = bold_font
    ws_summary.cell(row=row_idx, column=4).alignment = align_center
    ws_summary.cell(row=row_idx, column=5, value="").font = bold_font
    ws_summary.cell(row=row_idx, column=6, value="").font = bold_font
    for col_idx in range(1, 7):
        c = ws_summary.cell(row=row_idx, column=col_idx)
        c.fill = subhead_fill
        c.border = thin_border
        
    # Parameter Explanations Table
    row_idx += 3
    ws_summary.cell(row=row_idx, column=1, value="NIRF Ranking Parameters Explanation:").font = bold_font
    param_info = [
        ("TLR (100)", "Teaching, Learning & Resources", "Core teaching infrastructure, faculty-student ratio, faculty qualification & experience, financial resources utilization."),
        ("RPC (100)", "Research and Professional Practice", "Combined metrics for publications, citations, quality of publications, IPR and patents, projects and professional practice."),
        ("GO (100)", "Graduation Outcomes", "Metric for university examinations, median salary of placed graduates, and number of students selected for higher studies."),
        ("OI (100)", "Outreach and Inclusivity", "Percentage of students from other states/countries, percentage of women students/faculty, economically and socially disadvantaged students, facilities for physically challenged."),
        ("PERCEPTION (100)", "Peer Perception", "Perception from academic peers and employers across the country.")
    ]
    row_idx += 1
    p_headers = ["Parameter Code", "Full Name", "Description & Components"]
    for c_i, ph in enumerate(p_headers, 1):
        cell = ws_summary.cell(row=row_idx, column=c_i, value=ph)
        cell.font = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
        cell.fill = PatternFill(start_color="333f48", end_color="333f48", fill_type="solid")
        cell.alignment = align_center
        cell.border = thin_border
        
    for pcode, pname, pdesc in param_info:
        row_idx += 1
        c1 = ws_summary.cell(row=row_idx, column=1, value=pcode)
        c1.alignment = align_center
        c1.font = bold_font
        c1.border = thin_border
        
        c2 = ws_summary.cell(row=row_idx, column=2, value=pname)
        c2.font = regular_font
        c2.border = thin_border
        
        c3 = ws_summary.cell(row=row_idx, column=3, value=pdesc)
        c3.font = regular_font
        c3.border = thin_border
        
    # Adjust column widths for summary
    ws_summary.column_dimensions['A'].width = 28
    ws_summary.column_dimensions['B'].width = 34
    ws_summary.column_dimensions['C'].width = 50
    ws_summary.column_dimensions['D'].width = 18
    ws_summary.column_dimensions['E'].width = 46
    ws_summary.column_dimensions['F'].width = 14

    # ------------------ Function to Populate Category Sheet ------------------
    def populate_sheet(ws, records, include_category_col=False):
        ws.views.sheetView[0].showGridLines = True
        
        headers = []
        if include_category_col:
            headers.append("Category")
        headers.extend([
            "Rank", "Institute ID", "Institute Name", "City", "State",
            "Score", "TLR (100)", "RPC (100)", "GO (100)", "OI (100)", "Perception (100)", "Report PDF"
        ])
        
        # Write headers
        for col_idx, h in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col_idx, value=h)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = align_center
            cell.border = thin_border
            
        # Write rows
        for row_idx, r in enumerate(records, 2):
            col_pos = 1
            if include_category_col:
                c = ws.cell(row=row_idx, column=col_pos, value=r['Category'])
                c.alignment = align_left
                col_pos += 1
                
            rank_c = ws.cell(row=row_idx, column=col_pos, value=r['Rank'])
            rank_c.alignment = align_center
            col_pos += 1
            
            id_c = ws.cell(row=row_idx, column=col_pos, value=r['Institute ID'])
            id_c.alignment = align_center
            col_pos += 1
            
            name_c = ws.cell(row=row_idx, column=col_pos, value=r['Name'])
            name_c.alignment = align_left
            col_pos += 1
            
            city_c = ws.cell(row=row_idx, column=col_pos, value=r['City'])
            city_c.alignment = align_left
            col_pos += 1
            
            state_c = ws.cell(row=row_idx, column=col_pos, value=r['State'])
            state_c.alignment = align_left
            col_pos += 1
            
            # Numeric columns
            for metric in ['Score', 'TLR (100)', 'RPC (100)', 'GO (100)', 'OI (100)', 'Perception (100)']:
                val = r[metric]
                cell = ws.cell(row=row_idx, column=col_pos, value=val)
                cell.alignment = align_right
                if isinstance(val, (int, float)):
                    cell.number_format = "0.00"
                col_pos += 1
                
            # Report PDF Link
            pdf_c = ws.cell(row=row_idx, column=col_pos)
            if r['Report PDF']:
                pdf_c.value = "View PDF"
                pdf_c.hyperlink = r['Report PDF']
                pdf_c.font = link_font
                pdf_c.alignment = align_center
            else:
                pdf_c.value = ""
                pdf_c.alignment = align_center
                
            # Formatting and border
            is_band = isinstance(r['Rank'], str) and '-' in r['Rank']
            for col_i in range(1, len(headers) + 1):
                cell = ws.cell(row=row_idx, column=col_i)
                if not (col_i == len(headers) and r['Report PDF']):
                    cell.font = regular_font
                if is_band:
                    cell.fill = band_row_fill
                cell.border = thin_border
                
        # Enable auto-filter
        last_col_letter = get_column_letter(len(headers))
        ws.auto_filter.ref = f"A1:{last_col_letter}{len(records) + 1}"
        ws.freeze_panes = "A2"
        
        # Column width optimization
        for col in ws.columns:
            max_len = 0
            col_letter = get_column_letter(col[0].column)
            col_name = str(col[0].value or '')
            for cell in col:
                val = cell.value
                if val:
                    val_str = str(val)
                    if len(val_str) > max_len:
                        max_len = len(val_str)
            # Add padding
            if col_name in ['Institute Name', 'Name']:
                ws.column_dimensions[col_letter].width = min(max(max_len + 3, 30), 65)
            elif col_name in ['Report PDF']:
                ws.column_dimensions[col_letter].width = 14
            elif col_name in ['Score', 'TLR (100)', 'RPC (100)', 'GO (100)', 'OI (100)', 'Perception (100)']:
                ws.column_dimensions[col_letter].width = 14
            else:
                ws.column_dimensions[col_letter].width = max(max_len + 4, 12)

    # ------------------ Populate Individual Category Sheets ------------------
    for cfg in CONFIGS:
        cat = cfg['category']
        sheet_title = cfg['sheet_name']
        ws = wb.create_sheet(title=sheet_title)
        populate_sheet(ws, category_data[cat]['records'], include_category_col=False)
        
    # ------------------ Master Combined Sheet ------------------
    ws_all = wb.create_sheet(title="All Categories Combined")
    populate_sheet(ws_all, all_combined_data, include_category_col=True)
    
    # Remove default empty sheet
    if default_sheet in wb.worksheets:
        wb.remove(default_sheet)
        
    wb.save(output_filename)
    print(f"\nSuccessfully generated {output_filename} with {len(wb.sheetnames)} sheets!")

if __name__ == '__main__':
    build_excel()
