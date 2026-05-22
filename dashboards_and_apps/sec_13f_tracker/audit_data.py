import json
import os

def audit():
    print("--- DATA AUDIT START ---")
    
    # 1. Macro Audit
    if os.path.exists('public/macro.json'):
        with open('public/macro.json') as f:
            macro = json.load(f)
            fedfunds = macro['data']['FEDFUNDS']['observations']
            print(f"[MACRO] Observations for FEDFUNDS: {len(fedfunds)} (Target: 60)")
            if len(fedfunds) == 60: print("  [OK] History extension successful.")
            else: print(f"  [ERROR] History mismatch! Expected 60, got {len(fedfunds)}")
    else:
        print("[MACRO] ERROR: public/macro.json not found!")

    # 2. Holdings Audit
    if os.path.exists('public/holdings.json'):
        with open('public/holdings.json') as f:
            data = json.load(f)
            print(f"[HOLDINGS] Total Records: {len(data)}")
            
            targets = {
                'APPLE': 1e9, # > 1B for Berkshire usually
                'AMAZON': 1e7,
                'ALPHABET': 1e7,
                'MERCADOLIBRE': 1e5,
                'SPOTIFY': 1e7
            }
            
            fund_samples = {}
            for h in data:
                issuer = h['Issuer'].upper()
                fund = h['Fund']
                val = h['Value_USD']
                
                for t, min_val in targets.items():
                    if t in issuer and fund not in fund_samples:
                        fund_samples[fund] = {
                            'Issuer': h['Issuer'],
                            'Value_USD': f"${val/1e6:.1f}M",
                            'Shares': h['Shares'],
                            'Type': h['Type'],
                            'RawScale': val / (float(h['Shares']) if float(h['Shares']) > 0 else 1)
                        }
            
            print("\n[SCALING CHECK] Representative Positions:")
            for fund, s in list(fund_samples.items())[:10]:
                print(f"  {fund:<25} | {s['Issuer']:<25} | {s['Value_USD']:>10} | {s['Type']:<3} | Ratio: {s['RawScale']:.2f}")

            # Quadrillion Check
            quads = [h for h in data if h['Value_USD'] > 1e13] # > 10 Trillion is likely an error
            if quads:
                print(f"\n  [ERROR] Found {len(quads)} positions in the Quadrillions/High Trillions!")
                for q in quads[:3]:
                    print(f"    - {q['Issuer']} ({q['Fund']}): ${q['Value_USD']/1e12:.2f}T")
            else:
                print("\n  [OK] No Quadrillion-scale errors detected.")
    else:
        print("[HOLDINGS] ERROR: public/holdings.json not found!")

    print("\n--- DATA AUDIT END ---")

if __name__ == "__main__":
    audit()
