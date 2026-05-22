// Removed imports/exports
const GameState = {
    BETTING: 'betting',
    DEALING: 'dealing',
    INSURANCE: 'insurance',
    PLAYER_TURN: 'playerTurn',
    DEALER_TURN: 'dealerTurn',
    GAME_OVER: 'gameOver'
};

class BlackjackGame {
    constructor() {
        this.deck = new Deck();
        this.state = GameState.BETTING;

        // Refactored to support multiple hands (Split)
        // Each hand: { cards: [], bet: 0, status: 'playing'|'busted'|'stood'|'doubled' }
        this.playerHands = [];
        this.activeHandIndex = 0;

        this.dealerHand = [];
        this.balance = 1000;
        this.currentBet = 0; // Initial bet size for new hands
        this.insuranceBet = 0;
        this.listeners = [];
        this.lastResult = '';
    }

    subscribe(listener) {
        this.listeners.push(listener);
    }

    notify() {
        this.listeners.forEach(listener => listener({
            state: this.state,
            playerHands: this.playerHands,
            activeHandIndex: this.activeHandIndex,
            dealerHand: (this.state === GameState.PLAYER_TURN || this.state === GameState.INSURANCE)
                ? [this.dealerHand[0], { hidden: true }]
                : this.dealerHand,
            balance: this.balance,
            currentBet: this.currentBet, // Base bet
            insuranceBet: this.insuranceBet,
            lastResult: this.lastResult,
            dealerScore: (this.state === GameState.PLAYER_TURN || this.state === GameState.INSURANCE)
                ? calculateScore([this.dealerHand[0]])
                : calculateScore(this.dealerHand)
        }));
    }

    placeBet(amount) {
        if (this.state !== GameState.BETTING) return;
        if (this.balance >= amount) {
            this.balance -= amount;
            this.currentBet += amount;
            this.notify();
            return true;
        }
        return false;
    }

    clearBet() {
        if (this.state !== GameState.BETTING) return;
        this.balance += this.currentBet;
        this.currentBet = 0;
        this.notify();
    }

    deal() {
        if (this.state !== GameState.BETTING || this.currentBet === 0) return;

        this.deck.reset();
        this.deck.shuffle();
        this.dealerHand = [];
        this.insuranceBet = 0;

        // Initialize first hand
        this.playerHands = [{
            cards: [],
            bet: this.currentBet,
            status: 'playing'
        }];
        this.activeHandIndex = 0;

        this.state = GameState.DEALING;
        this.notify();

        // Deal initial cards
        this.playerHands[0].cards.push(this.deck.deal());
        this.dealerHand.push(this.deck.deal());
        this.playerHands[0].cards.push(this.deck.deal());
        this.dealerHand.push(this.deck.deal());

        // Check for Dealer Ace (Insurance)
        if (this.dealerHand[0].value === 'A') {
            this.state = GameState.INSURANCE;
            this.notify();
            return;
        }

        this.checkInitialBlackjack();
    }

    checkInitialBlackjack() {
        const pScore = calculateScore(this.playerHands[0].cards);

        if (pScore === 21) {
            this.state = GameState.GAME_OVER;
            this.resolveGame();
        } else {
            this.state = GameState.PLAYER_TURN;
        }
        this.notify();
    }

    // Insurance Actions
    buyInsurance() {
        if (this.state !== GameState.INSURANCE) return;
        const cost = this.currentBet / 2;
        if (this.balance >= cost) {
            this.balance -= cost;
            this.insuranceBet = cost;
        }
        this.resolveInsurance();
    }

    declineInsurance() {
        if (this.state !== GameState.INSURANCE) return;
        this.resolveInsurance();
    }

    resolveInsurance() {
        // Dealer checks hole card
        const dScore = calculateScore(this.dealerHand);
        if (dScore === 21) {
            // Dealer has Blackjack
            if (this.insuranceBet > 0) {
                this.balance += this.insuranceBet * 3; // Pay 2:1 (return cost + 2x)
                this.lastResult = "INSURANCE PAYS";
            } else {
                this.lastResult = "DEALER BLACKJACK";
            }
            this.state = GameState.GAME_OVER;
            this.resolveGame(); // Will handle main bet loss/push
        } else {
            // Dealer does NOT have Blackjack
            if (this.insuranceBet > 0) {
                // Lose insurance
                this.lastResult = "INSURANCE LOST";
            }
            this.state = GameState.PLAYER_TURN;
        }
        this.notify();
    }

    // Player Actions on Active Hand
    getActiveHand() {
        return this.playerHands[this.activeHandIndex];
    }

    hit() {
        if (this.state !== GameState.PLAYER_TURN) return;
        const hand = this.getActiveHand();
        hand.cards.push(this.deck.deal());

        if (calculateScore(hand.cards) > 21) {
            hand.status = 'busted';
            this.nextHand();
        }
        this.notify();
    }

