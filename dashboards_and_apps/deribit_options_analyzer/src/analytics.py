import pandas as pd
import numpy as np

class MarketAnalyzer:
    def __init__(self, df):
        self.df = df
        self.current_price = df['underlying_price'].iloc[0] if not df.empty else 0
        self.calls = df[df['instrument_type'] == 'call'].copy()
        self.puts = df[df['instrument_type'] == 'put'].copy()

    def clean_data(self):
        """
        Filters data based on User Requirements:
        - Delta in [0.05, 0.95] (Absolute)
        - OI > 10 (Liquidity Check, arbitrary low threshold or Volume > 0)
        """
        if self.df.empty:
            return
            
        # Delta cleaning
        # Delta might be negative for puts
        self.df = self.df[self.df['delta'].abs().between(0.05, 0.95)].copy()
        
        # Liquidity cleaning
        self.df = self.df[self.df['open_interest'] > 0].copy()

    def get_dominant_structural_expiry(self):
        """
        Scans future 50-140 days.
        Returns the expiry date with the MAXIMUM Total Notional OI.
        Notional OI = Sum(OI * Spot)
        """
        if self.df.empty:
            return None
            
        # Use UTC to match DF
        now = pd.Timestamp.now(tz='UTC')
        # Ensure expiry_date is datetime
        if not pd.api.types.is_datetime64_any_dtype(self.df['expiry_date']):
             self.df['expiry_date'] = pd.to_datetime(self.df['expiry_date'], utc=True) # Force UTC
             
        unique_expiries = self.df['expiry_date'].unique()
        candidates = []
        
        for exp in unique_expiries:
            exp_ts = pd.Timestamp(exp)
            if exp_ts.tz is None:
                exp_ts = exp_ts.tz_localize('UTC')
                
            days_diff = (exp_ts - now).days
            
            if 50 <= days_diff <= 140:
                # Calculate Total Notional OI for this expiry
                # Notional = OI * Underlying (Spot)
                # Since OI is in contracts (BTC), Notional = OI * Price
                exp_df = self.df[self.df['expiry_date'] == exp]
                spot = exp_df['underlying_price'].mean() # Approx
                total_oi = exp_df['open_interest'].sum()
                notional = total_oi * spot
                
                candidates.append({'date': exp_ts, 'notional': notional})
        
        if not candidates:
            return None
            
        # Return date with Max Notional
        best = max(candidates, key=lambda x: x['notional'])
        return best['date']

    def get_standard_quarters(self):
        """
        Returns a list of 'Standard' Calendar Quarterly expiries available in data.
        (Mar, Jun, Sep, Dec)
        """
        if self.df.empty:
            return []
            
        if not pd.api.types.is_datetime64_any_dtype(self.df['expiry_date']):
             self.df['expiry_date'] = pd.to_datetime(self.df['expiry_date'], utc=True)
             
        unique_expiries = sorted(self.df['expiry_date'].unique())
        quarters = []
        
        # Standard months: 3, 6, 9, 12
        for exp in unique_expiries:
            ts = pd.Timestamp(exp)
            if ts.month in [3, 6, 9, 12]:
                # Heuristic: Usually the LAST Friday or specific day? 
                # Let's just return all of them, or filter by 'is major'.
                # Usually major quarters have high OI.
                # Let's return them all, allow UI to pick.
                quarters.append(ts)
                
        return quarters

    def calculate_dealer_gamma_profile(self):
        """
        Calculates Dealer Net Gamma per strike using 'Standard Model' assumptions.
        
        Standard Model (SpotGamma/Kingfisher style):
        - Call OI: Market Selling (Covered Calls) -> Dealer Long -> Positive Gamma (Green)
        - Put OI: Market Buying (Hedges) -> Dealer Short -> Negative Gamma (Red)
        
        Formula: Net GEX = (Call Gamma * OI) - (Put Gamma * OI)
        """
        strikes = sorted(list(set(self.calls['strike'].unique()) | set(self.puts['strike'].unique())))
        profile = []
        
        for k in strikes:
            # Get Call GEX at this strike
            c_df = self.calls[self.calls['strike'] == k]
            # Sum GEX (which is OI * Gamma * S^2)
            c_gex = c_df['gex'].sum()
            
            # Get Put GEX at this strike
            p_df = self.puts[self.puts['strike'] == k]
            p_gex = p_df['gex'].sum()

            # Standard Logic: Calls contribute Positive, Puts contribute Negative
            net_gex = c_gex - p_gex
            
            profile.append({'strike': k, 'dealer_net_gamma': net_gex, 'net_gex': net_gex})
            
        if not profile:
             return pd.DataFrame(columns=['strike', 'dealer_net_gamma', 'net_gex'])
             
        return pd.DataFrame(profile)

    def calculate_gex_profile(self):
        """
        Legacy method kept for compatibility but updated to use new Dealer Logic if needed.
        Or redirect to calculate_dealer_gamma_profile.
        Let's keep the old 'Net GEX' structure but updated logic:
        Net GEX = - (Sum GEX)
        """
        # This method was used for the Bar Chart.
        # User wants "Dealer Net Gamma".
        df_profile = self.calculate_dealer_gamma_profile()
        # Rename for compatibility if needed, or update App to use 'dealer_net_gamma'
        df_profile['net_gex'] = df_profile['dealer_net_gamma'] 
        return df_profile

    def get_gex_curve(self, gex_df, num_points=200):
        """
        Generates the Interpolated GEX Curve (Unified Source of Truth).
        Returns a dictionary or object with:
        - x_smooth: Array of Prices (Strikes)
        - y_smooth: Array of Net GEX values
        - interpolator: The function f(price) -> ex
        """
        if gex_df.empty:
             return None
             
        # Sort by strike
        gex_df = gex_df.sort_values('strike').reset_index(drop=True)
        
        x = gex_df['strike'].values
        y = gex_df['net_gex'].values
        
        if len(x) < 2:
            return None
            
        # Interpolation Logic
        from scipy.interpolate import make_interp_spline
        
        try:
            # Handle edge case: few points for cubic
            k_val = 3 if len(x) > 3 else 1
            spl = make_interp_spline(x, y, k=k_val)
            
            # Generate Smooth X range
            x_min, x_max = x.min(), x.max()
            x_smooth = np.linspace(x_min, x_max, num_points)
            y_smooth = spl(x_smooth)
            
            return {
                'x': x_smooth,
                'y': y_smooth,
                'function': spl,
                'raw_x': x,
                'raw_y': y
            }
        except Exception as e:
            # Fallback
            return {
                'x': x, 
                'y': y, 
                'function': None
            }

    def find_flip_level(self, gex_df):
        """
        Finds the Flip Level (Zero Crossing) using the Unified Curve.
        """
        if gex_df.empty:
            return 0
            
        curve = self.get_gex_curve(gex_df)
        if not curve or curve['function'] is None:
             # Fallback to naive discrete scan
            return self._find_flip_discrete(gex_df)
            
        x_smooth = curve['x']
        y_smooth = curve['y']
        
        # Scan smoothed curve for crossing
        for i in range(len(x_smooth) - 1):
             val1 = y_smooth[i]
             val2 = y_smooth[i+1]
             
             if (val1 > 0 and val2 < 0) or (val1 < 0 and val2 > 0):
                  # Linear interpolate between these two close points
                  x1 = x_smooth[i]
                  x2 = x_smooth[i+1]
                  slope = (val2 - val1) / (x2 - x1)
                  if slope != 0:
                      return x1 - (val1 / slope)
                      
        # No crossing found
        total_gex = np.sum(y_smooth) # Integral approximation
        if total_gex > 0:
            return x_smooth[0] # Support
        else:
            return x_smooth[-1] # Resistance

    def _find_flip_discrete(self, df):
        # Fallback method (Old Logic)
        df = df.sort_values('strike')
        for i in range(len(df) - 1):
            g1 = df.iloc[i]['net_gex']
            g2 = df.iloc[i+1]['net_gex']
            k1 = df.iloc[i]['strike']
            k2 = df.iloc[i+1]['strike']
            
            if (g1 > 0 and g2 < 0) or (g1 < 0 and g2 > 0):
                slope = (g2 - g1) / (k2 - k1)
                if slope != 0:
                    return k1 - (g1 / slope)
                    
        total_gex = df['net_gex'].sum()
        if total_gex > 0:
            return df['strike'].min()
        else:
             return df['strike'].max()


    def calculate_max_pain(self):
        """
        Calculates Max Pain price using Vectorized Broadcasting (Institution Grade).
        Performance: O(1) in concept (Matrix Op), vast speedup over O(N*M).
        """
        if self.df.empty:
            return 0
            
        strikes = sorted(list(set(self.calls['strike'].unique()) | set(self.puts['strike'].unique())))
        if not strikes:
            return 0
            
        # Convert to numpy arrays
        # Strikes to Check (Targets)
        K_targets = np.array(strikes) # Shape (M,)
        
        # Option Data
        # Calls
        c_strikes = self.calls['strike'].values # Shape (Nc,)
        c_oi = self.calls['open_interest'].values
        
        # Puts
        p_strikes = self.puts['strike'].values # Shape (Np,)
        p_oi = self.puts['open_interest'].values
        
        # Broadcasting Logic
        # Total Loss at Price P = Sum(Intrinsic * OI)
        
        # 1. Calls Loss (If Price ends at K_target)
        # Intrinsic = max(0, K_target - K_strike)
        # Matrix: (M, Nc)
        # Loss_C = Sum( max(0, K_target - c_strike) * c_oi )
        # Reshape for broadcasting: K_targets (M, 1), c_strikes (1, Nc)
        
        # Values (M, Nc)
        c_intrinsic = np.maximum(0, K_targets[:, None] - c_strikes[None, :])
        c_loss = np.sum(c_intrinsic * c_oi[None, :], axis=1) # Sum over options (axis 1) -> Shape (M,)
        
        # 2. Puts Loss
        # Intrinsic = max(0, K_strike - K_target)
        p_intrinsic = np.maximum(0, p_strikes[None, :] - K_targets[:, None]) 
        p_loss = np.sum(p_intrinsic * p_oi[None, :], axis=1) # Shape (M,)
        
        # Total Loss
        total_loss = c_loss + p_loss
        
        # Find Min Index
        min_idx = np.argmin(total_loss)
        return K_targets[min_idx]

    def filter_by_expiry(self, hours=24, mode='under'):
        """
        Filters the DataFrame by time to expiry.
        mode='under': < hours (Short Term / 0DTE)
        mode='over': > hours (Long Term)
        """
        if self.df.empty:
            return MarketAnalyzer(pd.DataFrame())
            
        # time_to_expiry_years * 365 * 24 = hours
        self.df['hours_to_expiry'] = self.df['time_to_expiry_years'] * 365 * 24
        
        if mode == 'under':
            filtered_df = self.df[self.df['hours_to_expiry'] <= hours].copy()
        else:
            filtered_df = self.df[self.df['hours_to_expiry'] > hours].copy()
            
        return MarketAnalyzer(filtered_df)

    def get_major_expiry(self, timeframe='quarter'):
        """
        Identifies the major expiry date for a given timeframe based on Open Interest.
        timeframe: 'week', 'month', 'quarter'
        """
        if self.df.empty:
            return None
            
        now = pd.Timestamp.now()
        # Ensure expiry_date is datetime
        if not pd.api.types.is_datetime64_any_dtype(self.df['expiry_date']):
             self.df['expiry_date'] = pd.to_datetime(self.df['expiry_date'])
             
        unique_expiries = self.df['expiry_date'].unique()
        
        candidates = []
        
        for exp in unique_expiries:
            exp_ts = pd.Timestamp(exp)
            days_diff = (exp_ts - now).days
            
            is_candidate = False
            if timeframe == 'week':
                # Next 2-9 days (Targeting closest major weekly)
                if 2 <= days_diff <= 10:
                    is_candidate = True
            elif timeframe == 'month':
                # 15-45 days (Targeting next month end)
                if 15 <= days_diff <= 45:
                    is_candidate = True
            elif timeframe == 'quarter':
                # 50-140 days (Targeting next major quarter)
                if 50 <= days_diff <= 140:
                    is_candidate = True
            
            if is_candidate:
                # Calculate total OI for this expiry
                oi = self.df[self.df['expiry_date'] == exp]['open_interest'].sum()
                candidates.append({'date': exp_ts, 'oi': oi})
        
        if not candidates:
            return None
            
        # Return date with max OI
        best = max(candidates, key=lambda x: x['oi'])
        return best['date']

    def generate_ai_summary(self, gex_df, flip, max_pain, context="General"):
        """
        Generates ultra-concise AI summary.
        Regime determined by INTERPOLATED LOCAL GAMMA at Current Spot Price (Curve Logic).
        """
        price = self.current_price
        
        local_gex_val = 0
        total_net_gex = 0 # Keep for reference
        
        if not gex_df.empty:
            # 1. Get Curve
            curve = self.get_gex_curve(gex_df)
            
            # 2. Extract Value at Current Price
            if curve and curve['function']:
                try:
                    # Input: Scalar price. Output: Scalar GEX
                    local_gex_val = float(curve['function'](price))
                except:
                    local_gex_val = 0
            else:
                 # Fallback: Nearest Strike (Old method, but backup only)
                 closest_idx = (gex_df['strike'] - price).abs().idxmin()
                 local_gex_val = gex_df.loc[closest_idx, 'net_gex']
            
            total_net_gex = gex_df['net_gex'].sum()

        # Determine Sentiment Tag & Analysis (Interpolated Local GEX)
        # This matches the Chart Y-value at X=Price
        if local_gex_val > 0:
            sentiment_tag = "BULLISH"
            tag_color = "#00e676" # Bright Green
            regime = "Positive Gamma"
            analysis = "• <b>Regime</b>: Dealer 正 Gamma (提供流動性)。<br>• <b>觀點</b>: 波動受壓抑，價格易區間震盪。"
        else:
            sentiment_tag = "BEARISH"
            tag_color = "#ff1744" # Bright Red
            regime = "Negative Gamma"
            analysis = "• <b>Regime</b>: Dealer 負 Gamma (追漲殺跌)。<br>• <b>觀點</b>: 趨勢易加速，防範急漲急跌。"
            
        # Debug Info match the Chart
        analysis += f"<br><span style='color: #555; font-size: 10px;'>[Debug] Spot: ${price:,.0f} | Chart GEX at Spot: ${local_gex_val/1e6:,.1f}M</span>"
            

        # Key Levels Status
        dist_flip = (price - flip) / price
        if abs(dist_flip) < 0.02:
            flip_desc = "Testing"
            analysis += f"<br>• <b>Flip</b>: 價格測試 ${flip:,.0f}，關注突破方向。"
        elif price > flip:
            flip_desc = "Support"
        else:
            flip_desc = "Resistance"

        dist_pin = (price - max_pain) / price
        if abs(dist_pin) < 0.01:
            pin_desc = "Pinned"
            analysis += f"<br>• <b>Pin</b>: 價格釘在 ${max_pain:,.0f}，波動受限。"
        else:
            pin_desc = "Magnet"
            if abs(dist_pin) < 0.05:
                analysis += f"<br>• <b>Magnet</b>: Max Pain ${max_pain:,.0f} 可能有磁吸效應。"
        
        summary = f"""
<div style="font-family: 'Roboto', sans-serif; font-size: 13px; color: #e0e0e0; margin-bottom: 8px;">
    <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 6px;">
        <span style="color: #8b949e; font-weight: 600; font-size: 11px; letter-spacing: 1px;">{context.upper()}</span>
        <span style="background-color: {tag_color}20; color: {tag_color}; border: 1px solid {tag_color}; padding: 1px 6px; border-radius: 4px; font-size: 10px; font-weight: bold;">{sentiment_tag}</span>
    </div>
    <div style="line-height: 1.6; margin-bottom: 8px;">
        <span style="color: #b0b0b0;">Regime:</span> <span style="color: #ffffff;">{regime}</span><br>
        <span style="color: #b0b0b0;">Flip:</span> <span style="color: #ffffff;">${flip:,.0f}</span> <span style="color: #8b949e; font-size: 11px;">({flip_desc})</span><br>
        <span style="color: #b0b0b0;">Pin:</span> <span style="color: #ffffff;">${max_pain:,.0f}</span> <span style="color: #8b949e; font-size: 11px;">({pin_desc})</span>
    </div>
    <div style="color: #b0b0b0; font-size: 12px; line-height: 1.4; border-top: 1px solid rgba(255,255,255,0.1); padding-top: 6px;">
        {analysis}
    </div>
</div>
"""
        return summary

    def get_atm_iv(self):
        """Calculates the weighted average IV of ATM options."""
        if self.df.empty:
            return 0
            
        # Find strike closest to spot
        price = self.current_price
        closest_strike = self.df.iloc[(self.df['strike'] - price).abs().argsort()[:1]]['strike'].values[0]
        
        # Get options at this strike
        atm_opts = self.df[self.df['strike'] == closest_strike]
        
        if atm_opts.empty:
            return 0
            
        # Average IV
        avg_iv = atm_opts['mark_iv'].mean()
        return avg_iv / 100.0 # Convert to decimal

    def calculate_probability_distribution(self, days=7, num_points=100):
        """
        Calculates the Lognormal Probability Density Function (PDF) for future price.
        """
        S0 = self.current_price
        sigma = self.get_atm_iv()
        T = days / 365.0
        
        if sigma == 0 or T == 0:
            return pd.DataFrame()
            
        # Range: +/- 3 standard deviations
        # std_dev = sigma * sqrt(T)
        # log_ret_std = sigma * np.sqrt(T)
        
        # Create price range
        # 99.7% confidence interval roughly
        lower = S0 * np.exp(-3 * sigma * np.sqrt(T))
        upper = S0 * np.exp(3 * sigma * np.sqrt(T))
        
        prices = np.linspace(lower, upper, num_points)
        
        # Lognormal PDF
        # f(x) = (1 / (x * sigma * sqrt(T) * sqrt(2*pi))) * exp( - (ln(x) - mu)^2 / (2*sigma^2*T) )
        # Here assuming drift mu approx 0 for short term or risk neutral = ln(S0) - 0.5*sigma^2*T
        
        mu = np.log(S0) - 0.5 * sigma**2 * T
        denom = prices * sigma * np.sqrt(T) * np.sqrt(2 * np.pi)
        numer = - (np.log(prices) - mu)**2 / (2 * sigma**2 * T)
        pdf = (1 / denom) * np.exp(numer)
        
        # Normalize to make it look nice (peak at 1 or just raw density)
        # Raw density is fine, but maybe scale for chart
        
        return pd.DataFrame({'price': prices, 'probability': pdf})

    def get_gex_surface(self, points=20):
        """
        Generates 3D Surface Data: X=Expiry, Y=Strike, Z=Net GEX
        """
        if self.df.empty:
            return {}
            
        # Ensure UTC
        if not pd.api.types.is_datetime64_any_dtype(self.df['expiry_date']):
             self.df['expiry_date'] = pd.to_datetime(self.df['expiry_date'], utc=True)
             
        now = pd.Timestamp.now(tz='UTC')

        # Filter: Future Expiries only, up to 180 days
        usage_df = self.df[(self.df['expiry_date'] > now) & (self.df['expiry_date'] < now + pd.Timedelta(days=180))].copy()
        
        if usage_df.empty:
            return {}
            
        expiries = sorted(usage_df['expiry_date'].unique())[:12] # Top 12 expiries
        
        z_matrix = []
        x_dates = []
        
        # Create uniform strike grid centered on price
        center = self.current_price
        if center == 0 or np.isnan(center): center = 50000 # Fallback
        lower = center * 0.7
        upper = center * 1.3
        common_strikes = np.linspace(lower, upper, points).tolist()
        
        for exp in expiries:
            sub = usage_df[usage_df['expiry_date'] == exp]
            days_to_exp = (exp - now).days
            x_dates.append(f"{days_to_exp}d")
            
            # Calculate Profile for this expiry
            sub_analyzer = MarketAnalyzer(sub)
            sub_analyzer.current_price = self.current_price
            profile = sub_analyzer.calculate_dealer_gamma_profile()
            
            if profile.empty:
                z_row = [0] * len(common_strikes)
            else:
                strikes = profile['strike'].values
                gex = profile['net_gex'].values
                # Sort for interp
                idx = np.argsort(strikes)
                strikes = strikes[idx]
                gex = gex[idx]
                # Linear Interp
                z_row = np.interp(common_strikes, strikes, gex, left=0, right=0)
                
            z_matrix.append(z_row.tolist())
            
        return {
            "x": x_dates,
            "y": common_strikes,
            "z": z_matrix
        }

    def get_oi_profile(self):
        """
        Returns Call OI and Put OI per strike for the 'Options Inventory' chart.
        """
        if self.df.empty:
            return pd.DataFrame()
            
        # Group by strike, sum OI
        call_oi = self.calls.groupby('strike')['open_interest'].sum()
        put_oi = self.puts.groupby('strike')['open_interest'].sum()
        
        # Merge
        strikes = sorted(list(set(call_oi.index) | set(put_oi.index)))
        data = []
        for k in strikes:
            c = call_oi.get(k, 0)
            p = put_oi.get(k, 0)
            data.append({"strike": k, "call_oi": float(c), "put_oi": float(p)})
            
        return pd.DataFrame(data)
