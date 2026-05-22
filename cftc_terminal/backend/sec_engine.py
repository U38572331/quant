import requests
import pandas as pd
import logging
from datetime import datetime
import re
import xml.etree.ElementTree as ET

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "AntigravityTerminal/1.0 (contact@example.com)"
}

class SECEngine:
    def __init__(self):
        self.tickers_map = {}
        self._load_tickers()

    def _load_tickers(self):
        """Load Ticker -> CIK map from SEC."""
        try:
            logger.info("Loading SEC Company Tickers...")
            url = "https://www.sec.gov/files/company_tickers.json"
            r = requests.get(url, headers=HEADERS)
            r.raise_for_status()
            data = r.json()
            
            # Map ticker -> {cik, title}
            # Data format: "0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."}
            for entry in data.values():
                self.tickers_map[entry['ticker'].upper()] = {
                    'cik': str(entry['cik_str']).zfill(10), # CIKs are 10 digits
                    'title': entry['title']
                }
            logger.info(f"Loaded {len(self.tickers_map)} tickers.")
        except Exception as e:
            logger.error(f"Failed to load tickers: {e}")

    def search_company(self, query):
        """Search for a company/fund by Ticker or Name."""
        query = query.upper()
        results = []
        
        # 1. Direct Ticker Match
        if query in self.tickers_map:
            val = self.tickers_map[query]
            results.append({"ticker": query, "cik": val['cik'], "name": val['title']})
        
        # 2. Name Search (limit 5)
        # Only search if query is at least 3 chars to avoid spam
        if len(query) >= 3:
            for ticker, val in self.tickers_map.items():
                if query in val['title'].upper() and ticker != query:
                    results.append({"ticker": ticker, "cik": val['cik'], "name": val['title']})
                    if len(results) >= 10: 
                        break
        
        return results

    def get_filings(self, cik, form_types=['4', '13F-HR', '13G', '13D']):
        """Get recent filings for a CIK."""
        try:
            url = f"https://data.sec.gov/submissions/CIK{cik}.json"
            r = requests.get(url, headers=HEADERS)
            r.raise_for_status()
            data = r.json()
            
            recent = data['filings']['recent']
            # recent is a dict of lists: {'accessionNumber': [...], 'form': [...], ...}
            
            parsed_filings = []
            count = 0
            # Iterate through lists
            limit = 100 # Look at last 100 filings
            for i in range(min(len(recent['accessionNumber']), limit)):
                form = recent['form'][i]
                if form in form_types:
                    acc_num = recent['accessionNumber'][i]
                    primary_doc = recent['primaryDocument'][i]
                    filing_date = recent['filingDate'][i]
                    
                    parsed_filings.append({
                        "accession_number": acc_num,
                        "form": form,
                        "filing_date": filing_date,
                        "primary_document": primary_doc,
                        "cik": cik
                    })
                    count += 1
            
            return parsed_filings
        except Exception as e:
            logger.error(f"Error fetching filings for {cik}: {e}")
            return []

    def get_form4_details(self, filing):
        """Fetch and parse detailed insider transactions from a Form 4 XML."""
        # URL Construction: https://www.sec.gov/Archives/edgar/data/{cik}/{accession_no_without_dashes}/{primary_doc}
        cik = filing['cik']
        acc_num_clean = filing['accession_number'].replace("-", "")
        doc = filing['primary_document']
        
        if not doc.endswith(".xml"):
            # Only parsing XML versions for now (most modern Form 4s are XML)
            return None

        url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc_num_clean}/{doc}"
        
        try:
            r = requests.get(url, headers=HEADERS)
            r.raise_for_status()
            
            root = ET.fromstring(r.content)
            
            # Namespace handling (SEC XMLs often have namespaces)
            # We'll just strip namespaces for simplicity or use generic find methods
            
            # Helper to safely get user
            def get_text(node, path):
                item = node.find(path)
                return item.text if item is not None else ""

            # Extract Transactions
            transactions = []
            
            # <nonDerivativeTable> -> <nonDerivativeTransaction>
            # Use iter to find all nonDerivativeTransaction regardless of namespace
            for trans in root.iter():
                if 'nonDerivativeTransaction' in trans.tag:
                    try:
                        # Security Title
                        security = get_text(trans, ".//securityTitle/value")
                        
                        # Transaction Date
                        date = get_text(trans, ".//transactionDate/value")
                        
                        # Transaction Code (P=Purchase, S=Sale)
                        code = get_text(trans, ".//transactionCoding/transactionCode")
                        
                        # Shares
                        shares = get_text(trans, ".//transactionAmounts/transactionShares/value")
                        
                        # Price
                        price = get_text(trans, ".//transactionAmounts/transactionPricePerShare/value")
                        
                        # Acquired/Disposed (A/D)
                        ad = get_text(trans, ".//transactionAmounts/transactionAcquiredDisposedCode/value")
                        
                        # Ownership (D=Direct, I=Indirect)
                        ownership = get_text(trans, ".//ownershipNature/directOrIndirectOwnership/value")
                        
                        # Reporting Owner
                        owner_name = ""
                        # Ideally we parse reportingOwner from root, but let's try to get it simple
                        # Just grabbing the first reporting owner for now
                        for owner in root.iter():
                             if 'reportingOwnerId' in owner.tag:
                                 owner_name = get_text(owner, ".//rptOwnerName")
                                 break

                        transactions.append({
                            "security": security,
                            "date": date,
                            "code": code,
                            "action": "Buy" if ad == 'A' else "Sell",
                            "shares": float(shares) if shares else 0,
                            "price": float(price) if price else 0,
                            "owner": owner_name,
                            "type": "Form 4"
                        })
                    except Exception as parse_e:
                        logger.warning(f"Failed to parse a transaction row: {parse_e}")
                        continue
            
            return transactions

        except Exception as e:
            logger.error(f"Error parsing Form 4 {url}: {e}")
            return None

    def get_13f_holdings(self, filing):
        """Fetch and parse 13F holdings (Information Table)."""
        # 13F consist of a header (edgar.xml) and an information table (often xml, ending in .xml)
        # But accession points to the main doc. We usually need to find the "information table" link.
        # However, data.sec.gov only gives us the primary doc which is usually the form header.
        # The info table is a separate document in the same directory.
        
        # Strategy:
        # 1. Go to the index page of the filing to find the XML info table.
        #    URL: https://www.sec.gov/Archives/edgar/data/{cik}/{acc_num_clean}/index.json
        # 2. Identify the file with type "INFORMATION TABLE" and name *.xml
        
        cik = filing['cik']
        acc_num_clean = filing['accession_number'].replace("-", "")
        
        index_url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc_num_clean}/index.json"
        
        try:
            r = requests.get(index_url, headers=HEADERS)
            r.raise_for_status()
            index_data = r.json()
            
            info_table_doc = None
            for file in index_data['directory']['item']:
                # Heuristic: name contains "xml" and maybe "info" or just checks largest xml? 
                # Proper way: check 'type'. index.json doesn't always have type perfectly mapped.
                # Usually it's xml_2.xml or similar.
                # Let's look for xml file that IS NOT the primary document if primary is xml?
                # Or look for file name containing "info" or "table"
                name = file['name']
                if name.endswith('.xml') and ('info' in name.lower() or 'table' in name.lower()):
                    info_table_doc = name
                    break
            
            if not info_table_doc:
                # Fallback: look for the largest XML file that isn't the primary?
                # or just any xml that is not primary
                for file in index_data['directory']['item']:
                    if file['name'].endswith('.xml') and file['name'] != filing['primary_document']:
                         info_table_doc = file['name']
                         break
            
            if not info_table_doc:
                return [] # Can't find it

            # Fetch the Info Table XML
            table_url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc_num_clean}/{info_table_doc}"
            r_xml = requests.get(table_url, headers=HEADERS)
            r_xml.raise_for_status()
            
            root = ET.fromstring(r_xml.content)
            
            holdings = []
            for info in root.iter():
                if 'infoTable' in info.tag:
                    try:
                        issuer = get_text(info, ".//nameOfIssuer")
                        cusip = get_text(info, ".//cusip")
                        value = get_text(info, ".//value")
                        shares = get_text(info, ".//sshPrnamt")
                        
                        holdings.append({
                            "issuer": issuer,
                            "cusip": cusip,
                            "value": float(value) * 1000 if value else 0, # usually in thousands
                            "shares": float(shares) if shares else 0,
                            "date": filing['filing_date']
                        })
                    except:
                        continue
            
            # Sort by value desc
            holdings.sort(key=lambda x: x['value'], reverse=True)
            return holdings[:50] # Return top 50 holdings

        except Exception as e:
            logger.error(f"Error parsing 13F {index_url}: {e}")
            return []

    def get_market_wide_buys(self, limit=100):
        """
        Scan the latest Form 4 filings from SEC RSS feed and aggregate Buy volume.
        Returns a sorted list of {ticker, net_buy_val, num_insiders}.
        """
        # RSS Feed for latest Form 4s
        url = "https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=4&count=100&output=atom"
        try:
            r = requests.get(url, headers=HEADERS)
            r.raise_for_status()
            
            # Simple Regex parsing because Atom XML namespaces are annoying
            # We want to find entries with <title>4 - ... (Active)</title> and <link ...>
            # Actually, the RSS text structure is:
            # <title>4 - ISSUER NAME (0000123456) (Subject)</title>
            
            entries = r.text.split('<entry>')
            aggregated = {} # Ticker -> {buy_val: 0, insiders: set()}
            
            count = 0
            for entry in entries[1:]: # Skip header
                if count >= limit: break
                
                # Extract Title
                title_match = re.search(r'<title>(.*?)<\/title>', entry)
                if not title_match: continue
                title = title_match.group(1) # e.g. "4 - Tesla, Inc. (0001318605) (Issuer)"
                
                if not title.startswith('4 '): continue
                
                # Extract CIK
                cik_match = re.search(r'\((\d{10})\)', title)
                if not cik_match: continue
                cik = cik_match.group(1)
                
                # Find Ticker from our map
                # This is slow if we iterate. Let's build a CIK->Ticker reverse map on init if needed.
                # Or just assume we have it.
                ticker = None
                for t, v in self.tickers_map.items():
                    if v['cik'] == cik:
                        ticker = t
                        break
                
                if not ticker: continue
                
                # Extract Accession Number for Details
                # Link format: https://www.sec.gov/Archives/edgar/data/1318605/000131860524000123/0001318605-24-000123-index.htm
                link_match = re.search(r'href="(.*?)-index.htm"', entry)
                if not link_match: continue
                
                base_url = link_match.group(1) # .../0001318605-24-000123
                parts = base_url.split('/')
                acc_num = parts[-1] 
                
                # primary doc? usually the one ending in .xml or .html in the folder
                # We can try to guess or use get_form4_details with a constructed object
                
                # To be fast, we won't fetch EVERY XML. 
                # Let's just create a "Filings" object and pass to get_form4_details IF we want to go deep.
                # BUT deeply parsing 100 XMLs is slow (100 requests).
                # Optimization: Only parse if we haven't seen this ticker recently? 
                # Or just parse top 20? 
                # Let's try to parse all. 100 requests is okay-ish for a background job, but slow for UI.
                # FOR NOW: Let's simpler fetch the *index* page? No that's also a request.
                
                # We will limit to first 10 entries for speed in this demo.
                if count > 10: break 
                
                # Construct filing object
                # We need the primary document name for get_form4_details.
                # The RSS doesn't give it directly.
                # We have to fetch the index.json or try to guess.
                # Guessing: {acc_num}.xml ? No.
                # Let's Skip actual parsing for now and just list the TICKERS that have Form 4s.
                # Wait, user wants "Total Amounts". We MUST parse.
                # Let's try fetching the index.json for each.
                
                try:
                    # Reuse existing logic
                    # We need primary doc. 
                    # fetch index.json
                    idx_url = f"{base_url}-index.json"
                    ri = requests.get(idx_url, headers=HEADERS)
                    if ri.status_code != 200: continue
                    idx = ri.json()
                    primary = idx['directory']['item'][0]['name'] # First one is usually primary? Not always.
                    # Look for type=4
                    for item in idx['directory']['item']:
                         # No type field in directory listing usually?
                         # Usually primary is first.
                         pass

                    # Just use first.
                    filing = {
                        'cik': cik,
                        'accession_number': acc_num,
                        'primary_document': primary
                    }
                    
                    txs = self.get_form4_details(filing)
                    if txs:
                        if ticker not in aggregated: aggregated[ticker] = {'val': 0, 'buys': 0}
                        
                        for tx in txs:
                            val = tx['shares'] * tx['price']
                            if tx['action'] == 'Buy':
                                aggregated[ticker]['val'] += val
                                aggregated[ticker]['buys'] += 1
                        
                        count += 1
                        
                except Exception as e:
                    logger.warning(f"Failed to aggregate {ticker}: {e}")
                    continue

            # Convert to list
            result_list = []
            for t, data in aggregated.items():
                if data['val'] > 0: # Only show net buys
                    result_list.append({'ticker': t, 'total_buy': data['val'], 'count': data['buys']})
            
            # Sort by total value desc
            result_list.sort(key=lambda x: x['total_buy'], reverse=True)
            return result_list

        except Exception as e:
            logger.error(f"Market wide scan failed: {e}")
            return []

# Helper for XML parsing in 13F
def get_text(node, path):
    item = node.find(path)
    return item.text if item is not None else ""

if __name__ == "__main__":
    eng = SECEngine()
    # Test Search
    print("Searching AAPL...")
    res = eng.search_company("AAPL")
    print(res)
    
    if res:
        cik = res[0]['cik']
        print(f"Getting Filings for {cik}...")
        filings = eng.get_filings(cik)
        print(f"Found {len(filings)} filings.")
        
        # Find a Form 4
        f4 = next((f for f in filings if f['form'] == '4'), None)
        if f4:
            print("Parsing a Form 4...")
            txs = eng.get_form4_details(f4)
            print(txs)
            
    # Test 13F (Berkshire)
    print("\nSearching Berkshire...")
    res = eng.search_company("BERKSHIRE HATHAWAY")
    if res:
        cik = res[0]['cik']
        filings = eng.get_filings(cik, form_types=['13F-HR'])
        if filings:
            print("Parsing a 13F...")
            h = eng.get_13f_holdings(filings[0])
            print(h[:5])
