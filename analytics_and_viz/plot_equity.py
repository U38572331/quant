import pandas as pd
import matplotlib.pyplot as plt
import os

# Set paths
csv_path = r'C:\Users\user\.gemini\antigravity\scratch\trades_log.csv'
output_dir = r'C:\Users\user\.gemini\antigravity\brain\e0e36b8f-ef09-4c53-be6e-e8c576b6fc13'
output_path = os.path.join(output_dir, 'equity_curve.png')

print(f"Reading logs from {csv_path}...")
df = pd.read_csv(csv_path)

if 'PnL' not in df.columns:
    print(f"Error: PnL column not found. Columns: {df.columns}")
    exit(1)

# Calculate cumulative PnL
df['Cumulative_PnL'] = df['PnL'].cumsum()
df['Time'] = pd.to_datetime(df['Time'])

# Plotting
plt.figure(figsize=(12, 6))
plt.plot(df['Time'], df['Cumulative_PnL'], color='#00ffcc', linewidth=2)
plt.fill_between(df['Time'], df['Cumulative_PnL'], color='#00ffcc', alpha=0.1)

plt.title('NQ ORB Strategy - Equity Curve (2021-2025)', color='white', fontsize=14, pad=20)
plt.xlabel('Date', color='white')
plt.ylabel('Cumulative Profit ($)', color='white')

# Style adjustments for "Premium" look
plt.gcf().set_facecolor('#1a1a1a')
plt.gca().set_facecolor('#1a1a1a')
plt.gca().tick_params(colors='white')
for spine in plt.gca().spines.values():
    spine.set_edgecolor('#444444')

plt.grid(True, linestyle='--', alpha=0.2, color='white')
plt.tight_layout()

print(f"Saving chart to {output_path}...")
plt.savefig(output_path, dpi=120, facecolor='#1a1a1a')
print("Done.")
