// Main Entry Point
// Assumes Games and UI are loaded

const ui = new UI();
let currentBalance = 1000;
let currentInstance = null;

const games = {
    blackjack: () => new BlackjackGame(), // Use global classes
    baccarat: () => new BaccaratGame(currentBalance)
};

// Lobby Logic
const lobby = document.getElementById('lobby-overlay');
document.getElementById('select-blackjack').addEventListener('click', () => startGame('blackjack'));
document.getElementById('select-baccarat').addEventListener('click', () => startGame('baccarat'));

function startGame(mode) {
    lobby.classList.add('hidden');

    // Instantiate Game
    if (mode === 'blackjack') {
        currentInstance = new BlackjackGame();
        currentInstance.balance = currentBalance; // Carry over balance
        currentInstance.subscribe(state => {
            state.gameType = 'blackjack';
            currentBalance = state.balance;
            ui.update(state);
            handleAutoReset(state);
        });
    } else {
        currentInstance = new BaccaratGame(currentBalance);
        currentInstance.subscribe(state => {
            currentBalance = state.balance;
            ui.update(state);
            handleAutoReset(state);
        });
    }

    ui.setGameMode(mode);
    currentInstance.notify();
}

let resetTimer = null;
function handleAutoReset(state) {
    if (state.state === 'result' || state.state === 'gameOver') {
        if (resetTimer) clearTimeout(resetTimer);
        resetTimer = setTimeout(() => {
            if (currentInstance) currentInstance.resetGame();
        }, 3000);
    }
}


// Event Delegation
// Chips
// (Logic consolidated below)

// Since Baccarat betting is different (Spot clicking), we need to handle that.
// Let's modify Chip logic:
// Blackjack: Click Chip = Add to Bet immediately (Standard simple UI).
// Baccarat: Click Chip = Select Coin. Click Spot = Place Bet.

let selectedChipValue = 10;
// Highlight selected chip
document.querySelectorAll('.chip').forEach(btn => {
    btn.addEventListener('click', (e) => {
        selectedChipValue = parseInt(e.target.dataset.value);
        Sound.playChip();
        // Visual feedback for selected chip
        document.querySelectorAll('.chip').forEach(c => c.style.border = '5px dashed white');
        e.target.style.border = '5px solid var(--gold-accent)';

        // If Blackjack, just add it (Legacy behavior support)
        if (ui.currentGameType === 'blackjack') {
            currentInstance.placeBet(selectedChipValue);
        }
    });
});


// Baccarat Spots
document.getElementById('bet-player').addEventListener('click', () => baccaratBet('player'));
document.getElementById('bet-banker').addEventListener('click', () => baccaratBet('banker'));
document.getElementById('bet-tie').addEventListener('click', () => baccaratBet('tie'));
document.getElementById('bet-ppair').addEventListener('click', () => baccaratBet('ppair'));
document.getElementById('bet-bpair').addEventListener('click', () => baccaratBet('bpair'));

function baccaratBet(type) {
    if (ui.currentGameType !== 'baccarat') return;
    Sound.playChip();
    currentInstance.placeBet(type, selectedChipValue);
}


// Generic Controls
document.getElementById('btn-deal').addEventListener('click', () => currentInstance.deal());
document.getElementById('btn-clear').addEventListener('click', () => {
    if (currentInstance.clearBet) currentInstance.clearBet();
    if (currentInstance.clearBets) currentInstance.clearBets();
});

// Blackjack Specifics
document.getElementById('btn-hit').addEventListener('click', () => {
    if (ui.currentGameType === 'blackjack') currentInstance.hit();
});
document.getElementById('btn-stand').addEventListener('click', () => {
    if (ui.currentGameType === 'blackjack') currentInstance.stand();
});
document.getElementById('btn-double').addEventListener('click', () => {
    if (ui.currentGameType === 'blackjack') currentInstance.doubleDown();
});
document.getElementById('btn-split').addEventListener('click', () => {
    if (ui.currentGameType === 'blackjack') currentInstance.split();
});
document.getElementById('btn-ins-yes').addEventListener('click', () => {
    if (ui.currentGameType === 'blackjack') currentInstance.buyInsurance();
});
document.getElementById('btn-ins-no').addEventListener('click', () => {
    if (ui.currentGameType === 'blackjack') currentInstance.declineInsurance();
});

// Lobby Return
document.getElementById('btn-lobby').addEventListener('click', () => {
    lobby.classList.remove('hidden');
    // Optional: Pause auto-reset?
    if (resetTimer) clearTimeout(resetTimer);
});

// Restart (legacy, mostly unused now)
document.getElementById('btn-restart').addEventListener('click', () => {
    currentInstance.resetGame();
});

// Blackjack Spot Logic
const bjSpot = document.getElementById('betting-spot');
if (bjSpot) {
    bjSpot.addEventListener('click', () => {
        if (ui.currentGameType === 'blackjack') {
            // Place selected chip value
            currentInstance.placeBet(selectedChipValue);
            Sound.playChip();
        }
    });
}

// Initial
// Show lobby (handled by CSS default)
