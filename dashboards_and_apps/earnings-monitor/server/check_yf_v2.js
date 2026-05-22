import * as yf from 'yahoo-finance2';
console.log('Keys:', Object.keys(yf));
console.log('Default type:', typeof yf.default);
if (yf.default && yf.default.prototype) {
    console.log('Default Prototype:', Object.keys(yf.default.prototype));
}
