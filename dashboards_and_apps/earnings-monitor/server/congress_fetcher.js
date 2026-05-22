import YahooFinance from 'yahoo-finance2';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const yf = new YahooFinance({ suppressNotices: ['yahooSurvey'] });

// Mock Congressional Trades (Real data would come from STOCK Act filings)
const CONGRESS_TRADES = [
  { politician: 'Nancy Pelosi', ticker: 'NVDA', date: '2023-11-22', type: 'Purchase', amount: '$1,000,001 - $5,000,000' },
  { politician: 'Josh Gottheimer', ticker: 'MSFT', date: '2024-02-15', type: 'Purchase', amount: '$100,001 - $250,000' },
  { politician: 'Mark Green', ticker: 'NGL', date: '2024-01-10', type: 'Purchase', amount: '$250,001 - $500,000' },
  { politician: 'Thomas Tuberville', ticker: 'XOM', date: '2024-03-05', type: 'Purchase', amount: '$50,001 - $100,000' },
  { politician: 'Nancy Pelosi', ticker: 'AAPL', date: '2024-01-15', type: 'Purchase', amount: '$1,000,001 - $5,000,000' },
  { politician: 'Josh Gottheimer', ticker: 'TSLA', date: '2024-03-20', type: 'Sale', amount: '$15,001 - $50,000' }
];

async function fetchHistoricalData(ticker, startDate) {
  try {
    const end = new Date();
    const start = new Date(startDate);
    start.setMonth(start.getMonth() - 2); // Get 2 months before for context
    
    const result = await yf.historical(ticker, {
      period1: start,
      period2: end,
      interval: '1d'
    });

    return result.map(d => ({
      time: d.date.toISOString().split('T')[0],
      open: d.open,
      high: d.high,
      low: d.low,
      close: d.close,
      volume: d.volume
    }));
  } catch (error) {
    console.error(`Error fetching history for ${ticker}:`, error.message);
    return [];
  }
}

async function main() {
  console.log('Fetching Congressional Trades and K-Line data...');
  const results = [];

  for (const trade of CONGRESS_TRADES) {
    console.log(`Processing ${trade.politician} - ${trade.ticker}...`);
    const history = await fetchHistoricalData(trade.ticker, trade.date);
    results.push({
      ...trade,
      klineData: history
    });
    // Small delay to be polite
    await new Promise(resolve => setTimeout(resolve, 500));
  }

  const outputPath = path.join(__dirname, '../src/data/congressData.json');
  fs.writeFileSync(outputPath, JSON.stringify(results, null, 2));
  console.log(`Successfully saved ${results.length} congressional trades with K-Line data.`);
}

main().catch(console.error);
