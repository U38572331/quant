export const getEarningsData = async () => {
  try {
    const response = await fetch('/api/earnings');
    if (!response.ok) throw new Error('API failed');
    return await response.json();
  } catch (error) {
    console.warn('Live API unavailable, falling back to cached data');
    // Fallback to the JSON file if the server is not running
    const response = await fetch('/src/data/yahooData.json');
    return await response.json();
  }
};
