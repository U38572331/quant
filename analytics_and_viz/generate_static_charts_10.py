import json
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
import os

with open("capital_data_10.json", "r") as f:
    data = json.load(f)

dates = pd.to_datetime(data["dates"])
port_vals = data["lump_sum"]["portfolio"]
spx_vals = data["lump_sum"]["spx"]

port_vals_small = data["lump_sum_small"]["portfolio"]
spx_vals_small = data["lump_sum_small"]["spx"]

sns.set_theme(style="darkgrid")
artifact_dir = r"C:\Users\user\.gemini\antigravity\brain\94b3c258-68ae-4021-b830-56f62b4e8864"

# 1M Chart
plt.figure(figsize=(12, 6))
plt.plot(dates, port_vals, label='10-Ticker Portfolio', color='#2f81f7', linewidth=2)
plt.plot(dates, spx_vals, label='S&P 500 TR', color='#f78166', linestyle='--', linewidth=2)
plt.title('15-Year Capital Growth (1,000,000 Initial Investment)', fontsize=14, pad=15)
plt.xlabel('Year', fontsize=12)
plt.ylabel('Capital Value ($)', fontsize=12)
plt.gca().yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: format(int(x), ',')))
plt.legend(fontsize=12)
plt.tight_layout()
out_path1 = os.path.join(artifact_dir, "lump_sum_10_ticker.png")
plt.savefig(out_path1, dpi=150)
print(f"Saved lump sum chart to {out_path1}")

# 10k Chart
plt.figure(figsize=(12, 6))
plt.plot(dates, port_vals_small, label='10-Ticker Portfolio', color='#2f81f7', linewidth=2)
plt.plot(dates, spx_vals_small, label='S&P 500 TR', color='#f78166', linestyle='--', linewidth=2)
plt.title('15-Year Capital Growth (10,000 Initial Investment)', fontsize=14, pad=15)
plt.xlabel('Year', fontsize=12)
plt.ylabel('Capital Value ($)', fontsize=12)
plt.gca().yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: format(int(x), ',')))
plt.legend(fontsize=12)
plt.tight_layout()
out_path2 = os.path.join(artifact_dir, "lump_sum_small_10_ticker.png")
plt.savefig(out_path2, dpi=150)
print(f"Saved 10k lump sum chart to {out_path2}")

# Annual Returns
years = [d["year"] for d in data["annual"]]
port_ann = [d["portfolio"] for d in data["annual"]]
spx_ann = [d["spx"] for d in data["annual"]]

plt.figure(figsize=(12, 6))
bar_width = 0.35
index = range(len(years))
plt.bar(index, port_ann, bar_width, label='10-Ticker Portfolio', color='#2f81f7')
plt.bar([i + bar_width for i in index], spx_ann, bar_width, label='S&P 500 TR', color='#f78166')
plt.xlabel('Year', fontsize=12)
plt.ylabel('Annual Return (%)', fontsize=12)
plt.title('Independent Annual Return Comparison', fontsize=14, pad=15)
plt.xticks([i + bar_width / 2 for i in index], years)
plt.legend(fontsize=12)
plt.tight_layout()
out_path3 = os.path.join(artifact_dir, "annual_returns_10_ticker.png")
plt.savefig(out_path3, dpi=150)
print(f"Saved annual return chart to {out_path3}")
