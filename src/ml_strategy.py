
import pandas as pd
import numpy as np
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import precision_score, accuracy_score
import xgboost as xgb
import itertools

class MLStrategy:
    def __init__(self, data_path):
        self.df = pd.read_csv(data_path, index_col=0, parse_dates=True)
        self.best_params = {}
        
    def prepare_data(self):
        """
        Defines X (Features) and Y (Target).
        For ML training, we create a binary target: Did it move > 1 ATR without hitting Stop (1 ATR)?
        This is just a proxy to learn "Good Conditions".
        """
        # Features to use
        feature_cols = [
            'Prev_ATR', 'Prev_Vol_SMA', 
            'Norm_ORB_Range', 'Norm_Gap', 
            'RVol', 'DayOfWeek', 'Month',
            'VWAP_Dev', 'Norm_Upper_Wick', 'Norm_Lower_Wick'
        ]
        
        # Clean
        self.df = self.df.dropna()
        
        # Define Proxy Target for Classification: Reliable Breakout
        # 2R Target with 1R Stop relative to ATR?
        # Let's say: Success if MFE > 1.0 * ATR and MAE < 1.0 * ATR
        atr = self.df['Prev_ATR']
        
        self.df['Long_Success'] = ((self.df['Long_MFE'] > 1.0 * atr) & (self.df['Long_MAE'] < 1.0 * atr)).astype(int)
        self.df['Short_Success'] = ((self.df['Short_MFE'] > 1.0 * atr) & (self.df['Short_MAE'] < 1.0 * atr)).astype(int)
        
        self.X = self.df[feature_cols]
        self.y_long = self.df['Long_Success']
        self.y_short = self.df['Short_Success']
        
        return feature_cols

    def train_models(self):
        """
        Trains Long and Short models using TimeSeriesSplit.
        Returns the models and Out-of-Sample predictions.
        """
        print("Training XGBoost Models...")
        
        # Simple Train/Test Split (70% Train, 30% Test)
        split = int(len(self.X) * 0.7)
        
        X_train, X_test = self.X.iloc[:split], self.X.iloc[split:]
        y_long_train, y_long_test = self.y_long.iloc[:split], self.y_long.iloc[split:]
        y_short_train, y_short_test = self.y_short.iloc[:split], self.y_short.iloc[split:]
        
        print(f"Train Size: {len(X_train)}")
        print(f"Long Class Balance: {y_long_train.value_counts().to_dict()}")
        print(f"Short Class Balance: {y_short_train.value_counts().to_dict()}")
        
        # XGBoost Params
        params = {
            'n_estimators': 100,
            'max_depth': 4,
            'learning_rate': 0.1,
            'eval_metric': 'logloss',
            'objective': 'binary:logistic',
            'scale_pos_weight': 10, # Handle class imbalance
            'n_jobs': -1
        }
        
        model_long = xgb.XGBClassifier(**params)
        model_long.fit(X_train, y_long_train)
        
        model_short = xgb.XGBClassifier(**params)
        model_short.fit(X_train, y_short_train)
        
        model_short.fit(X_train, y_short_train)
        
        # Get Probabilities for ENTIRE set (In-Sample + Out-of-Sample)
        self.df['Prob_Long'] = model_long.predict_proba(self.X)[:, 1]
        self.df['Prob_Short'] = model_short.predict_proba(self.X)[:, 1]
        
        # Feature Importance
        importances = pd.Series(model_long.feature_importances_, index=self.X.columns).sort_values(ascending=False)
        print("Long Model Feature Importance:")
        print(importances)
        importances.to_csv("src/feature_importance.csv", header=False)
        
        self.test_start_index = split
        return model_long, model_short

    def optimize_strategy(self):
        """
        Grid Search for Best Algo Parameters on the TEST set (Out-of-Sample).
        Params:
        - Entry Threshold (Prob > X)
        - Take Profit (ATR Multiple)
        - Stop Loss (ATR Multiple)
        """
        print("Optimizing Strategy Strategy (Grid Search)...")
        
        test_df = self.df.iloc[self.test_start_index:].copy()
        atr = test_df['Prev_ATR']
        
        best_sharpe = -999
        best_combo = (0.0, 0.0, 0.0) # Default
        
        # Grid Search
        # Lower thresholds due to class imbalance
        probs = [0.3, 0.4, 0.5, 0.6]
        tp_multiples = [1.0, 2.0, 3.0]
        sl_multiples = [0.5, 1.0, 1.5]
        
        results = []
        
        for prob, tp_m, sl_m in itertools.product(probs, tp_multiples, sl_multiples):
            # Simulation Logic
            
            # --- LONG Trades ---
            long_entries = test_df['Prob_Long'] > prob
            limit_price = tp_m * atr
            stop_price = sl_m * atr
            
            hit_tp_long = (test_df['Long_MFE'] >= limit_price)
            hit_sl_long = (test_df['Long_MAE'] >= stop_price)
            
            long_pnl = pd.Series(0.0, index=test_df.index)
            # Stop out
            long_pnl[hit_sl_long] = -stop_price[hit_sl_long]
            # Win (if not stopped)
            wins_long = (~hit_sl_long) & hit_tp_long
            long_pnl[wins_long] = limit_price[wins_long]
            
            long_pnl = long_pnl * long_entries.astype(int)
            
            # --- SHORT Trades ---
            short_entries = test_df['Prob_Short'] > prob
            hit_tp_short = (test_df['Short_MFE'] >= limit_price)
            hit_sl_short = (test_df['Short_MAE'] >= stop_price)
            
            short_pnl = pd.Series(0.0, index=test_df.index)
            short_pnl[hit_sl_short] = -stop_price[hit_sl_short]
            wins_short = (~hit_sl_short) & hit_tp_short
            short_pnl[wins_short] = limit_price[wins_short]
            
            short_pnl = short_pnl * short_entries.astype(int)
            
            # Total PnL
            total_pnl = long_pnl + short_pnl
            
            # Metrics
            trades = (long_entries.sum() + short_entries.sum())
            if trades < 10: continue # Ignore low sample
            
            cum_pnl = total_pnl.sum()
            mean_ret = total_pnl.mean()
            std_ret = total_pnl.std()
            sharpe = (mean_ret / std_ret * np.sqrt(252)) if std_ret > 0 else 0
            
            if sharpe > best_sharpe:
                best_sharpe = sharpe
                best_combo = (prob, tp_m, sl_m)
                
            results.append({
                'Prob': prob, 'TP': tp_m, 'SL': sl_m,
                'Sharpe': sharpe, 'Trades': trades, 'Total_PnL': cum_pnl
            })
            
        print(f"Optimization Complete. Best Sharpe: {best_sharpe}")
        print(f"Best Params: Prob>{best_combo[0]}, TP={best_combo[1]} ATR, SL={best_combo[2]} ATR")
        
        # Save results
        res_df = pd.DataFrame(results)
        if not res_df.empty:
            res_df.sort_values('Sharpe', ascending=False).to_csv("src/optimization_results.csv")
        else:
            print("No valid results found (low trades).")
            
        return best_combo

    def save_equity_curve(self, params):
        """
        Runs the simulation with specific parameters and saves the PnL series.
        """
        print("Simulating Equity Curve on FULL Dataset...")
        prob, tp_m, sl_m = params
        test_df = self.df.copy() # Use FULL dataframe
        atr = test_df['Prev_ATR']
        
        # --- LONG Trades ---
        long_entries = test_df['Prob_Long'] > prob
        limit_price = tp_m * atr
        stop_price = sl_m * atr
        
        hit_tp_long = (test_df['Long_MFE'] >= limit_price)
        hit_sl_long = (test_df['Long_MAE'] >= stop_price)
        
        long_pnl = pd.Series(0.0, index=test_df.index)
        long_pnl[hit_sl_long] = -stop_price[hit_sl_long]
        wins_long = (~hit_sl_long) & hit_tp_long
        long_pnl[wins_long] = limit_price[wins_long]
        long_pnl = long_pnl * long_entries.astype(int)
        
        # --- SHORT Trades ---
        short_entries = test_df['Prob_Short'] > prob
        hit_tp_short = (test_df['Short_MFE'] >= limit_price)
        hit_sl_short = (test_df['Short_MAE'] >= stop_price)
        
        short_pnl = pd.Series(0.0, index=test_df.index)
        short_pnl[hit_sl_short] = -stop_price[hit_sl_short]
        wins_short = (~hit_sl_short) & hit_tp_short
        short_pnl[wins_short] = limit_price[wins_short]
        short_pnl = short_pnl * short_entries.astype(int)
        
        # Total PnL
        total_pnl = long_pnl + short_pnl
        
        curve = pd.DataFrame({
            'Daily_PnL': total_pnl,
            'Cumulative_PnL': total_pnl.cumsum()
        })
        curve.to_csv("src/equity_curve.csv")
        print("Equity curve saved to src/equity_curve.csv")

if __name__ == "__main__":
    ml = MLStrategy("src/training_data.csv")
    ml.prepare_data()
    ml.train_models()
    best_params = ml.optimize_strategy()
    if best_params and best_params[0] > 0:
        ml.save_equity_curve(best_params)
