import yahooFinance from 'yahoo-finance2';
async function test() {
  const result = await yahooFinance.historical('AAPL', {
    period1: '2026-01-01',
    period2: '2026-05-11',
    interval: '1d'
  });
  console.log('Result:', result.length);
}
test();
