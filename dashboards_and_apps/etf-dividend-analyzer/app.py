import os
import json
import traceback
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory
import yfinance as yf
import pandas as pd
import numpy as np

app = Flask(__name__, static_folder='static')

@app.route('/')
def index():
    return app.send_static_file('index.html')

@app.route('/<path:path>')
def send_static(path):
    return send_from_directory('static', path)

@app.route('/api/analyze', methods=['POST'])
def analyze():
    try:
        data = request.json
        tickers = data.get('tickers', [])
        initial_capital = float(data.get('initialCapital', 10000))
        tax_rate = float(data.get('taxRate', 30.0)) / 100.0 # user sends percentage like 30
        start_date = data.get('startDate')
        end_date = data.get('endDate')
        
        results = []
        
        for ticker in tickers:
            ticker = ticker.strip().upper()
            if not ticker: continue
            try:
                # Fetch data
                t = yf.Ticker(ticker)
                
                # Fetch historical prices (Close)
                hist = t.history(start=start_date, end=end_date)
                if hist.empty:
                    continue
                
                # Fetch dividends in that period
                divs = t.dividends
                
                # Convert hist index to naive timezone for clean alignment
                if hist.index.tz is not None:
                    hist.index = hist.index.tz_localize(None)
                
                if not divs.empty:
                    if divs.index.tz is not None:
                        divs.index = divs.index.tz_localize(None)
                        
                    # Filter dividends by date range manually
                    sd = pd.to_datetime(start_date)
                    ed = pd.to_datetime(end_date)
                    divs = divs[(divs.index >= sd) & (divs.index <= ed)]
                
                df = pd.DataFrame({
                    'close': hist['Close']
                })
                
                div_series = pd.Series(dtype=float)
                if not divs.empty:
                    # align indexes by normalizing time to midnight
                    divs.index = divs.index.normalize()
                    div_series = divs
                
                df.index = df.index.normalize()
                # Use groupby in case there are multiple entries on the same day (rare, but good practice)
                df = df.groupby(df.index).last()
                if not div_series.empty:
                    div_series = div_series.groupby(div_series.index).sum()
                    
                df['dividend'] = div_series
                df['dividend'] = df['dividend'].fillna(0.0)
                
                # Ensure continuous chronological order
                df = df.sort_index()
                
                # Setup simulation variables
                drip_shares = initial_capital / df['close'].iloc[0]
                drip_value_history = []
                drip_dividends_total = 0.0
                drip_tax_total = 0.0
                
                nodrip_shares = initial_capital / df['close'].iloc[0]
                nodrip_cash = 0.0
                nodrip_value_history = []
                nodrip_dividends_total = 0.0
                nodrip_tax_total = 0.0
                
                dates = []
                
                for date, row in df.iterrows():
                    price = row['close']
                    div_per_share = row['dividend']
                    
                    if div_per_share > 0:
                        # DRIP
                        gross_div_drip = drip_shares * div_per_share
                        tax_drip = gross_div_drip * tax_rate
                        net_div_drip = gross_div_drip - tax_drip
                        
                        drip_dividends_total += gross_div_drip
                        drip_tax_total += tax_drip
                        drip_shares += net_div_drip / price # reinvest
                        
                        # NO DRIP
                        gross_div_nodrip = nodrip_shares * div_per_share
                        tax_nodrip = gross_div_nodrip * tax_rate
                        net_div_nodrip = gross_div_nodrip - tax_nodrip
                        
                        nodrip_dividends_total += gross_div_nodrip
                        nodrip_tax_total += tax_nodrip
                        nodrip_cash += net_div_nodrip
                    
                    drip_value = drip_shares * price
                    drip_value_history.append(round(drip_value, 2))
                    
                    nodrip_value = nodrip_shares * price + nodrip_cash
                    nodrip_value_history.append(round(nodrip_value, 2))
                    
                    dates.append(date.strftime('%Y-%m-%d'))
                
                years = (df.index[-1] - df.index[0]).days / 365.25
                if years <= 0: years = 1
                
                final_drip_value = drip_value_history[-1]
                drip_cagr = ((final_drip_value / initial_capital) ** (1 / years)) - 1
                drip_avg_yield = (drip_dividends_total / years) / initial_capital
                
                final_nodrip_value = nodrip_value_history[-1]
                nodrip_cagr = ((final_nodrip_value / initial_capital) ** (1 / years)) - 1
                nodrip_avg_yield = (nodrip_dividends_total / years) / initial_capital
                
                results.append({
                    "ticker": ticker,
                    "dates": dates,
                    "dripHistory": drip_value_history,
                    "nodripHistory": nodrip_value_history,
                    "metrics": {
                        "drip": {
                            "finalValue": final_drip_value,
                            "cagr": drip_cagr,
                            "totalReturn": (final_drip_value / initial_capital) - 1,
                            "dividendsPaid": drip_dividends_total,
                            "taxPaid": drip_tax_total,
                            "avgYield": drip_avg_yield
                        },
                        "nodrip": {
                            "finalValue": final_nodrip_value,
                            "cagr": nodrip_cagr,
                            "totalReturn": (final_nodrip_value / initial_capital) - 1,
                            "dividendsPaid": nodrip_dividends_total,
                            "taxPaid": nodrip_tax_total,
                            "avgYield": nodrip_avg_yield
                        }
                    }
                })
                
            except Exception as e:
                print(f"Error processing {ticker}: {traceback.format_exc()}")
                
        return jsonify({"success": True, "results": results})
        
    except Exception as e:
        print(traceback.format_exc())
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == '__main__':
    if not os.path.exists('static'):
        os.makedirs('static')
    app.run(host='127.0.0.1', port=5000, debug=True)
