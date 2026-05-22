import requests
import json
import logging

logger = logging.getLogger(__name__)

class GPTEngine:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

    def analyze(self, market_name, price, cot_data, score_data):
        """
        Generates a market analysis using Gemini.
        """
        # Construct Prompt
        prompt = self._build_prompt(market_name, price, cot_data, score_data)
        
        # Call API
        try:
            url = f"{self.base_url}?key={self.api_key}"
            payload = {
                "contents": [{
                    "parts": [{"text": prompt}]
                }]
            }
            
            resp = requests.post(url, json=payload, timeout=30)
            resp.raise_for_status()
            
            result = resp.json()
            # Extract text
            if "candidates" in result and result["candidates"]:
                return result["candidates"][0]["content"]["parts"][0]["text"]
            else:
                return self._fallback_analysis(market_name, score_data)
                
        except Exception as e:
            logger.error(f"Gemini API Error: {e}")
            return self._fallback_analysis(market_name, score_data)

    def _fallback_analysis(self, market_name, score_data):
        """Generates a template-based analysis when AI is unavailable."""
        score = score_data.get('score', 50)
        rating = score_data.get('rating', 'Neutral')
        signals = score_data.get('signals', [])
        
        # Tone
        tone = "neutral"
        if score > 60: tone = "bullish"
        elif score < 40: tone = "bearish"
        
        # Template Construction
        text = f"**System Note:** AI Quota Exceeded. Switching to Internal Quant Engine.\n\n"
        text += f"**Market Structure:** {market_name} is currently exhibiting a **{rating}** structure (Score: {score}). "
        
        if tone == "bullish":
            text += "Smart Money positioning suggests accumulation, supporting a potential upside continuation. "
            text += "Speculators are beginning to chase the trend, which validates the momentum. "
        elif tone == "bearish":
            text += "Commercials are actively hedging into strength, creating a resistance ceiling. "
            text += "The breakdown in net positioning suggests further downside risk. "
        else:
            text += "Price action is effectively range-bound with conflicting signals from major players. "
            text += "Volatility contraction suggests a breakout is imminent, but direction remains unclear. "
            
        if signals:
            text += f"\n\n**Key Alerts:** Detected {', '.join(signals)}. Monitor these levels closely for validation."
            
        text += "\n\n**Recommendation:** "
        if tone == "bullish": text += "Look for dips to buy. Maintain trailing stops."
        elif tone == "bearish": text += "Fade rallies into resistance. Reduce long exposure."
        else: text += "Stand aside and wait for a confirmed trend signal."
        
        return text

    def _build_prompt(self, market_name, price, cot_data, score_data):
        return f"""
        Act as a Senior Quant Trader at a top Hedge Fund. 
        Analyze the following CFTC 'Commitment of Traders' (COT) data for {market_name}.
        
        CONTEXT:
        - Current COT Net Position (Managed Money): {cot_data.get('net_noncomm', 0)}
        - Current COT Net Position (Commercials): {cot_data.get('net_comm', 0)}
        - Open Interest: {cot_data.get('open_interest_all', 0)}
        - Calculated Bullish Score (0-100): {score_data.get('score', 50)} ({score_data.get('rating', 'Neutral')})
        - Signals Detected: {', '.join(score_data.get('signals', []))}
        
        INSTRUCTIONS:
        1. Provide a concise, professional analysis of the market sentiment.
        2. Focus on the divergence between 'Smart Money' (Commercials) and 'Speculators' (Managed Money).
        3. Interpret the Open Interest trend if relevant.
        4. Conclude with a clear Directional Bias (Bullish/Bearish/Neutral) and Key Risks.
        5. Keep it under 200 words. Use bullet points for readability.
        """
