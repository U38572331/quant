import pandas as pd
df = pd.read_csv('nq_orb_results.csv')
print(df['Risk'].describe())
