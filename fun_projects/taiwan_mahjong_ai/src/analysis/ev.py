
class EVCalculator:
    def __init__(self):
        pass

    def calculate_ev(self, discard_tile, win_prob, score, deal_in_prob, deal_in_cost):
        """
        EV = (P_win * Score) - (P_deal_in * Cost) - (P_draw * Penalty)
        """
        return (win_prob * score) - (deal_in_prob * deal_in_cost)

    def estimate_hand_value(self, hand):
        """
        Estimates 'Tai' (Fan) count.
        Placeholder logic.
        """
        return 5 # Assume average 5 Tai
