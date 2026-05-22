import express from 'express';
import cors from 'cors';
import yahooFinance from 'yahoo-finance2';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
const PORT = 3001;

app.use(cors());
app.use(express.json());

// Serve static files from the build folder
const distPath = path.join(__dirname, '../dist');
app.use(express.static(distPath));

const yf = new yahooFinance.YahooFinance();

const SCRAPED_TRADES = [
  { politician: "Greg Stanton", ticker: "TCNNF", date: "2026-05-06", disclosureDate: "2026-05-10", amount: "15K-50K", type: "Sale" },
  { politician: "April McClain Delaney", ticker: "CLH", date: "2026-04-30", disclosureDate: "2026-05-08", amount: "1K-15K", type: "Sale" },
  { politician: "April McClain Delaney", ticker: "MKL", date: "2026-04-30", disclosureDate: "2026-05-08", amount: "1K-15K", type: "Purchase" },
  { politician: "April McClain Delaney", ticker: "MORN", date: "2026-04-30", disclosureDate: "2026-05-08", amount: "1K-15K", type: "Sale" },
  { politician: "April McClain Delaney", ticker: "PKG", date: "2026-04-29", disclosureDate: "2026-05-08", amount: "1K-15K", type: "Purchase" },
  { politician: "David Taylor", ticker: "AVGO", date: "2026-04-27", disclosureDate: "2026-05-05", amount: "1K-15K", type: "Sale" },
  { politician: "David Taylor", ticker: "HD", date: "2026-04-27", disclosureDate: "2026-05-05", amount: "1K-15K", type: "Purchase" },
  { politician: "David Taylor", ticker: "PG", date: "2026-04-27", disclosureDate: "2026-05-05", amount: "1K-15K", type: "Purchase" },
  { politician: "David Taylor", ticker: "V", date: "2026-04-27", disclosureDate: "2026-05-05", amount: "1K-15K", type: "Purchase" },
  { politician: "April McClain Delaney", ticker: "CHRW", date: "2026-04-24", disclosureDate: "2026-05-03", amount: "15K-50K", type: "Sale" },
  { politician: "April McClain Delaney", ticker: "NDAQ", date: "2026-04-24", disclosureDate: "2026-05-03", amount: "1K-15K", type: "Purchase" },
  { politician: "Shelley Moore Capito", ticker: "AAPL", date: "2026-04-17", disclosureDate: "2026-04-28", amount: "1K-15K", type: "Sale" },
  { politician: "Shelley Moore Capito", ticker: "CEG", date: "2026-04-17", disclosureDate: "2026-04-28", amount: "1K-15K", type: "Sale" },
  { politician: "April McClain Delaney", ticker: "ENTG", date: "2026-04-15", disclosureDate: "2026-04-28", amount: "1K-15K", type: "Purchase" },
  { politician: "Shelley Moore Capito", ticker: "AVGO", date: "2026-04-13", disclosureDate: "2026-04-25", amount: "1K-15K", type: "Sale" },
  { politician: "John Boozman", ticker: "DVN", date: "2026-04-09", disclosureDate: "2026-04-22", amount: "1K-15K", type: "Purchase" },
  { politician: "April McClain Delaney", ticker: "TECH", date: "2026-04-08", disclosureDate: "2026-04-22", amount: "1K-15K", type: "Sale" },
  { politician: "John Boozman", ticker: "CEG", date: "2026-04-02", disclosureDate: "2026-04-15", amount: "1K-15K", type: "Purchase" },
  { politician: "Lloyd Doggett", ticker: "KO", date: "2026-04-01", disclosureDate: "2026-04-12", amount: "1K-15K", type: "Purchase" }
];

async function fetchKLines(ticker, tradeDate) {
  try {
    const end = new Date();
    const start = new Date(tradeDate);
    start.setMonth(start.getMonth() - 5);
    const result = await yf.historical(ticker, { period1: start, period2: end, interval: '1d' });
    if (!result || result.length === 0) return [];
    return result.map(d => ({ time: d.date.toISOString().split('T')[0], open: d.open, high: d.high, low: d.low, close: d.close }));
  } catch (e) { return []; }
}

async function fetchStockEarnings(ticker) {
  try {
    const result = await yf.quoteSummary(ticker, { modules: ['earnings', 'price', 'earningsTrend'] }, { validateResult: false });
    if (!result.earnings || !result.earnings.earningsChart) return null;
    const price = result.price;
    const quarterlyEps = result.earnings.earningsChart.quarterly;
    const latestEps = quarterlyEps[quarterlyEps.length - 1];
    return {
      ticker: ticker,
      name: price.shortName,
      reportDate: latestEps.date,
      epsActual: latestEps.actual,
      epsEstimate: latestEps.estimate,
      epsSurprise: (((latestEps.actual - latestEps.estimate) / Math.abs(latestEps.estimate)) * 100).toFixed(2),
      priceChange: (price.regularMarketChangePercent * 100).toFixed(2)
    };
  } catch (e) { return null; }
}

let congressCache = SCRAPED_TRADES.map(t => ({ ...t, klineData: [] }));

app.get('/api/congress', (req, res) => {
  res.json(congressCache);
});

app.get('/api/earnings', async (req, res) => {
  const tickers = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'TSLA', 'NVDA', 'NFLX', 'AMD', 'INTC'];
  const results = await Promise.all(tickers.map(fetchStockEarnings));
  res.json(results.filter(r => r !== null));
});

// Fallback for SPA
app.get('*', (req, res) => {
  res.sendFile(path.join(distPath, 'index.html'));
});

async function prefetchKLines() {
    const updated = [];
    for (const t of SCRAPED_TRADES) {
        const klineData = await fetchKLines(t.ticker, t.date);
        updated.push({ ...t, klineData });
    }
    congressCache = updated;
}

app.listen(PORT, () => {
  console.log(`Standalone Server running on http://localhost:${PORT}`);
  console.log(`Open your browser and navigate to http://localhost:${PORT}`);
  prefetchKLines().catch(console.error);
});
