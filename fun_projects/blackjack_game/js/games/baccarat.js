// Baccarat Game Logic
// Dependency: Deck (assumed global or passed)

const BaccaratState = {
    BETTING: 'betting',
    DEALING: 'dealing',
    RESULT: 'result'
};

class BaccaratGame {
    constructor(balance) {
        this.deck = new Deck(); // Assumes Deck class is available globally or mixed in
        this.state = BaccaratState.BETTING;
        this.balance = balance || 1000;

        this.bets = {
            player: 0,
            banker: 0,
            tie: 0,
            ppair: 0,
            bpair: 0
        };

        this.hands = {
            player: [],
            banker: []
        };

        this.listeners = [];
        this.lastResult = '';
    }

    subscribe(listener) {
        this.listeners.push(listener);
    }

    notify() {
        // Calculate Total Bet safely
        const totalBet = (this.bets.player || 0) + (this.bets.banker || 0) + (this.bets.tie || 0) +
            (this.bets.ppair || 0) + (this.bets.bpair || 0);

        this.listeners.forEach(l => l({
            gameType: 'baccarat',
            state: this.state,
            hands: this.hands,
            scores: {
                player: this.calculateScore(this.hands.player),
                banker: this.calculateScore(this.hands.banker)
            },
            balance: this.balance,
            bets: this.bets,
            totalBet: totalBet,
            lastResult: this.lastResult
        }));
    }

    placeBet(type, amount) { // type: 'player', 'banker', 'tie', 'ppair', 'bpair'
        if (this.state !== BaccaratState.BETTING) return;
        if (this.balance >= amount) {
            this.balance -= amount;
            if (!this.bets[type]) this.bets[type] = 0;
            this.bets[type] += amount;
            this.notify();
            return true;
        }
        return false;
    }

    clearBets() {
        if (this.state !== BaccaratState.BETTING) return;
        const total = Object.values(this.bets).reduce((a, b) => a + b, 0);
        this.balance += total;
        this.bets = { player: 0, banker: 0, tie: 0, ppair: 0, bpair: 0 };
        this.notify();
    }

    calculateScore(hand) {
        let score = 0;
        for (let card of hand) {
            // J,Q,K,10 = 0. A = 1.
            let val = 0;
            if (['J', 'Q', 'K', '10'].includes(card.value)) val = 0;
            else if (card.value === 'A') val = 1;
            else val = parseInt(card.value);
            score += val;
        }
        return score % 10;
    }

    deal() {
        if (this.state !== BaccaratState.BETTING) return;
        const totalBet = Object.values(this.bets).reduce((a, b) => a + b, 0);
        if (totalBet === 0) return;

        this.deck.reset();
        this.deck.shuffle();
        this.hands = { player: [], banker: [] };
        this.state = BaccaratState.DEALING;
        this.notify();

        // Initial Deal (2 cards each)
        // Order: Player, Banker, Player, Banker
        this.hands.player.push(this.deck.deal());
        this.hands.banker.push(this.deck.deal());
        this.hands.player.push(this.deck.deal());
        this.hands.banker.push(this.deck.deal());

        this.runGameLogic();
    }

    runGameLogic() {
        // 1. Evaluate Side Bets (Pairs) based on first 2 cards
        let pPairWin = (this.hands.player[0].value === this.hands.player[1].value);
        let bPairWin = (this.hands.banker[0].value === this.hands.banker[1].value);

        // Evaluate Naturals & Third Card Rules
        let pScore = this.calculateScore(this.hands.player);
        let bScore = this.calculateScore(this.hands.banker);

        let finished = false;

        if (pScore >= 8 || bScore >= 8) {
            finished = true;
        } else {
            // Player Draw Rule
            let playerDrew = false;
            let player3rdCard = null; // Value

            if (pScore <= 5) {
                const card = this.deck.deal();
                this.hands.player.push(card);

                // Get value for calculation (0 for face cards)
                let val = 0;
                if (['J', 'Q', 'K', '10'].includes(card.value)) val = 0;
                else if (card.value === 'A') val = 1;
                else val = parseInt(card.value); // card.value is string

                player3rdCard = val;
                playerDrew = true;
                pScore = this.calculateScore(this.hands.player);
            }

            // Banker Draw Rule
            if (!playerDrew) {
                if (bScore <= 5) {
                    this.hands.banker.push(this.deck.deal());
                }
            } else {
                // Complex Banker Draw Logic uses the *Value* of the third card
                if (bScore <= 2) {
                    this.hands.banker.push(this.deck.deal());
                } else if (bScore === 3 && player3rdCard !== 8) {
                    this.hands.banker.push(this.deck.deal());
                } else if (bScore === 4 && [2, 3, 4, 5, 6, 7].includes(player3rdCard)) {
                    this.hands.banker.push(this.deck.deal());
                } else if (bScore === 5 && [4, 5, 6, 7].includes(player3rdCard)) {
                    this.hands.banker.push(this.deck.deal());
                } else if (bScore === 6 && [6, 7].includes(player3rdCard)) {
                    this.hands.banker.push(this.deck.deal());
                }
            }
        }

        // Final Score
        pScore = this.calculateScore(this.hands.player);
        bScore = this.calculateScore(this.hands.banker);

        this.state = BaccaratState.RESULT;

        let winner = '';
        let payout = 0;

        // Main Bets
        if (pScore > bScore) {
            winner = 'PLAYER WIN';
            payout += this.bets.player * 2;
        } else if (bScore > pScore) {
            winner = 'BANKER WIN';
            payout += this.bets.banker * 1.95;
        } else {
            winner = 'TIE';
            payout += this.bets.tie * 9;
            payout += this.bets.player;
            payout += this.bets.banker;
        }

        // Side Bets
        if (pPairWin) {
            winner += (winner ? ' + ' : '') + 'P.PAIR';
            payout += this.bets.ppair * 12; // 11:1 payout means You get Bet + 11xBet = 12xBet
        }
        if (bPairWin) {
            winner += (winner ? ' + ' : '') + 'B.PAIR';
            payout += this.bets.bpair * 12;
        }

        this.balance += payout;
        this.lastResult = `${winner} (${pScore} - ${bScore})`;
        this.bets = { player: 0, banker: 0, tie: 0, ppair: 0, bpair: 0 };

        this.notify();
    }

    resetGame() {
        this.state = BaccaratState.BETTING;
        this.hands = { player: [], banker: [] };
        this.notify();
    }
}
