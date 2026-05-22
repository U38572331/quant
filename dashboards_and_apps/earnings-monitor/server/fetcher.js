import YahooFinance from 'yahoo-finance2';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const yf = new YahooFinance({ suppressNotices: ['yahooSurvey'] });

const TICKERS = Array.from(new Set([
  'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'TSLA', 'NVDA', 'NFLX', 'AMD', 'INTC',
  'PYPL', 'ADBE', 'CSCO', 'PEP', 'AVGO', 'COST', 'TMUS', 'TXN', 'CMCSA', 'QCOM',
  'ABNB', 'ORCL', 'CRM', 'INTU', 'AMAT', 'MU', 'LRCX', 'ADI', 'PANW', 'SNPS',
  'CDNS', 'ASML', 'KLAC', 'MAR', 'BKNG', 'MELI', 'PDD', 'JD', 'BABA', 'TME',
  'V', 'MA', 'JPM', 'BAC', 'WFC', 'C', 'GS', 'MS', 'BLK', 'AXP',
  'UNH', 'LLY', 'JNJ', 'ABBV', 'MRK', 'PFE', 'TMO', 'DHR', 'ABT', 'BMY',
  'PG', 'KO', 'WMT', 'MDLZ', 'TGT', 'EL', 'PM', 'MO', 'CL',
  'XOM', 'CVX', 'SHEL', 'TTE', 'COP', 'BP', 'SLB', 'EOG', 'MPC', 'VLO',
  'AMT', 'PLD', 'CCI', 'EQIX', 'DLR', 'PSA', 'VICI', 'O', 'WELL', 'SPG',
  'NEE', 'DUK', 'SO', 'D', 'AEP', 'EXC', 'SRE', 'XEL', 'ED', 'WEC',
  'LIN', 'APD', 'SHW', 'ECL', 'NEM', 'FCX', 'DD', 'DOW', 'CTVA', 'ALB',
  'UPS', 'HON', 'CAT', 'GE', 'DE', 'LMT', 'RTX', 'UNP', 'BA', 'MMM',
  'DIS', 'CMG', 'SBUX', 'NKE', 'LOW', 'HD', 'TJX', 'ORLY', 'AZO',
  'ZTS', 'IDXX', 'SYK', 'ISRG', 'BSX', 'REGN', 'VRTX', 'GILD', 'CI', 'HCA',
  'MCD', 'YUM', 'DRI', 'DASH', 'UBER', 'LYFT', 'EXPE', 'TRIP',
  'SNOW', 'PLTR', 'TEAM', 'WDAY', 'NOW', 'CRWD', 'DDOG', 'ZS', 'OKTA', 'MDB',
  'AFRM', 'SQ', 'COIN', 'HOOD', 'SHOP', 'SE', 'STNE', 'NU', 'PAGS',
  'NET', 'FSLY', 'AKAM', 'U', 'RBLX', 'TTD', 'MGNI', 'PUBM', 'PERI',
  'ZM', 'DOCU', 'FIVN', 'RING', 'EGHT', 'BAND', 'TWLO', 'CFLT', 'PATH',
  'AI', 'C3AI', 'UPST', 'SOFI', 'OPEN', 'DKNG', 'PENN', 'WYNN', 'LVS'
]));

async function fetchStockEarnings(ticker) {
  try {
    // We combine multiple modules to get the most accurate picture
    const result = await yf.quoteSummary(ticker, {
      modules: ['earnings', 'price', 'earningsTrend', 'earningsHistory']
    });

    const earnings = result.earnings;
    const price = result.price;
    const trend = result.earningsTrend;
    const historyModule = result.earningsHistory;

    if (!earnings || !earnings.earningsChart) return null;

    const quarterlyEps = earnings.earningsChart.quarterly;
    const quarterlyFin = earnings.financialsChart.quarterly;

    if (quarterlyEps.length === 0) return null;

    // Get the most recent quarter
    const latestEps = quarterlyEps[quarterlyEps.length - 1];
    const latestFin = quarterlyFin[quarterlyFin.length - 1];

    // Surprise calculation from earningsHistory (if available) or manual
    let epsSurprise = 0;
    if (historyModule && historyModule.history && historyModule.history.length > 0) {
      const h = historyModule.history[historyModule.history.length - 1];
      epsSurprise = h.surprisePercent ? h.surprisePercent * 100 : ((h.epsActual - h.epsEstimate) / Math.abs(h.epsEstimate) * 100);
    } else {
      epsSurprise = ((latestEps.actual - latestEps.estimate) / Math.abs(latestEps.estimate) * 100);
    }

    // Revenue Surprise from earningsTrend
    let revEstimate = null;
    let revSurprise = null;
    if (trend && trend.trend) {
      const currentTrend = trend.trend.find(t => t.period === '0q');
      if (currentTrend && currentTrend.revenueEstimate) {
        revEstimate = currentTrend.revenueEstimate.avg;
        if (revEstimate && latestFin.revenue) {
          revSurprise = ((latestFin.revenue - revEstimate) / Math.abs(revEstimate) * 100);
        }
      }
    }

    if (Math.abs(epsSurprise) > 1000) epsSurprise = epsSurprise > 0 ? 999 : -999;
    
    return {
      ticker: ticker,
      name: price.shortName || price.longName,
      reportDate: latestEps.date,
      period: latestEps.date,
      epsActual: latestEps.actual,
      epsEstimate: latestEps.estimate,
      epsSurprise: epsSurprise.toFixed(2),
      revActual: (latestFin.revenue / 1e9).toFixed(2),
      revEstimate: revEstimate ? (revEstimate / 1e9).toFixed(2) : null,
      revSurprise: revSurprise ? revSurprise.toFixed(2) : null,
      priceChange: (price.regularMarketChangePercent * 100).toFixed(2),
      history: quarterlyEps.map(q => ({
        quarter: q.date,
        actual: q.actual,
        estimate: q.estimate
      }))
    };
  } catch (error) {
    return null;
  }
}

async function main() {
  const uniqueTickers = TICKERS;
  console.log(`Starting improved Yahoo Finance data fetch for ${uniqueTickers.length} unique stocks...`);
  const results = [];
  
  const BATCH_SIZE = 10;
  for (let i = 0; i < uniqueTickers.length; i += BATCH_SIZE) {
    const batch = uniqueTickers.slice(i, i + BATCH_SIZE);
    process.stdout.write(`Fetching ${i + batch.length}/${uniqueTickers.length}...\r`);
    const batchResults = await Promise.all(batch.map(fetchStockEarnings));
    results.push(...batchResults.filter(r => r !== null));
    
    if (i + BATCH_SIZE < uniqueTickers.length) {
      await new Promise(resolve => setTimeout(resolve, 500));
    }
  }

  console.log('\nSorting results...');
  results.sort((a, b) => b.epsSurprise - a.epsSurprise);

  const outputPath = path.join(__dirname, '../src/data/yahooData.json');
  fs.writeFileSync(outputPath, JSON.stringify(results, null, 2));
  console.log(`Successfully fetched ${results.length} stocks. Saved to src/data/yahooData.json`);
}

main().catch(console.error);
