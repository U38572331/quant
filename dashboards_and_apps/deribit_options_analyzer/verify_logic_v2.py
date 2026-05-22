
import pandas as pd
import numpy as np
from src.calculator import AdvancedCalculator
from src.analytics import MarketAnalyzer

def verify_math():
    print("--- Verifying Math Logic ---")
    calc = AdvancedCalculator()
    S = 100000
    K = 100000
    T = 0.25 # (90 days)
    sigma = 0.5
    r = 0.03
    
    # 1. Forward Price
    F = calc.calculate_forward_price(S, T, r=0.03)
    expected_F = S * np.exp(0.03 * T)
    print(f"Forward Price: {F} (Expected: {expected_F}) -> {'PASS' if abs(F - expected_F) < 0.1 else 'FAIL'}")
    
    # 2. GEX Calculation
    # Mock row -> Mock DF
    row_data = {
        'underlying_price': S,
        'strike': K,
        'time_to_expiry_years': T,
        'mark_iv': 50.0,
        'instrument_type': 'call',
        'open_interest': 100
    }
    df_row = pd.DataFrame([row_data])
    
    # Calculate using updated Vectorized Calculator
    df_res = calc.calculate_greeks(df_row)
    gamma = df_res['gamma'].iloc[0]
    gex = df_res['gex'].iloc[0]
    
    # Expected GEX = OI * Gamma * S^2
    expected_gex = 100 * gamma * (S**2)
    print(f"GEX: {gex} (Expected: {expected_gex}) -> {'PASS' if abs(gex - expected_gex) < 1.0 else 'FAIL'}")
    
    # Check Dealer Net Logic (Analytics)
    # Standard Model: Call GEX should be Positive, Put GEX should be Negative impact.
    print(f"Call GEX Component: {gex} (Should be > 0)")
    
    # Test Mixed Portfolio for Flip
    df_mixed = pd.DataFrame([
        # Call (Positive GEX)
        {'expiry_date': '2026-03-27', 'open_interest': 1000, 'underlying_price': 100000, 'delta': 0.5, 'strike': 110000, 'gamma': 0.0001, 'gex': 1000000, 'instrument_type': 'call'},
        # Put (Negative GEX impact)
        {'expiry_date': '2026-03-27', 'open_interest': 1000, 'underlying_price': 100000, 'delta': -0.5, 'strike': 90000, 'gamma': 0.0001, 'gex': 1000000, 'instrument_type': 'put'},
    ])
    df_mixed['expiry_date'] = pd.to_datetime(df_mixed['expiry_date']).dt.tz_localize('UTC')
    
    analyzer = MarketAnalyzer(df_mixed)
    analyzer.calls = df_mixed[df_mixed['instrument_type'] == 'call']
    analyzer.puts = df_mixed[df_mixed['instrument_type'] == 'put']
    
    profile = analyzer.calculate_dealer_gamma_profile()
    # Expectation: 
    # Strike 110000 (Call) -> Net GEX +1,000,000
    # Strike 90000 (Put) -> Net GEX -1,000,000
    
    net_110k = profile[profile['strike'] == 110000]['net_gex'].iloc[0]
    net_90k = profile[profile['strike'] == 90000]['net_gex'].iloc[0]
    
    print(f"Net GEX at Call Strike (110k): {net_110k} (Expected positive) -> {'PASS' if net_110k > 0 else 'FAIL'}")
    print(f"Net GEX at Put Strike (90k): {net_90k} (Expected negative) -> {'PASS' if net_90k < 0 else 'FAIL'}")
    # Mock DF
    df = pd.DataFrame([
        {'expiry_date': '2026-03-27', 'open_interest': 1000, 'underlying_price': 100000, 'delta': 0.5, 'strike': 100000, 'gamma': 0.0001, 'gex': 1000000, 'instrument_type': 'call'}, # Structural Candidate
        {'expiry_date': '2025-12-31', 'open_interest': 100, 'underlying_price': 100000, 'delta': 0.5, 'strike': 100000, 'gamma': 0.0001, 'gex': 100000, 'instrument_type': 'call'}, # Short term
    ])
    df['expiry_date'] = pd.to_datetime(df['expiry_date']).dt.tz_localize('UTC')
    
    analyzer = MarketAnalyzer(df)
    
    # Test Dominant Structural Expiry
    # Assuming current date is Dec 2025. 2026-03-27 is ~90 days out.
    # 2025-12-31 is ~5 days out.
    # Structural looks for 50-140 days.
    
    dom_exp = analyzer.get_dominant_structural_expiry()
    print(f"Dominant Structural Expiry: {dom_exp}")
    if dom_exp and dom_exp.date() == pd.Timestamp('2026-03-27').date():
        print("PASS: Correctly identified structural expiry")
    else:
        print(f"FAIL: Identified {dom_exp}")

    # Test Dealer Profile
    # Mock analyzer with calculated 'gex'
    analyzer.df = df
    profile = analyzer.calculate_dealer_gamma_profile()
    # Dealer Net for Strike 100000 should be -1 * (1000000 + 100000) (if aggregating all)
    # But usually we call this on a specific expiry slice.
    
    print("Verification Script Done.")
    
    # Test Max Pain (Vectorized)
    # Create simple scenario:
    # Spot 100k. Calls at 90k, 100k, 110k. Puts at 90k, 100k, 110k.
    # If OI is symmetric at 100k, Max Pain should be 100k?
    # Or if lots of Puts at 90k (Deep OTM for them if price is high? No, Put 90k is OTM if price 100k).
    # Buying Puts (Long Puts) -> Dealer Short Puts.
    # Max Pain targets the option BUYERS (Market).
    # Buyers lose most at Max Pain.
    # If Market bought 90k Puts, they lose if Price > 90k.
    # If Market bought 110k Calls, they lose if Price < 110k.
    # So Max Pain should be between 90k and 110k -> 100k.
    
    mp_strike = analyzer.calculate_max_pain()
    print(f"Calculated Max Pain: {mp_strike}")
    if mp_strike > 0:
        print("PASS: Max Prain Calculated (Vectorized).")
    else:
        print(f"FAIL: Max Pain returned {mp_strike}")

