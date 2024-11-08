from scripts.arbitrage.outcome import Outcome
from scripts.arbitrage.sport import Sport
from scripts.arbitrage.bet_type import BetType
from scripts.arbitrage.bet_id import BetID


class Bet(Outcome):
    def __init__(
        self,
        stake: float | int,
        win: float | int,
        outcome: Outcome
    ):
        super().__init__(outcome.odd, outcome.outcome, outcome.sportbook, outcome.bet_id, outcome.sport, outcome.bet_type)

        self.stake = stake
        self.win = win

    @property
    def stake(self):
        return self._stake

    @stake.setter
    def stake(self, value: int):
        if not isinstance(value, int):
            raise ValueError('stake value must be an integer')

        self._stake = value

    @property
    def win(self):
        return self._win

    @win.setter
    def win(self, value: float | int):
        if not isinstance(value, (float, int)):
            raise ValueError('win value must be a float or an integer')

        elif value <= 0:
            raise ValueError('win value must be greater than 0')

        elif value < self.stake:
            raise ValueError('win value must not be greater than stake')

        self._win = int(value)

    def to_dict(self):
        return {
            'stake': self.stake,
            'win': self.win,
            'odd': self.odd,
            'outcome': self.outcome,
            'sportbook': self.sportbook,
            'bet_id': self.bet_id.to_dict(),
            'sport': self.sport,
            'bet_type': self.bet_type
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            stake=data['stake'],
            win=data['win'],
            outcome=Outcome(
                outcome=data['outcome'],
                odd=data['odd'],
                sportbook=data['sportbook'],
                bet_id=BetID.from_dict(data['bet_id']),
                bet_type=data["bet_type"],
                sport=data['sport'],
            )
        )

    def __repr__(self):
        return f"Bet(stake: {self.stake}, win: {self.win}, odd: {self.odd}, outcome: {self.outcome}, {self.sportbook}, {self.bet_id}, {self.sport}, {self.bet_type})"