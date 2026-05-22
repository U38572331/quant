import requests
import pandas as pd
import time
import xml.etree.ElementTree as ET
import statistics

# --- Configuration ---
TARGET_FUNDS_CIK = {
    "Duquesne (Druckenmiller)": "0001536411",
    "Appaloosa (Tepper)":       "0001656456",
    "Berkshire (Buffett)":      "0001067983",
    "Soros Fund Mgmt":          "0001029160",
    "Bridgewater (Dalio)":      "0001350694",
    "Scion (Michael Burry)":    "0001649339",
    "Baupost (Klarman)":        "0001061768",
    "Oaktree (Howard Marks)":   "0000949509",
    "Coatue (Laffont)":         "0001137731",
    "Tiger Global (Coleman)":   "0001167483",
    "Viking Global (Halvorsen)":"0001103804",
    "Lone Pine (Mandel)":       "0001061165",
    "Maverick Capital (Ainslie)":"0001063236",
    "D1 Capital (Sundheim)":    "0001747021",
    "ARK Invest (Cathie Wood)": "0001697748",
    "Baillie Gifford":          "0001088875",
    "Whale Rock Capital":       "0001377484",
    "Pershing Square (Ackman)": "0001336528",
    "Elliott Mgmt (Singer)":    "0001040579",
    "Third Point (Loeb)":       "0001040273",
    "Icahn Capital (Carl Icahn)":"0000921669",
    "Greenlight (Einhorn)":     "0001079114",
    "ValueAct Capital":         "0001389803",
    "Renaissance (RenTech)":    "0001037389",
    "Citadel (Ken Griffin)":    "0001423053",
    "Point72 (Steve Cohen)":    "0001603466",
    "Millennium (Englander)":   "0001273013",
    "Two Sigma":                "0001179392",
    "D.E. Shaw":                "0001009207",
    "Jane Street Group":        "0001612613",
    "Susquehanna Int'l":        "0001446194",
    "Jump Trading":             "0001612504",
    "BlackRock Inc":            "0001364742",
    "Vanguard Group":           "0001029093",
    "State Street Corp":        "0000093751",
    "Fidelity (FMR LLC)":       "0000315066",
    "JPMorgan Chase":           "0000019617",
    "Baker Bros (Biotech)":     "0001261657",
    "Perceptive Advisors":      "0001224385",
    "TCI Fund (Chris Hohn)":    "0001647251",
    "Farallon Capital":         "0000902219",
    "Sequoia Capital":          "0001099238",
    "Polen Capital":            "0001064511"
}

USER_AGENT = "Individual Investor <analysis@example.com>"
HEADERS = {"User-Agent": USER_AGENT}

def get_submission_history(cik):
    url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    try:
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
        return response.json()
    except: return None

def find_latest_13f_filing(submissions_data):
    if not submissions_data or 'filings' not in submissions_data: return None
    recent = submissions_data['filings']['recent']
    candidates = []
    for i, form in enumerate(recent['form']):
        if form in ['13F-HR', '13F-HR/A']:
            candidates.append({
                'accessionNumber': recent['accessionNumber'][i],
                'reportDate': recent['reportDate'][i],
                'filingDate': recent['filingDate'][i]
            })
    if not candidates: return None
    candidates.sort(key=lambda x: x['filingDate'], reverse=True)
    return candidates[0]

