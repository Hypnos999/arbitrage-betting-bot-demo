from scripts.arbitrage.sport import Sport


class BetType(Sport):
    def __init__(
        self,
        bet_type: str,
        sport: str
    ):
        super().__init__(sport)
        self.bet_type = bet_type

    @property
    def bet_type(self):
        return self._bet_type

    @bet_type.setter
    def bet_type(self, value: str):
        if not isinstance(value, str):
            raise ValueError('bet_type must be a string')

        if self.sport == 'football' and value not in ['1X2', 'DC', 'GG/NG']:
            raise ValueError(f'Wrong bet_type: {self.sport}/{value}')
        elif self.sport == 'basketball' and value not in ['T/T']:
            raise ValueError(f'Wrong bet_type: {self.sport}/{value}')
        elif self.sport == 'tennis' and value not in ['T/T']:
            raise ValueError(f'Wrong bet_type: {self.sport}/{value}')

        self._bet_type = value
