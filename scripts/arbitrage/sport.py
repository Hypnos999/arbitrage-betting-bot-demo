class Sport:
    def __init__(
        self,
        sport: str
    ):
        self.sport = sport

    @property
    def sport(self):
        return self._sport

    @sport.setter
    def sport(self, value: str):
        if not isinstance(value, str):
            raise ValueError('sport must be a string')

        elif value not in [
            'football',
            'basketball',
            'tennis'
        ]:
            raise ValueError('sport must be either "football", "basketball" or "tennis"')

        self._sport = value
