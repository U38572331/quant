
import pandas as pd
import os

def generate_report():
    print("Generating Strategy Report...")
    
    # Load Optimization Results
    try:
        results = pd.read_csv("src/optimization_results.csv", index_col=0)
        best_res = results.iloc[0] # Assumes sorted by Sharpe descending
    except FileNotFoundError:
        print("Optimization results not found.")
        return

    # Load Feature Importance
    # (Assuming we saved it, if not we skip)
    features_md = ""
    if os.path.exists("src/feature_importance.csv"):
        feats = pd.read_csv("src/feature_importance.csv", names=['Feature', 'Importance'])
        feats = feats.sort_values('Importance', ascending=False)
        top_features = feats.head(5)
        
        features_md = "\n### Key Predictive Features (Machine Learning)\n"
        features_md += "| Feature | Importance |\n|---|---|\n"
        for _, row in top_features.iterrows():
            features_md += f"| {row['Feature']} | {row['Importance']:.4f} |\n"

    # Create Markdown Content
    report_content = f"""# 15m ORB ML Quantitative Strategy Report
    
## Strategy Overview
A Machine Learning enhanced Opening Range Breakout (ORB) strategy for NQ Futures.
The strategy uses an XGBoost model to filter breakouts based on volatility (ATR), Volume, and Gap characteristics.

## Optimization Results (Best Configuration)
Based on Grid Search over the test period:

- **Sharpe Ratio**: {best_res['Sharpe']:.2f}
- **Total PnL (Test Period)**: {best_res['Total_PnL']:.2f} Points (approx)
- **Trade Count**: {int(best_res['Trades'])}

### Optimal Parameters
| Parameter | Value | Description |
|---|---|---|
| **ML Probability Threshold** | **{best_res['Prob']:.2f}** | Minimum confidence score to take a trade. |
| **Take Profit** | **{best_res['TP']} x ATR** | Dynamic target based on volatility. |
| **Stop Loss** | **{best_res['SL']} x ATR** | Dynamic risk management. |

{features_md}

## Recommended Algorithm Logic
1. **Wait** for the first 15 minutes of the RTH session (9:30 - 9:45 ET).
2. **Calculate** ORB High and Low.
3. **Compute** features: 14-Day ATR, Relative Volume (RVol), Generalized Gap.
4. **Predict** success probability using the trained XGBoost model.
5. **Execution**:
    - IF `Price > ORB High` AND `Long_Prob > {best_res['Prob']:.2f}`:
        - **BUY** NQ.
        - **STOP**: Entry - ({best_res['SL']} * ATR)
        - **TARGET**: Entry + ({best_res['TP']} * ATR)
    - IF `Price < ORB Low` AND `Short_Prob > {best_res['Prob']:.2f}`:
        - **SELL** NQ.
        - **STOP**: Entry + ({best_res['SL']} * ATR)
        - **TARGET**: Entry - ({best_res['TP']} * ATR)

"""
    
    with open("strategy_report.md", "w") as f:
        f.write(report_content)
    
    print("Report generated: strategy_report.md")

if __name__ == "__main__":
    generate_report()
