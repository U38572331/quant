import os
import time
import requests
import pandas as pd

class AlphaVantageFetcher:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://www.alphavantage.co/query"
        
    def fetch_daily_data(self, symbol: str) -> pd.DataFrame:
        """
        Fetches daily historical data for a symbol.
        Returns a sorted DataFrame with ['Open', 'High', 'Low', 'Close', 'Volume'].
        """
        params = {
            "function": "TIME_SERIES_DAILY",
            "symbol": symbol,
            "outputsize": "compact",
            "apikey": self.api_key,
            "datatype": "json"
        }
        res = requests.get(self.base_url, params=params)
        data = res.json()
        
        if "Time Series (Daily)" not in data:
            print(f"[Daily] Error or Rate Limit fetching {symbol}: {data}")
            return pd.DataFrame()
            
        df = pd.DataFrame.from_dict(data["Time Series (Daily)"], orient='index')
        df.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
        df = df.astype(float)
        df.index = pd.to_datetime(df.index)
        df = df.sort_index()
        return df

    def fetch_intraday_data(self, symbol: str, interval: str = '5min') -> pd.DataFrame:
        """
        Fetches trailing 30 days of intraday data.
        Returns a sorted DataFrame with ['Open', 'High', 'Low', 'Close', 'Volume'].
        """
        params = {
            "function": "TIME_SERIES_INTRADAY",
            "symbol": symbol,
            "interval": interval,
            "outputsize": "compact",
            "apikey": self.api_key,
            "datatype": "json"
        }
        res = requests.get(self.base_url, params=params)
        data = res.json()
        
        key = f"Time Series ({interval})"
        if key not in data:
            print(f"[Intraday] Error or Rate Limit fetching {symbol}: {data}")
            return pd.DataFrame()
            
        df = pd.DataFrame.from_dict(data[key], orient='index')
        df.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
        df = df.astype(float)
        df.index = pd.to_datetime(df.index)
        df = df.sort_index()
        return df
