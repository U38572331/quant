import pandas as pd
import numpy as np
import json
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Load optimized trades
df = pd.read_csv(r'C:\Users\user\.gemini\antigravity\scratch\nq_optimized_trades.csv' if False else r'C:\Users\user\.gemini\antigravity\scratch\nq_master_trades.csv') # Re-run to save proper csv
# Wait, I didn't save nq_optimized_trades.csv in the last script. I should do that.
