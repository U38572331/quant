
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score

INPUT_FILE = "features.csv"
OUTPUT_DIR = r"C:\Users\user\.gemini\antigravity\brain\a2f4e47b-f71a-4f3f-8b02-41be5d153b0f"

def main():
    print("Loading features...")
    df = pd.read_csv(INPUT_FILE)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date')
    
    # Features
    drop_cols = ['date', 'target_bias', 'rth_open', 'rth_close']
    feature_cols = [c for c in df.columns if c not in drop_cols]
    
    X = df[feature_cols]
    y = df['target_bias']
    
    # Train/Test Split (Time Series 80/20)
    split_idx = int(len(df) * 0.8)
    
    X_train = X.iloc[:split_idx]
    y_train = y.iloc[:split_idx]
    X_test = X.iloc[split_idx:]
    y_test = y.iloc[split_idx:]
    
    test_dates = df['date'].iloc[split_idx:]
    test_prices_open = df['rth_open'].iloc[split_idx:]
    test_prices_close = df['rth_close'].iloc[split_idx:]
    
    # Model
    print("Training Random Forest...")
    clf = RandomForestClassifier(n_estimators=200, max_depth=5, min_samples_leaf=10, random_state=42)
    clf.fit(X_train, y_train)
    
    # --- Visualization 1: Feature Importance ---
    importances = clf.feature_importances_
    indices = np.argsort(importances)[::-1]
    top_indices = indices[:10]
    
    plt.figure(figsize=(10, 6))
    plt.title("Top 10 Feature Importances")
    plt.barh(range(10), importances[top_indices][::-1], color='b', align='center')
    plt.yticks(range(10), [feature_cols[i] for i in top_indices][::-1])
    plt.xlabel('Relative Importance')
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/feature_importance.png")
    plt.close()
    print("Saved feature_importance.png")
    
    # --- Visualization 2: Confusion Matrix ---
    y_pred = clf.predict(X_test)
    cm = confusion_matrix(y_test, y_pred)
    
    plt.figure(figsize=(6, 5))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', cbar=False)
    plt.title('Confusion Matrix (Test Set)')
    plt.ylabel('Actual Label')
    plt.xlabel('Predicted Label')
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/confusion_matrix.png")
    plt.close()
    print("Saved confusion_matrix.png")
    
    # --- Visualization 3: Equity Curve (Backtest) ---
    print("Simulating Equity Curve...")
    # Strategy: 
    # If pred = 1 (Bullish), buy at Open, sell at Close.
    # If pred = 0 (Bearish/Neutral), sell at Open, buy at Close (Short).
    # Multiplier: 20 per point (NQ standard) -> but let's just use Points
    
    points = []
    
    # Use array operations
    signals = y_pred # 0 or 1
    # Actual daily movement: Close - Open
    daily_move = test_prices_close.values - test_prices_open.values
    
    # If signal 1: PnL = daily_move
    # If signal 0: PnL = -daily_move (Short)
    # Note: Target was 1 if Close > Open. Model predicts "Close > Open".
    # So if Prediction=0, Model thinks Close <= Open. Strategy: Go Short.
    
    # Vectorized PnL
    # Map 0 -> -1 for direction
    directions = np.where(signals == 1, 1, -1)
    pnl = directions * daily_move
    
    cumulative_pnl = np.cumsum(pnl)
    
    # Baseline: Buy and Hold (Always Multiplier = 1)
    cumulative_bh = np.cumsum(daily_move)
    
    plt.figure(figsize=(12, 6))
    plt.plot(test_dates, cumulative_pnl, label='Strategy (ML Predictor)', color='green')
    plt.plot(test_dates, cumulative_bh, label='Buy & Hold Baseline', color='gray', linestyle='--')
    plt.title(f'Cumulative Strategy Performance (Points) - {test_dates.iloc[0].date()} to {test_dates.iloc[-1].date()}')
    plt.xlabel('Date')
    plt.ylabel('Cumulative Points')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/equity_curve.png")
    plt.close()
    print("Saved equity_curve.png")

if __name__ == "__main__":
    main()
