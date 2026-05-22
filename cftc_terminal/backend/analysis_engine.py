import pandas as pd
import numpy as np

class AnalysisEngine:
    def __init__(self):
        pass

    def calculate_score(self, market_data):
        """
        Calculate a 0-100 'Prime Score' based on CFTC data.
        
        Inputs:
        - Commercial Net Position (Smart Money): Reversal Indicator
        - Non-Commercial Net Position (Trend): Momentum Indicator
        - Open Interest: Strength Indicator
        
        Logic:
        - If Trend (Non-Comm) is identifying a direction AND OI is rising -> High Score (Trend Strength)
        - If Smart Money (Comm) is extremely divergent -> Reversal Warning (Lowers Score if Bullish)
        
        For simplicity in V1: 
        - We return a 'Bullishness' Score (0-100).
        """
        if not market_data or len(market_data) < 26: # Need some history
            return {"score": 50, "rating": "Neutral", "components": {}}

        # Convert to DF for easier math
        df = pd.DataFrame(market_data)
        # Sort by date asc
        df = df.sort_values('report_date_as_yyyy_mm_dd')
        
        latest = df.iloc[-1]
        
        # 1. Non-Commercial (Speculator) Trend Rank (0-100)
        # Percentile of current net position over last 1 year (52 weeks)
        lookback = min(len(df), 52)
        history_nc = df['net_noncomm'].tail(lookback).values
        current_nc = latest['net_noncomm']
        
        rank_nc = self._percentile_rank(current_nc, history_nc)
        
        # 2. Commercial (Smart Money) Divergence
        # If Commercials are hitting record shorts, it's a bearish signal (they are hedging heavily)
        history_c = df['net_comm'].tail(lookback).values
        current_c = latest['net_comm']
        rank_c = self._percentile_rank(current_c, history_c)
        
        # 3. Open Interest Strength
        # Rising OI validates the trend
        oi_ma = df['open_interest_all'].tail(3).mean()
        oi_prev_ma = df['open_interest_all'].iloc[-6:-3].mean()
        oi_trend = 1 if oi_ma > oi_prev_ma else 0
        
        # Combined Score Calculation
        # Base score is the Speculator Rank (Trend)
        # Adjusted by Commercials (if Comm rank is excessively low/high, it indicates hedging stress)
        
        # Simple weighted model:
        # Bullish Score = (Spec_Rank * 0.6) + (Comm_Rank * 0.2) + (OI_Strength * 20)
        # Note: Commercials usually take opposite side. So High Comm Net (Long) is Bullish.
        
        raw_score = (rank_nc * 0.5) + (rank_c * 0.3) + (oi_trend * 20)
        
        # Normalize/Clamp
        final_score = min(max(raw_score, 0), 100)
        
        rating = "Neutral"
        if final_score > 75: rating = "Strong Bullish"
        elif final_score > 60: rating = "Bullish"
        elif final_score < 25: rating = "Strong Bearish"
        elif final_score < 40: rating = "Bearish"

        return {
            "score": round(final_score),
            "rating": rating,
            "components": {
                "speculator_index": round(rank_nc),
                "smart_money_index": round(rank_c),
                "oi_trend": "Rising" if oi_trend else "Falling"
            },
            "signals": self._generate_signals(rank_nc, rank_c)
        }

    def _percentile_rank(self, val, arr):
        """Calculate percentile rank of val in arr."""
        if len(arr) == 0: return 50
        return (np.sum(arr < val) / len(arr)) * 100

    def _generate_signals(self, rank_nc, rank_c):
        signals = []
        if rank_nc > 90: signals.append("Crowded Longs (Speculators)")
        if rank_nc < 10: signals.append("Crowded Shorts (Speculators)")
        if rank_c > 90: signals.append("Commercials Aggressively Buying")
        if rank_c < 10: signals.append("Commercials Aggressively Hedging")
        
        if rank_nc > 80 and rank_c < 20:
            signals.append("DIVERGENCE: Specs Buying into Comm Selling (Potential Top)")
            
        if rank_nc < 20 and rank_c > 80:
             signals.append("CONVERGENCE: Specs Selling into Comm Buying (Potential Bottom)")
             
        return signals

if __name__ == "__main__":
    # Test stub
    pass