    stand() {
        if (this.state !== GameState.PLAYER_TURN) return;
        const hand = this.getActiveHand();
        hand.status = 'stood';
        this.nextHand();
        this.notify();
    }

    doubleDown() {
        if (this.state !== GameState.PLAYER_TURN) return;
        const hand = this.getActiveHand();
        if (hand.cards.length !== 2) return; // Can only double on 2 cards (usually)

        // Cost is equal to that hand's current bet
        if (this.balance >= hand.bet) {
            this.balance -= hand.bet;
            hand.bet += hand.bet;
            hand.cards.push(this.deck.deal());

            if (calculateScore(hand.cards) > 21) {
                hand.status = 'busted';
            } else {
                hand.status = 'doubled'; // effectively stood
            }
            this.nextHand();
        }
    }

    split() {
        if (this.state !== GameState.PLAYER_TURN) return;
        const hand = this.getActiveHand();
        // Check split conditions: 2 cards, same value (rough check, can refine to rank specific)
        // Standard blackjack: 10, J, Q, K are all value 10. Usually split requires SAME RANK (e.g. K+K, not K+Q).
        // For simplicity here: check value property equality or calculated value? 
        // Let's check strict value property (e.g. '10'=='10' or 'K'=='K').
        if (hand.cards.length !== 2) return;

        // Relaxed rule: Allow splitting if values are equal (e.g. 10 & King)
        if (getCardValue(hand.cards[0]) !== getCardValue(hand.cards[1])) return;

        if (this.balance >= hand.bet) {
            this.balance -= hand.bet;

            // Create new hand
            const newHand = {
                cards: [hand.cards.pop()], // Remove 2nd card from first hand
                bet: hand.bet,
                status: 'playing'
            };

            // Update current hand (now has 1 card)
            // Deal to current hand
            hand.cards.push(this.deck.deal());
            // Deal to new hand
            newHand.cards.push(this.deck.deal());

            // Insert new hand after current
            this.playerHands.splice(this.activeHandIndex + 1, 0, newHand);

            // Stay on current hand (Index 0).
            // User plays hand 0, then hand 1.
            this.notify();
        }
    }

    nextHand() {
        if (this.activeHandIndex < this.playerHands.length - 1) {
            this.activeHandIndex++;
            // Check for single Ace split rule? (Usually 1 card only). Ignoring for simplicity.
            // Check for immediate Blackjack on split? (Usually split aces don't get BJ payout).
            this.notify();
        } else {
            this.state = GameState.DEALER_TURN;
            this.notify();
            this.playDealer();
        }
    }

    playDealer() {
        // First, check if all player hands busted. If so, dealer doesn't need to play (except to show cards).
        const allBusted = this.playerHands.every(h => h.status === 'busted');

        if (allBusted) {
            this.state = GameState.GAME_OVER;
            this.resolveGame();
            this.notify();
            return;
        }

        const drawLoop = () => {
            const dScore = calculateScore(this.dealerHand);
            if (dScore < 17) {
                this.dealerHand.push(this.deck.deal());
                this.notify();
                setTimeout(drawLoop, 1000);
            } else {
                this.state = GameState.GAME_OVER;
                this.resolveGame();
                this.notify();
            }
        };
        setTimeout(drawLoop, 500);
    }

    resolveGame() {
        const dScore = calculateScore(this.dealerHand);
        let totalWinnings = 0;
        let mainResult = '';

        this.playerHands.forEach((hand, index) => {
            const pScore = calculateScore(hand.cards);
            let result = '';
            let isBlackjack = (pScore === 21 && hand.cards.length === 2 && this.playerHands.length === 1); // No BJ on split

            if (hand.status === 'busted') {
                result = 'BUST';
            } else if (dScore > 21) {
                result = 'WIN';
                totalWinnings += hand.bet * 2;
                if (isBlackjack) totalWinnings += hand.bet * 0.5;
            } else if (pScore > dScore) {
                result = 'WIN';
                totalWinnings += hand.bet * 2;
                if (isBlackjack) totalWinnings += hand.bet * 0.5;
            } else if (pScore < dScore) {
                result = 'LOSE';
            } else {
                result = 'PUSH';
                totalWinnings += hand.bet;
            }

            // Store result on hand for UI
            hand.result = result;
            if (index === 0) mainResult = result; // Approx summary
        });

        this.balance += totalWinnings;
        this.lastResult = this.playerHands.length > 1 ? "ROUND OVER" : mainResult;
        this.currentBet = 0;
    }

    resetGame() {
        this.state = GameState.BETTING;
        this.playerHands = [];
        this.dealerHand = [];
        this.insuranceBet = 0;
        this.notify();
    }
}
