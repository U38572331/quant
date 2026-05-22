import numpy as np
from scipy.stats import norm
import pandas as pd

class AdvancedCalculator:
    def __init__(self, interest_rate=0.0):
        self.r = interest_rate

    def calculate_forward_price(self, S, T, r=0.03, q=0.0):
        """
        Calculates Forward Price F = S * e^((r-q)T)
        """
        return S * np.exp((r - q) * T)

    def calculate_greeks(self, df):
        """
        Calculates advanced Greeks for the entire DataFrame using Vectorized Numpy operations.
        Performance: ~100x faster than apply().
        """
        if df.empty:
            return df
            
        # Ensure native types for numpy
        S = df['underlying_price'].values.astype(float)
        K = df['strike'].values.astype(float)
        T = df['time_to_expiry_years'].values.astype(float)
        sigma = df['mark_iv'].values.astype(float) / 100.0
        r = 0.03 # Risk Free Rate
        q = 0.0
        
        # Avoid division by zero and invalid inputs
        # Mask for valid entries (T > 0, sigma > 0)
        valid_mask = (T > 0.001) & (sigma > 0) & (S > 0)
        
        # Initialize result arrays with NaNs
        n = len(df)
        delta = np.full(n, np.nan)
        gamma = np.full(n, np.nan)
        vega = np.full(n, np.nan)
        theta = np.full(n, np.nan)
        rho = np.full(n, np.nan)
        vanna = np.full(n, np.nan)
        charm = np.full(n, np.nan)
        vomma = np.full(n, np.nan)
        gex = np.full(n, np.nan)
        forward_prices = np.full(n, np.nan)
        
        # --- Vectorized Calculations (Valid Only) ---
        S_v = S[valid_mask]
        K_v = K[valid_mask]
        T_v = T[valid_mask]
        sigma_v = sigma[valid_mask]
        
        sqrt_T = np.sqrt(T_v)
        
        # Forward Price F = S * e^(rT)
        F_v = S_v * np.exp((r - q) * T_v)
        forward_prices[valid_mask] = F_v
        
        # d1 / d2 (Black-76)
        d1 = (np.log(F_v / K_v) + 0.5 * sigma_v**2 * T_v) / (sigma_v * sqrt_T)
        d2 = d1 - sigma_v * sqrt_T
        
        # PDFs and CDFs
        N_d1 = norm.cdf(d1)
        N_d2 = norm.cdf(d2)
        n_d1 = norm.pdf(d1)
        
        # Discount Factor
        df_r = np.exp(-r * T_v)
        
        # Common Gamma / Vega
        # Gamma (Spot) = n(d1) / (S * sigma * sqrt(T)) or Forward? 
        # Using Spot Gamma formula consistent with "S^2" GEX
        # Gamma = n(d1) / (S * sigma * sqrt(T)) 
        gamma_v = n_d1 / (S_v * sigma_v * sqrt_T)
        
        # Vega = S * n(d1) * sqrt(T) / 100
        vega_v = S_v * n_d1 * sqrt_T / 100.0
        
        # --- Call / Put Differences ---
        is_call = df['instrument_type'].values == 'call'
        call_mask = valid_mask & is_call
        put_mask = valid_mask & (~is_call)
        
        # Subset indices for rebuilding
        # Valid Calls
        if np.any(call_mask):
            # We need to re-slice from the '_v' arrays which are already subsetted? 
            # No, logic is tricky with double masking.
            # Easier: Calculate All as Call first, then adjust Put.
            
            # Delta
            delta[valid_mask] = N_d1 # Default Call
            
            # Theta (Call)
            # theta = (- S n(d1) sigma / 2sqrt(T) - r K e^-rT N(d2)) / 365
            theta_sub = (- (S_v * n_d1 * sigma_v) / (2 * sqrt_T) - r * K_v * df_r * N_d2) / 365.0
            
            # Rho (Call)
            rho_sub = (K_v * T_v * df_r * N_d2) / 100.0
            
            # Advanced
            vanna_sub = -n_d1 * d2 / sigma_v
            charm_sub = -n_d1 * (d2 / (2 * T_v))
            vomma_sub = vega_v * d1 * d2 / sigma_v
            
            # Assign to main arrays (this assigns assuming ALL are Calls, will correct Puts)
            theta[valid_mask] = theta_sub
            rho[valid_mask] = rho_sub
            vanna[valid_mask] = vanna_sub
            charm[valid_mask] = charm_sub
            vomma[valid_mask] = vomma_sub
            gamma[valid_mask] = gamma_v
            vega[valid_mask] = vega_v
            
        # Correct Puts
        # Put Delta = Call Delta - 1
        # Put Theta, Rho differ
        if np.any(put_mask):
            # Indices in the full array
            idxs = np.where(put_mask)[0]
            
            # But we need valid_mask indices corresponding to Puts.
            # Let's perform full vector calculation for Puts specifically to be safe and clear.
            
            # Re-slice for Puts
            S_p = S[put_mask]
            K_p = K[put_mask]
            T_p = T[put_mask]
            sigma_p = sigma[put_mask]
            r_p = r
            
            sqrt_T_p = np.sqrt(T_p)
            F_p = S_p * np.exp((r - q) * T_p)
            d1_p = (np.log(F_p / K_p) + 0.5 * sigma_p**2 * T_p) / (sigma_p * sqrt_T_p)
            d2_p = d1_p - sigma_p * sqrt_T_p
            
            N_d1_p = norm.cdf(d1_p)
            N_d2_p = norm.cdf(d2_p)
            n_d1_p = norm.pdf(d1_p)
            df_r_p = np.exp(-r * T_p)

            # Delta Put
            delta[put_mask] = N_d1_p - 1.0
            
            # Theta Put
            theta[put_mask] = (- (S_p * n_d1_p * sigma_p) / (2 * sqrt_T_p) + r * K_p * df_r_p * (1 - N_d2_p)) / 365.0
            
            # Rho Put
            rho[put_mask] = (-K_p * T_p * df_r_p * (1 - N_d2_p)) / 100.0
            
            # Advanced (Vanna/Vomma same, Charm differs slightly or Approx same?)
            # Charm Put
            charm[put_mask] = -n_d1_p * (d2_p / (2 * T_p)) # Using approx
            vanna[put_mask] = -n_d1_p * d2_p / sigma_p
            vomma[put_mask] = (S_p * n_d1_p * sqrt_T_p / 100.0) * d1_p * d2_p / sigma_p

        # GEX Calculation
        # GEX = OI * Gamma * S^2
        # Use filled 'gamma' array
        oi = df['open_interest'].values.astype(float)
        gex = oi * gamma * (S**2)
        
        # Populate DataFrame columns
        df['delta'] = delta
        df['gamma'] = gamma
        df['vega'] = vega
        df['theta'] = theta
        df['rho'] = rho
        df['vanna'] = vanna
        df['charm'] = charm
        df['vomma'] = vomma
        df['gex'] = gex
        df['forward_price'] = forward_prices
        
        return df

    def process_dataframe(self, df):
        if df.empty:
            return df
        # Call vectorized calculator directly
        # process_dataframe used to loop, now it calls the block
        return self.calculate_greeks(df)
