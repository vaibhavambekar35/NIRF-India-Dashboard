import sqlite3

def setup_institution_types():
    conn = sqlite3.connect('nirf_v2.db')
    c = conn.cursor()

    c.execute('PRAGMA table_info(institutions)')
    cols = [r[1] for r in c.fetchall()]
    if 'institution_type' not in cols:
        c.execute("ALTER TABLE institutions ADD COLUMN institution_type VARCHAR(50) DEFAULT 'Private / Deemed'")
        conn.commit()
        print('Added institution_type column to institutions table')
    else:
        print('institution_type column already exists')

    # Get institutions in state_public_university category
    c.execute('''
        SELECT DISTINCT i.id 
        FROM institutions i
        JOIN ranking_results rr ON rr.institution_id = i.id
        JOIN ranking_editions re ON re.id = rr.ranking_edition_id
        WHERE re.category_slug = 'state_public_university'
    ''')
    spu_ids = set(r[0] for r in c.fetchall())

    central_keywords = [
        'indian institute of technology', 'national institute of technology', 'indian institute of management',
        'all india institute of medical sciences', 'indian institute of science', 'iit', 'nit', 'iim', 'aiims', 'iisc',
        'central university', 'banaras hindu university', 'aligarh muslim university', 'jawaharlal nehru university',
        'university of delhi', 'jamia millia islamia', 'visva-bharati', 'indian institute of information technology',
        'iiit', 'niper', 'nift', 'school of planning and architecture', 'spa', 'indian statistical institute',
        'tata institute of fundamental research', 'homi bhabha national institute', 'jawaharlal institute of postgraduate medical',
        'post graduate institute of medical education and research', 'national institute of mental health and neuro sciences',
        'nimhans', 'jipmer', 'pgimer', 'dakshina bharat hindi prachar sabha', 'tezpur university', 'assam university',
        'mizoram university', 'north-eastern hill university', 'nehu', 'pondicherry university', 'babasaheb bhimrao ambedkar university',
        'rajiv gandhi university', 'sikkim university', 'tripura university', 'central agricultural university',
        'indian veterinary research institute', 'national dairy research institute'
    ]

    state_keywords = [
        'government', 'govt.', 'govt', 'state university', 'state institute'
    ]

    c.execute('SELECT id, institution_name FROM institutions')
    institutions = c.fetchall()

    for i_id, name in institutions:
        n_lower = name.lower()
        if any(k in n_lower for k in central_keywords):
            itype = 'Central'
        elif i_id in spu_ids or any(k in n_lower for k in state_keywords) or 'university of calcutta' in n_lower or 'anna university' in n_lower or 'jadavpur' in n_lower or 'osmania' in n_lower or 'savitribai phule pune' in n_lower or 'university of madras' in n_lower or 'university of mumbai' in n_lower or 'delhi technological university' in n_lower or 'netaji subhas' in n_lower:
            itype = 'State Public'
        else:
            itype = 'Private / Deemed'
        c.execute('UPDATE institutions SET institution_type = ? WHERE id = ?', (itype, i_id))

    conn.commit()

    c.execute('SELECT institution_type, count(*) FROM institutions GROUP BY institution_type')
    print('Classification breakdown:', c.fetchall())
    conn.close()

if __name__ == '__main__':
    setup_institution_types()
