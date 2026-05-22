import os
import json
import pandas as pd
from datetime import datetime, timedelta

ARCHIVE_DIR = "archive"
OUTPUT_FILE = "public/change_summary.json"

# --- Sector Mapping (Top Market Caps) ---
SECTOR_MAP = {
    "APPLE": "Technology", "MICROSOFT": "Technology", "NVIDIA": "Technology", "ALPHABET": "Communication",
    "AMAZON": "Consumer Disc", "META PLATFORMS": "Communication", "TESLA": "Consumer Disc", "BROADCOM": "Technology",
    "ELI LILLY": "Healthcare", "BERKSHIRE HATHAWAY": "Financials", "JPMORGAN CHASE": "Financials", "VISA": "Financials",
    "MASTERCARD": "Financials", "UNITEDHEALTH": "Healthcare", "EXXON MOBIL": "Energy", "JOHNSON & JOHNSON": "Healthcare",
    "COSTCO": "Consumer Staples", "PROCTER & GAMBLE": "Consumer Staples", "HOME DEPOT": "Consumer Disc",
    "ABBVIE": "Healthcare", "WALMART": "Consumer Staples", "MERCK": "Healthcare", "CHEVRON": "Energy",
    "NETFLIX": "Communication", "COCA-COLA": "Consumer Staples", "PEPSICO": "Consumer Staples",
    "ORACLE": "Technology", "ADOBE": "Technology", "SALESFORCE": "Technology", "INTEL": "Technology",
    "DISNEY": "Communication", "BANK OF AMERICA": "Financials", "WELLS FARGO": "Financials",
    "AMD": "Technology", "QUALCOMM": "Technology", "ARM HOLDINGS": "Technology", "PALANTIR": "Technology"
}

def get_archive_files():
    if not os.path.exists(ARCHIVE_DIR):
        return []
    files = [f for f in os.listdir(ARCHIVE_DIR) if f.startswith("holdings_") and f.endswith(".json")]
    files.sort(reverse=True)
    return files

def load_data(filename):
    with open(os.path.join(ARCHIVE_DIR, filename), 'r') as f:
        return pd.DataFrame(json.load(f))

def get_sector(name):
    name = str(name).upper()
    for key, sector in SECTOR_MAP.items():
        if key in name:
            return sector
    return "Other / Misc"

def calculate_deltas(current_df, previous_df, period_label):
    if previous_df is None:
        return { "period": period_label, "changes": [], "new_positions": [], "closed_positions": [] }

    def summarize(df):
        df['Shares'] = pd.to_numeric(df['Shares'], errors='coerce').fillna(0)
        # Support both new normalized field and old legacy field
        val_col = 'Value_USD' if 'Value_USD' in df.columns else 'Value (x$1000)'
        df['val_numeric'] = pd.to_numeric(df[val_col], errors='coerce').fillna(0)
        
        # Heuristic normalization for legacy data in archive
        def normalize_row(r):
            v, s = r['val_numeric'], r['Shares']
            if s > 0 and (v / s) < 1.0: # Likely thousands
                return v * 1000
            if v < 10000000 and s > 0 and v > 0: # Plausible thousands
                 return v * 1000 if 'Value (x$1000)' in df.columns else v
            return v
            
        df['val_norm'] = df.apply(normalize_row, axis=1)
        
        return df.groupby(['Issuer', 'CUSIP']).agg({
            'Shares': 'sum',
            'val_norm': 'sum',
            'Fund': 'count'
        }).rename(columns={'val_norm': 'value_usd'}).reset_index()

    curr_sum = summarize(current_df)
    prev_sum = summarize(previous_df)

    merged = pd.merge(curr_sum, prev_sum, on=['Issuer', 'CUSIP'], how='outer', suffixes=('_curr', '_prev')).fillna(0)
    
    merged['share_change'] = merged['Shares_curr'] - merged['Shares_prev']
    merged['value_change'] = merged['value_usd_curr'] - merged['value_usd_prev']
    merged['fund_change'] = merged['Fund_curr'] - merged['Fund_prev']
    
    # Sector Enrichment
    merged['Sector'] = merged['Issuer'].apply(get_sector)

    # Classification
    new_pos = merged[(merged['Shares_prev'] == 0) & (merged['Shares_curr'] > 0)].sort_values(by='value_change', ascending=False)
    closed_pos = merged[(merged['Shares_curr'] == 0) & (merged['Shares_prev'] > 0)].sort_values(by='value_change', ascending=True)
    
    significant = merged[merged['share_change'] != 0].copy()
    significant.sort_values(by='value_change', ascending=False, inplace=True)
    
    # Sector Deltas (Rotation Analysis)
    sector_rotation = merged.groupby('Sector')['value_change'].sum()
    sector_rotation = sector_rotation[sector_rotation.index != "Other / Misc"].sort_values(ascending=False).to_dict()

    return {
        "period": period_label,
        "changes": significant.head(100).to_dict(orient='records'),
        "new_positions": new_pos.head(20).to_dict(orient='records'),
        "closed_positions": closed_pos.head(20).to_dict(orient='records'),
        "sector_rotation": sector_rotation
    }

def main():
    files = get_archive_files()
    if len(files) < 1:
        print("Not enough archive data yet.")
        return

    print(f"Analyzing {len(files)} snapshots...")
    current_df = load_data(files[0])
    
    now = datetime.now()
    weekly_file = None
    monthly_file = None
    
    def get_date_from_filename(f):
        ts_str = f.split('_')[1].split('.')[0]
        return datetime.strptime(ts_str, "%Y%m%d-%H%M")

    for f in files[1:]:
        f_date = get_date_from_filename(f)
        diff = now - f_date
        if diff.days >= 7 and not weekly_file: weekly_file = f
        if diff.days >= 30 and not monthly_file:
            monthly_file = f
            break

    if not weekly_file and len(files) > 1:
        weekly_file = files[-1]
        print(f"Fallback: Using oldest file {weekly_file} for weekly baseline.")

    weekly_df = load_data(weekly_file) if weekly_file else None
    monthly_df = load_data(monthly_file) if monthly_file else None

    summary = {
        "generated_at": now.isoformat(),
        "weekly": calculate_deltas(current_df, weekly_df, "7d"),
        "monthly": calculate_deltas(current_df, monthly_df, "30d")
    }

    if not os.path.exists("public"): os.makedirs("public")
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"Deep change summary generated: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
