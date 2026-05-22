import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
import matplotlib.pyplot as plt
import os

OUTPUT_DIR = r"C:\Users\user\.gemini\antigravity\scratch\results"
CSV_PATH = f"{OUTPUT_DIR}/opt_trades.csv"

def optimize_and_ml():
    try:
        trades_df = pd.read_csv(CSV_PATH)
    except:
        print("No CSV")
        return
        
    print("\n--- Strategy Optimization ---")
    
    # 1. Identify Best Raw Parameters (SL/TP) on Training Data
    dates = trades_df['Date'].unique()
    # Sort dates to ensure time-series split
    dates.sort()
    train_dates, test_dates = train_test_split(dates, test_size=0.3, shuffle=False)
    
    train_df = trades_df[trades_df['Date'].isin(train_dates)]
    test_df = trades_df[trades_df['Date'].isin(test_dates)]
    
    # Group by (SL_Type, TP_R)
    stats = train_df.groupby(['SL_Type', 'TP_R'])['PnL'].sum().reset_index()
    best_config = stats.loc[stats['PnL'].idxmax()]
    
    print(f"Best Raw Configuration (Train Set): SL={best_config['SL_Type']}, TP={best_config['TP_R']}R")
    
    # 2. Apply ML to Best Configuration
    subset_train = train_df[(train_df['SL_Type'] == best_config['SL_Type']) & (train_df['TP_R'] == best_config['TP_R'])].copy()
    subset_test = test_df[(test_df['SL_Type'] == best_config['SL_Type']) & (test_df['TP_R'] == best_config['TP_R'])].copy()
    
    # Target
    subset_train['Target'] = (subset_train['PnL'] > 0).astype(int)
    subset_test['Target'] = (subset_test['PnL'] > 0).astype(int)
    
    features = ['ORBHeight', 'ATR', 'GridVolume'] 
    subset_train = subset_train.dropna(subset=features)
    subset_test = subset_test.dropna(subset=features)
    
    rf = RandomForestClassifier(n_estimators=100, max_depth=4, random_state=42, class_weight='balanced')
    rf.fit(subset_train[features], subset_train['Target'])
    
    # Evaluate
    test_preds = rf.predict(subset_test[features])
    
    print("\nML Performance on Test Set (Best Config):")
    print(classification_report(subset_test['Target'], test_preds))
    
    # Check Precision for Class 1 (Win)
    from sklearn.metrics import precision_score
    prec = precision_score(subset_test['Target'], test_preds)
    print(f"Precision for WIN: {prec:.4f}")

    # Feature Importance
    imps = rf.feature_importances_
    print("\nFeature Importance:")
    for f, i in zip(features, imps):
        print(f"{f}: {i:.4f}")

if __name__ == "__main__":
    optimize_and_ml()
