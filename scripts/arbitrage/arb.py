from scripts.arbitrage.bet import Bet
from scripts.arbitrage.highest_odds import HighestOdds
import itertools
from scripts.arbitrage.info import Info


class Arb:
    def __init__(
        self,
        probability: float,
        bets: list[Bet],
        probability_treshold: list[float],
        bet_radar_id: str,
        info: dict[str: Info]
    ):
        self.bet_radar_id = bet_radar_id
        self.probability_treshold = probability_treshold
        self.probability = probability
        self.bets = bets
        self.status = None
        self.info = info
        self.sportbooks = [bet.sportbook for bet in self.bets]

    @property
    def bets(self):
        return self._bets

    @bets.setter
    def bets(self, value: list[Bet]):
        """Raise error if bets are duplicated or don't have all their complementary bets"""
        if not isinstance(value, list):
            raise ValueError('bets is not a list')

        if len(value) == 0:
            raise ValueError('bets is empty')

        for bet in value:
            if not isinstance(bet, Bet):
                raise ValueError('bet is not an instance of Bet')

            corr = False
            for b in value:
                if b.sportbook == bet.sportbook and b.bet_type == bet.bet_type and b.outcome == bet.outcome:
                    if corr:
                        raise ValueError('duplicate bet')
                    corr = True

                elif (b.bet_type != bet.complentary_bet_type and b.bet_type != bet.compatible_bet_type) or (b.outcome not in bet.complentary_outcomes and b.outcome not in bet.compatible_outcomes):
                    raise ValueError(f'complementary bet should be of bet_type/{bet.complentary_bet_type} and outcome/{bet.complentary_outcomes} but is: {b}')

        if len(value) != len(set([b.sportbook for b in value])):
            raise ValueError('duplicate sportbooks')

        self._bets = value

    @classmethod
    def from_highest_odds(
        cls,
        highest_odds: HighestOdds,
        probability_treshold: list[float],
        round_up: float,
        total_amount: float,
    ):
        arbs = []

        for outcome in highest_odds.highest_odds:
            complementary_outcomes = {}

            for ot in highest_odds.highest_odds:
                if outcome.sportbook == ot.sportbook or outcome.complentary_bet_type != ot.bet_type or ot.outcome not in outcome.complentary_outcomes:
                    continue

                if ot.outcome not in complementary_outcomes:
                    complementary_outcomes[ot.outcome] = []
                complementary_outcomes[ot.outcome].append(ot)

            if len(complementary_outcomes) != len(outcome.complentary_outcomes):
                continue

            sportbooks = [[outcome.sportbook]] + [[ot.sportbook for ot in complementary_outcomes[outcome_str]] for outcome_str in complementary_outcomes]
            combinations = [list(c) for c in list(itertools.product(*sportbooks)) if len(c) == len(set(c))]

            for c in combinations:
                outcomes = [outcome]
                for i, outcome_str in enumerate(complementary_outcomes, start=1):
                    # print(outcome_str, complementary_outcomes[outcome_str])
                    for ot in complementary_outcomes[outcome_str]:
                        if ot.sportbook != c[i]:
                            continue

                        outcomes.append(ot)
                        break

                if len(outcomes) != len(complementary_outcomes) + 1:
                    continue

                probability = sum([1/ot.odd for ot in outcomes])
                if probability >= 1:
                    continue

                bets = []
                for ot in outcomes:
                    stake = round_up * round(total_amount * (1 / ot.odd / probability / round_up))
                    win = stake * ot.odd

                    if win - stake <= 0:
                        bets = False
                        break

                    bets.append(
                        Bet(
                            stake,
                            stake * ot.odd,
                            ot,
                        )
                    )

                if not bets:
                    continue

                arbs.append(cls(
                    probability,
                    bets,
                    probability_treshold,
                    highest_odds.bet_radar_id,
                    {event.sportbook: event.info for event in highest_odds.events if event.sportbook in c}
                ))

        return arbs

    @property
    def status(self):
        return self._status

    @status.setter
    def status(self, value: None):
        if value is not None:
            raise ValueError(f'status must be None: {value}')

        value = self.update_status()
        if not isinstance(value, bool):
            raise ValueError(f'status must be a bool: {value}')

        self._status = value

    def update_status(self) -> bool:
        return True

    @property
    def probability_treshold(self):
        return self._probability_treshold

    @probability_treshold.setter
    def probability_treshold(self, value: list[float]):
        if not isinstance(value, list):
            raise ValueError(f'probability_treshold is not a list: {value}')

        if len(value) != 2:
            raise ValueError(f'probability_treshold must have 2 values: {value}')

        for el in value:
            if not isinstance(el, float):
                raise ValueError(f'probability_treshold must be a list of float: {value}')

        self._probability_treshold = value

    def to_dict(self):
        return {
            'probability': self.probability,
            'status': self.status,
            'info': {w: info.to_dict() for w, info in self.info.items()},
            'bets': [b.to_dict() for b in self.bets],
        }
