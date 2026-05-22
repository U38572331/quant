import requests
import pandas as pd
from datetime import datetime

class DeribitClient:
    BASE_URL = "https://www.deribit.com/api/v2/public"

    def get_instruments(self, currency="BTC", kind="option"):
        """Fetch all active option instruments for a currency."""
        url = f"{self.BASE_URL}/get_instruments?currency={currency}&kind={kind}&expired=false"
        try:
            resp = requests.get(url)
            data = resp.json()
            if 'result' in data:
                return pd.DataFrame(data['result'])
            return pd.DataFrame()
        except Exception as e:
            print(f"Error fetching instruments: {e}")
            return pd.DataFrame()

    def get_book_summary_by_currency(self, currency="BTC", kind="option"):
        """Fetch market data (mark price, iv, etc.) for all options of a currency."""
        url = f"{self.BASE_URL}/get_book_summary_by_currency?currency={currency}&kind={kind}"
        try:
            resp = requests.get(url)
            data = resp.json()
            if 'result' in data:
                return pd.DataFrame(data['result'])
            return pd.DataFrame()
        except Exception as e:
            print(f"Error fetching book summary: {e}")
            return pd.DataFrame()

    def get_ticker(self, instrument_name):
        """Fetch ticker for a specific instrument (includes Greeks sometimes)."""
        url = f"{self.BASE_URL}/ticker?instrument_name={instrument_name}"
        try:
            resp = requests.get(url)
            data = resp.json()
            if 'result' in data:
                return data['result']
            return {}
        except Exception as e:
            print(f"Error fetching ticker: {e}")
            return {}

    def get_index_price(self, index_name="btc_usd"):
        """Fetch the current Spot Index Price (Real-Time)."""
        url = f"{self.BASE_URL}/get_index_price?index_name={index_name}"
        try:
            resp = requests.get(url)
            data = resp.json()
            if 'result' in data:
                return data['result']['index_price']
        except Exception as e:
            print(f"Error fetching index price: {e}")
        return None
