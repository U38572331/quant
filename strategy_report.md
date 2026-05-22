# 15m ORB ML Quantitative Strategy Report
    
## Strategy Overview
A Machine Learning enhanced Opening Range Breakout (ORB) strategy for NQ Futures.
The strategy uses an XGBoost model to filter breakouts based on volatility (ATR), Volume, and Gap characteristics.

## Optimization Results (Best Configuration)
Based on Grid Search over the test period:

- **Sharpe Ratio**: 1.79
- **Total PnL (Test Period)**: 889.13 Points (approx)
- **Trade Count**: 141

### Optimal Parameters
| Parameter | Value | Description |
|---|---|---|
| **ML Probability Threshold** | **0.30** | Minimum confidence score to take a trade. |
| **Take Profit** | **1.0 x ATR** | Dynamic target based on volatility. |
| **Stop Loss** | **1.5 x ATR** | Dynamic risk management. |


### Key Predictive Features (Machine Learning)
| Feature | Importance |
|---|---|
| VWAP_Dev | 0.1396 |
| RVol | 0.1205 |
| Norm_Upper_Wick | 0.1072 |
| Norm_Gap | 0.1050 |
| Prev_Vol_SMA | 0.1018 |


## Recommended Algorithm Logic
1. **Wait** for the first 15 minutes of the RTH session (9:30 - 9:45 ET).
2. **Calculate** ORB High and Low.
3. **Compute** features: 14-Day ATR, Relative Volume (RVol), Generalized Gap.
4. **Predict** success probability using the trained XGBoost model.
5. **Execution**:
    - IF `Price > ORB High` AND `Long_Prob > 0.30`:
        - **BUY** NQ.
        - **STOP**: Entry - (1.5 * ATR)
        - **TARGET**: Entry + (1.0 * ATR)
    - IF `Price < ORB Low` AND `Short_Prob > 0.30`:
        - **SELL** NQ.
        - **STOP**: Entry + (1.5 * ATR)
        - **TARGET**: Entry - (1.0 * ATR)

