
try:
    print("Importing pandas...")
    import pandas as pd
    print("Importing plotly...")
    import plotly.express as px
    import plotly.graph_objects as go
    print("Importing src.client...")
    from src.client import DeribitClient
    print("Importing src.calculator...")
    from src.calculator import AdvancedCalculator
    print("Importing src.utils...")
    from src.utils import enrich_data
    print("Importing src.analytics...")
    from src.analytics import MarketAnalyzer
    print("All imports successful!")
except Exception as e:
    print(f"Import failed: {e}")
    import traceback
    traceback.print_exc()
