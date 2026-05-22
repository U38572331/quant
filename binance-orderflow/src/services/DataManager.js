// src/services/DataManager.js
import _ from 'lodash';

export class DataManager {
    constructor(symbol = 'btcusdt', onUpdate, onLargeOrder) {
        this.symbol = symbol.toLowerCase();
        this.ws = null;
        this.candles = {};
        this.activeCandleTime = 0;
        this.onUpdate = onUpdate;
        this.onLargeOrder = onLargeOrder;
        this.largeOrderThreshold = 5;
        this.orderBook = { bids: [], asks: [] };
        this.sessionProfile = {};

        this.emitUpdate = _.throttle(() => {
            if (this.onUpdate) {
                this.onUpdate({
                    candles: this.getSortedCandles(),
                    orderBook: this.orderBook,
                    sessionProfile: this.sessionProfile
                });
            }
        }, 100);
    }

    async fetchHistory() {
        try {
            console.log('Fetching historical data...');
            const klineRes = await fetch(`https://fapi.binance.com/fapi/v1/klines?symbol=${this.symbol.toUpperCase()}&interval=1m&limit=60`);
            const klines = await klineRes.json();

            let latestTime = 0;
            klines.forEach(k => {
                const [time, open, high, low, close, volume] = k;
                const t = parseInt(time);
                latestTime = Math.max(latestTime, t);
                this.candles[t] = {
                    time: t,
                    open: parseFloat(open),
                    high: parseFloat(high),
                    low: parseFloat(low),
                    close: parseFloat(close),
                    volume: parseFloat(volume),
                    delta: 0,
                    poc: parseFloat(close),
                    maxLevelVolume: 0,
                    levels: {}
                };
            });
            this.activeCandleTime = latestTime;

            const tradeRes = await fetch(`https://fapi.binance.com/fapi/v1/aggTrades?symbol=${this.symbol.toUpperCase()}&limit=1000`);
            const trades = await tradeRes.json();
            trades.forEach(t => this.processTrade(t, true));

            console.log(`History sync complete: ${klines.length} candles loaded.`);
            this.emitUpdate();
        } catch (err) {
            console.error('Failed to fetch history:', err);
        }
    }

    async connect() {
        await this.fetchHistory();

        // Connect to Binance Futures AggTrade and Depth Streams
        const streams = `${this.symbol}@aggTrade/${this.symbol}@depth20@100ms`;
        this.ws = new WebSocket(`wss://fstream.binance.com/stream?streams=${streams}`);

        this.ws.onopen = () => {
            console.log('Connected to Binance Futures Stream');
        };

        this.ws.onmessage = (event) => {
            const msg = JSON.parse(event.data);
            if (msg.stream === `${this.symbol}@aggTrade`) {
                this.processTrade(msg.data);
            } else if (msg.stream === `${this.symbol}@depth20@100ms`) {
                this.processDepth(msg.data);
            }
        };

        this.ws.onerror = (err) => {
            console.error('WebSocket Error:', err);
        };

        this.ws.onclose = () => {
            console.log('Connection closed, reconnecting in 5s...');
            setTimeout(() => this.connect(), 5000);
        }
    }

    processDepth(depth) {
        // depth.b: bids [[price, qty], ...], depth.a: asks [[price, qty], ...]
        this.orderBook = {
            bids: depth.b.map(item => ({ price: parseFloat(item[0]), quantity: parseFloat(item[1]) })),
            asks: depth.a.map(item => ({ price: parseFloat(item[0]), quantity: parseFloat(item[1]) }))
        };
        this.emitUpdate();
    }

    processTrade(trade, isHistory = false) {
        const price = parseFloat(trade.p);
        const quantity = parseFloat(trade.q);
        const time = trade.T;
        const isSell = trade.m;

        const candleTime = Math.floor(time / 60000) * 60000;

        if (candleTime > this.activeCandleTime) {
            this.activeCandleTime = candleTime;
        }

        if (!this.candles[candleTime]) {
            this.candles[candleTime] = {
                time: candleTime,
                open: price,
                high: price,
                low: price,
                close: price,
                volume: 0,
                delta: 0,
                poc: price,
                maxLevelVolume: 0,
                levels: {} // price -> { buy: 0, sell: 0, delta: 0 }
            };

            // Clean up old candles (> 60 mins)
            const cutoff = candleTime - 60 * 60000;
            Object.keys(this.candles).forEach(key => {
                if (parseInt(key) < cutoff) delete this.candles[key];
            });
        }

        const candle = this.candles[candleTime];

        candle.close = price;
        candle.high = Math.max(candle.high, price);
        candle.low = Math.min(candle.low, price);
        candle.volume += quantity;
        candle.delta += isSell ? -quantity : quantity;

        const levelPrice = price.toFixed(1);

        if (!candle.levels[levelPrice]) {
            candle.levels[levelPrice] = { buy: 0, sell: 0, delta: 0, total: 0 };
        }

        const level = candle.levels[levelPrice];
        if (isSell) {
            level.sell += quantity;
            level.delta -= quantity;
        } else {
            level.buy += quantity;
            level.delta += quantity;
        }
        level.total += quantity;

        // POC Update
        if (level.total > candle.maxLevelVolume) {
            candle.maxLevelVolume = level.total;
            candle.poc = parseFloat(levelPrice);
        }

        // Global Session Profile Update (can be simple map)
        if (!this.sessionProfile) this.sessionProfile = {};
        if (!this.sessionProfile[levelPrice]) this.sessionProfile[levelPrice] = 0;
        this.sessionProfile[levelPrice] += quantity;

        // Large Order Detection
        if (quantity >= this.largeOrderThreshold) {
            if (this.onLargeOrder) {
                this.onLargeOrder({ price, quantity, isSell, time });
            }
        }

        if (!isHistory) this.emitUpdate();
    }

    getSortedCandles() {
        return Object.values(this.candles).sort((a, b) => a.time - b.time);
    }

    setThreshold(val) {
        this.largeOrderThreshold = val;
    }

    disconnect() {
        if (this.ws) this.ws.close();
    }
}
