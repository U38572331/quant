
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
import matplotlib.pyplot as plt

INPUT_FILE = "features.csv"

def main():
    print("Loading features...")
    df = pd.read_csv(INPUT_FILE)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date')
    
    print(f"Total samples: {len(df)}")
    print(f"Date range: {df['date'].min().date()} to {df['date'].max().date()}")
    
    # Class balance
    print("Class Balance (1=Bullish, 0=Bearish/Neutral):")
    print(df['target_bias'].value_counts(normalize=True))
    
    # Features
    drop_cols = ['date', 'target_bias']
    feature_cols = [c for c in df.columns if c not in drop_cols]
    
    X = df[feature_cols]
    y = df['target_bias']
    
    # Train/Test Split (Time Series)
    # Use 80% train, 20% test
    split_idx = int(len(df) * 0.8)
    
    X_train = X.iloc[:split_idx]
    y_train = y.iloc[:split_idx]
    X_test = X.iloc[split_idx:]
    y_test = y.iloc[split_idx:]
    
    test_dates = df['date'].iloc[split_idx:]
    
    print(f"Train size: {len(X_train)}, Test size: {len(X_test)}")
    print(f"Test starts from: {test_dates.iloc[0].date()}")
    
    # Model
    print("Training Random Forest...")
    clf = RandomForestClassifier(n_estimators=200, max_depth=5, min_samples_leaf=10, random_state=42)
    clf.fit(X_train, y_train)
    
    # Predict
    y_pred = clf.predict(X_test)
    y_prob = clf.predict_proba(X_test)[:, 1]
    
    # Evaluation
    acc = accuracy_score(y_test, y_pred)
    print(f"\nAccuracy: {acc:.4f}")
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred))
    
    print("Confusion Matrix:")
    print(confusion_matrix(y_test, y_pred))
    
    # Feature Importance
    importances = clf.feature_importances_
    indices = np.argsort(importances)[::-1]
    
    print("\nTop 10 Feature Importances:")
    for i in range(10):
        print(f"{feature_cols[indices[i]]}: {importances[indices[i]]:.4f}")
        
    # Save results explanation
    with open("results.txt", "w") as f:
        f.write(f"Accuracy: {acc:.4f}\n")
        f.write(f"Test Period: {test_dates.iloc[0].date()} to {test_dates.iloc[-1].date()}\n")
        for i in range(10):
            f.write(f"Feature {feature_cols[indices[i]]}: {importances[indices[i]]:.4f}\n")

if __name__ == "__main__":
    main()
