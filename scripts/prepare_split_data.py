import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Load full trade details for split analysis
raw = pd.read_csv(r'C:\Users\user\.gemini\antigravity\scratch\nq_raw_compare.csv')
opt = pd.read_csv(r'C:\Users\user\.gemini\antigravity\scratch\nq_opt_compare.csv')

# Re-run a detailed comparison to keep 'type' info
# Wait, I need to make sure the CSVs have 'type'.
# Let me re-run run_comparison.py to include 'type'.