def parse_information_table(xml_content):
    try:
        root = ET.fromstring(xml_content)
        ns = {}
        if '}' in root.tag: ns = {'ns': root.tag.split('}')[0].strip('{')}
        rows = root.findall('.//ns:infoTable', ns) if ns else root.findall('.//infoTable')
        if not rows: rows = root.findall('infoTable')
        
        raw_holdings = []
        ratios = []
        
        for row in rows:
            def get_text(tag):
                elem = row.find(f'.//ns:{tag}', ns) if ns else row.find(tag)
                return elem.text if elem is not None else ""

            name = get_text('nameOfIssuer')
            title = get_text('titleOfClass')
            cusip = get_text('cusip')
            value_raw = get_text('value')
            
            shrs_elem = row.find('.//ns:shrsOrPrnAmt', ns) if ns else row.find('shrsOrPrnAmt')
            shares_raw = "0"
            sshPrnamtType = ""
            if shrs_elem is not None:
                s_elem = shrs_elem.find('ns:sshPramt' if ns else 'sshPramt', ns) # Fixed typo in previous attempt
                if s_elem is None: s_elem = shrs_elem.find('ns:sshPrnamt', ns) if ns else shrs_elem.find('sshPrnamt')
                t_elem = shrs_elem.find('ns:sshPrnamtType', ns) if ns else shrs_elem.find('sshPrnamtType')
                shares_raw = s_elem.text if s_elem is not None else "0"
                sshPrnamtType = t_elem.text if t_elem is not None else ""

            try:
                v = float(value_raw)
                s = float(shares_raw)
                if s > 0:
                    r = v / s
                    if sshPrnamtType == 'SH': ratios.append(r)
            except: pass
            
            raw_holdings.append({
                'Issuer': name, 'Class': title, 'CUSIP': cusip,
                'v_raw': value_raw, 's_raw': shares_raw, 'Type': sshPrnamtType
            })

        # Scaling Detection
        # If median Price-Ratio is < 1.0, it's very likely Thousands (e.g. $100 stock -> 0.1 ratio)
        # If median Price-Ratio is > 5.0, it's very likely Dollars (e.g. $100 stock -> 100 ratio)
        is_dollars = True
        if ratios:
            median_ratio = statistics.median(ratios)
            if median_ratio < 1.0: is_dollars = False
            # Special case for high-priced funds (if median is say 2.5, it could be a Thousands fund with MELI)
            # But most funds have 50+ holdings, median will be a normal stock ($50-200).
            # If median is < 1.0, it's definitely Thousands.
        
        final_holdings = []
        for h in raw_holdings:
            try:
                val = float(h['v_raw'])
                if not is_dollars: val *= 1000
                final_holdings.append({
                    'Issuer': h['Issuer'], 'Class': h['Class'], 'CUSIP': h['CUSIP'],
                    'Value_USD': val, 'Shares': h['s_raw'], 'Type': h['Type']
                })
            except: pass
        return final_holdings
    except Exception as e:
        print(f"Error parsing XML: {e}")
        return []

def get_filing_documents(cik, accession_number):
    accession_no_hyphen = accession_number.replace("-", "")
    index_url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession_no_hyphen}/index.json"
    try:
        listing = requests.get(index_url, headers=HEADERS).json()
        xml_candidates = [f for f in listing['directory']['item'] if f['name'].lower().endswith('.xml')]
        xml_file = next((f['name'] for f in xml_candidates if 'infotable' in f['name'].lower()), None)
        if not xml_file and xml_candidates:
            xml_candidates.sort(key=lambda x: x.get('size', 0), reverse=True)
            xml_file = xml_candidates[0]['name']
        if xml_file: return f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession_no_hyphen}/{xml_file}"
    except: pass
    return None

def main():
    import sys
    limit = 15
    if '--limit' in sys.argv: limit = int(sys.argv[sys.argv.index('--limit') + 1])
    
    all_data = []
    funds = list(TARGET_FUNDS_CIK.items())[:limit]
    print(f"Starting tracking for {len(funds)} funds...")
    
    for fund_name, cik in funds:
        print(f"Processing {fund_name}...")
        try:
            history = get_submission_history(cik)
            latest = find_latest_13f_filing(history)
            if not latest: continue
            xml_url = get_filing_documents(cik, latest['accessionNumber'])
            if not xml_url: continue
            r = requests.get(xml_url, headers=HEADERS)
            holdings = parse_information_table(r.content)
            for h in holdings:
                h.update({'Fund': fund_name, 'CIK': cik, 'ReportDate': latest['reportDate'], 'FilingDate': latest['filingDate']})
                all_data.append(h)
            time.sleep(0.15)
        except Exception as e: print(f"  Error: {e}")

    if all_data:
        df = pd.DataFrame(all_data)
        import os
        if not os.path.exists("public"): os.makedirs("public")
        df['Value_USD'] = pd.to_numeric(df['Value_USD'], errors='coerce').fillna(0)
        df.to_json("public/holdings.json", orient='records')
        print(f"Saved {len(df)} records.")
    else: print("No data.")

if __name__ == "__main__":
    main()
