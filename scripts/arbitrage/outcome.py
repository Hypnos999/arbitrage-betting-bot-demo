from scripts.arbitrage.bet_type import BetType
from scripts.arbitrage.sport import Sport
from scripts.arbitrage.bet_id import BetID


class Outcome(BetType):
    def __init__(
        self,
        odd: float,
        outcome: str,
        sportbook: str,
        bet_id: BetID,
        sport: str,
        bet_type: str,
    ):
        super().__init__(bet_type, sport)
        self.odd = odd
        self.sportbook = sportbook
        self.outcome = outcome
        self.bet_id = bet_id
        self.complentary_bet_type = None
        self.complentary_outcomes = None
        self.compatible_bet_type = None
        self.compatible_outcomes = None

    @property
    def outcome(self):
        return self._outcome

    @outcome.setter
    def outcome(self, value: str):
        if not isinstance(value, str):
            raise ValueError('outcome should be a string')

        if self.sport == 'football' and ((self.bet_type == '1X2' and value not in ['1', 'X', '2']) or (self.bet_type == 'DC' and value not in ['1X', 'X2', '12']) or (self.bet_type == 'GG/NG' and value not in ['GG', 'NG'])):
            raise ValueError(f'Wrong combination for sport/bet_type/outcome: {self.sport}/{self.bet_type}/{self.outcome}')

        elif self.sport == 'basketball' and self.bet_type == 'T/T' and value not in ['1', '2']:
            raise ValueError(f'Wrong combination for sport/bet_type/outcome: {self.sport}/{self.bet_type}/{self.outcome}')

        elif self.sport == 'tennis' and self.bet_type == 'T/T' and value not in ['1', '2']:
            raise ValueError(f'Wrong combination for sport/bet_type/outcome: {self.sport}/{self.bet_type}/{self.outcome}')

        self._outcome = value

    @property
    def odd(self):
        return self._odd

    @odd.setter
    def odd(self, value):
        if not isinstance(value, float):
            raise ValueError('odd value should be a float')

        if value < 1:
            value = 1.0

        self._odd = value

    @property
    def bet_id(self):
        return self._bet_id

    @bet_id.setter
    def bet_id(self, value: BetID):
        if not isinstance(value, BetID):
            raise ValueError('bet_id should be an instance of BetID')

        self._bet_id = value

    @property
    def sportbook(self):
        return self._sportbook

    @sportbook.setter
    def sportbook(self, value):
        if not isinstance(value, str):
            raise ValueError('sportbook should be a string')

        if value not in [
            "better",
            "eurobet",
            "vincitu",
            "betsson",
            "betflag",
            "sisal",
            "snai",
        ]:
            raise ValueError('sportbook should be one of the given values')

        self._sportbook = value

    @property
    def complentary_bet_type(self):
        return self._complentary_bet_type

    @complentary_bet_type.setter
    def complentary_bet_type(self, value: None):
        if value is not None:
            raise ValueError('complentary_bet_type must be None')

        if self.sport == 'football' and self.bet_type == 'DC':
            self._complentary_bet_type = '1X2'
        else:
            self._complentary_bet_type = self.bet_type

    @property
    def complentary_outcomes(self):
        return self._complentary_outcomes

    @complentary_outcomes.setter
    def complentary_outcomes(self, value: None):
        if value is not None:
            raise ValueError('complentary_outcomes value must be None')

        if self.sport == 'football' and self.bet_type == 'DC':
            if self.outcome == "1X":
                outcomes = ['2']
            elif self.outcome == "X2":
                outcomes = ['1']
            elif self.outcome == "12":
                outcomes = ['X']
            else:
                raise ValueError(f'Wrong outcome: {self.outcome}')

        elif self.sport == "football" and self.bet_type == "1X2":
            outcomes = ['1', 'X', '2']

        elif self.sport == "football" and self.bet_type == "GG/NG":
            outcomes = ['GG', 'NG']

        elif self.sport == "basketball" and self.bet_type == "T/T":
            outcomes = ['1', '2']

        elif self.sport == "tennis" and self.bet_type == "T/T":
            outcomes = ['1', '2']

        else:
            raise ValueError(f'Wrong combination for sport/bet_type/outcome: {self.sport}/{self.bet_type}/{self.outcome}')

        if self.outcome in outcomes:
            outcomes.pop(outcomes.index(self.outcome))
        self._complentary_outcomes = outcomes

    @property
    def compatible_outcomes(self):
        return self._compatible_outcomes

    @compatible_outcomes.setter
    def compatible_outcomes(self, value: None):
        if value is not None:
            raise ValueError('compatible_outcomes value must be None')

        outcomes = []
        if self.bet_type == "1X2":
            outcomes = ["1X", "X2", "12"]

        self._compatible_outcomes = outcomes

    @property
    def compatible_bet_type(self):
        return self._compatible_bet_type

    @compatible_bet_type.setter
    def compatible_bet_type(self, value: None):
        if value is not None:
            raise ValueError('compatible_bet_type value must be None')

        compatible_bet_type = None
        if self.bet_type == "1X2":
            compatible_bet_type = "DC"

        self._compatible_bet_type = compatible_bet_type

    def to_dict(self):
        dict_ = {}
        for attr in self.__dict__:
            if isinstance(self.__dict__[attr], BetID):
                dict_[attr[1:]] = self.__dict__[attr].to_dict()
            else:
                dict_[attr[1:]] = self.__dict__[attr]

        return dict_

    @classmethod
    def from_dict(cls, data):
        return cls(
            odd=data['odd'],
            outcome=data['outcome'],
            sportbook=data['sportbook'],
            bet_id=BetID.from_dict(data['bet_id']),
            sport=data['sport'],
            bet_type=data['bet_type'],
        )

    def __repr__(self):
        return f"Outcome(odd: {self.odd}, outcome: {self.outcome}, {self.sportbook}, {self.sport}, {self.bet_type})"