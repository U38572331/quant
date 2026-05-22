import pandas as pd
df = pd.read_csv("backtest_trades.csv")
print("Types before:")
print(df.dtypes)
df['EntryTime'] = pd.to_datetime(df['EntryTime'])
df['ExitTime'] = pd.to_datetime(df['ExitTime'])
diff = df['ExitTime'] - df['EntryTime']
print("Diff type:")
print(type(diff))
print(diff.head())
print("Can use .dt?")
try:
    print(diff.dt.total_seconds().head())
    print("Yes!")
except Exception as e:
    print(f"No: {e}")