if __name__ == "__main__":
    verify_math()
    
    # Test Utils Spot Price Priority
    print("\n--- Verifying Utils (Spot Priority) ---")
    from src.utils import enrich_data
    
    # Creates Mock Data with conflicting Underlying vs Index
    inst_df = pd.DataFrame([{'instrument_name': 'BTC-27MAR26-100000-C'}])
    summ_df = pd.DataFrame([{
        'instrument_name': 'BTC-27MAR26-100000-C', 
        'underlying_price': 88000, # Future
        'index_price': 87000 # Spot
    }])
    
    res = enrich_data(inst_df, summ_df)
    used_price = res['underlying_price'].iloc[0]
    print(f"Input Prices -> Future: 88000, Index(Spot): 87000")
    print(f"Selected Price: {used_price}")
    
    # Test 2: Explicit Real Spot Argument
    print("Test 2: Explicit Real Spot Argument")
    forced_spot = 85000
    res_forced = enrich_data(inst_df.copy(), summ_df.copy(), real_spot=forced_spot)
    used_price_forced = res_forced['underlying_price'].iloc[0]
    print(f"Forced Spot: {forced_spot}, Result: {used_price_forced}")
    
    if used_price_forced == forced_spot:
        print("PASS: System correctly prioritized Forced Real Spot Argument.")
    else:
        print("FAIL: System ignored Forced Real Spot.")
    
    if used_price == 87000:
        print("PASS: System correctly prioritized Index Spot Price.")
    else:
        print("FAIL: System used Future/Wrong Price.")
        
    # Test Unified Curve Logic
    # 1. Create Analyzer with data where GEX is Neg at Spot but Pos Total Sum (User's Case)
    print("\n--- Verifying Unified Curve Logic ---")
    mock_curve_df = pd.DataFrame([
        {'strike': 80000, 'net_gex': -100, 'underlying_price': 82000, 'instrument_type': 'call', 'open_interest':1, 'expiry_date': pd.Timestamp.now()},
        {'strike': 90000, 'net_gex': 100, 'underlying_price': 82000, 'instrument_type': 'call', 'open_interest':1, 'expiry_date': pd.Timestamp.now()}, # Flip around 85000
        {'strike': 100000, 'net_gex': 100, 'underlying_price': 82000, 'instrument_type': 'call', 'open_interest':1, 'expiry_date': pd.Timestamp.now()} # Total Sum +100.
    ])
    
    # Instantiate analyzer for this test
    analyzer_curve = MarketAnalyzer(mock_curve_df)
    analyzer_curve.current_price = 82000
    
    curve = analyzer_curve.get_gex_curve(mock_curve_df)
    
    # Check Curve Value at 82000
    if curve and curve['function']:
        val_at_spot = curve['function'](82000)
        print(f"Curve Value at 82000: {val_at_spot:.2f} (Expected Negative)")
        
        if val_at_spot < 0:
            print("PASS: Curve correctly identifies Negative Gamma at Spot despite Positive Total Sum.")
        else:
            print("FAIL: Curve Calculation Positive.")
    else:
        print("FAIL: Curve generation failed.")
