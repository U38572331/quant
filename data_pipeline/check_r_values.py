import pandas as pd
df = pd.read_csv(r'C:\Users\user\.gemini\antigravity\scratch\nq_orb_trades_r.csv')
print("Max cum_r:", df['cum_r'].max())
print("Min cum_r:", df['cum_r'].min())
print("Final cum_r:", df['cum_r'].iloc[-1])
print("Max pnl_r:", df['pnl_r'].max())
print("Min pnl_r:", df['pnl_r'].min())
