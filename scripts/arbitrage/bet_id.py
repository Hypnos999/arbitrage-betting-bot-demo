class BetID:
    def __init__(
        self,
        bet_id: str | None = None,
        event_id: str | None = None,
        bet_type: str | None = None,
        outcome: str | None = None,
        url: str | None = None,
        sport: str | None = None,
        teams: list[str] | None = None,
    ):
        self.bet_id = bet_id
        self.event_id = event_id
        self.bet_type = bet_type
        self.outcome = outcome
        self.url = url
        self.sport = sport
        self.teams = teams

    @property
    def bet_id(self) -> str | None:
        return self._bet_id

    @bet_id.setter
    def bet_id(self, value: str | None):
        if not isinstance(value, str) and value is not None:
            raise ValueError(f'bet_id should be a string or none: {value}')

        self._bet_id = value

    @property
    def event_id(self) -> str | None:
        return self._event_id

    @event_id.setter
    def event_id(self, value: str | None):
        if not isinstance(value, str) and value is not None:
            raise ValueError('event_id should be a string')

        self._event_id = value

    @property
    def bet_type(self) -> str | None:
        return self._bet_type

    @bet_type.setter
    def bet_type(self, value: str | None):
        if not isinstance(value, str) and value is not None:
            raise ValueError('bet_type should be a string')

        self._bet_type = value

    @property
    def outcome(self) -> str | None:
        return self._outcome

    @outcome.setter
    def outcome(self, value: str | None):
        if not isinstance(value, str) and value is not None:
            raise ValueError('outcome should be a string')

        self._outcome = value

    @property
    def url(self) -> str | None:
        return self._url

    @url.setter
    def url(self, value: str | None):
        if not isinstance(value, str) and value is not None:
            raise ValueError('url should be a string')

        self._url = value

    @property
    def sport(self) -> str | None:
        return self._sport

    @sport.setter
    def sport(self, value: str | None):
        if not isinstance(value, str) and value is not None:
            raise ValueError('sport should be a string')

        self._sport = value

    @property
    def teams(self) -> list[str] | None:
        return self._teams

    @teams.setter
    def teams(self, value: list[str] | None):
        if not isinstance(value, list) and value is not None:
            raise ValueError('teams should be a list')

        if isinstance(value, list):
            for e in value:
                if not isinstance(e, str):
                    raise ValueError('teams should be a list of strings')

            if len(value) != 2:
                raise ValueError('teams should have exactly two elements')

        self._teams = value

    def to_dict(self):
        dict_ = {}
        for attr in self.__dict__:
            if self.__dict__[attr] is None:
                continue

            # [1:] since attr have _ in front because of @property
            dict_[attr[1:] if attr[0] == "_" else attr] = self.__dict__[attr]

        return dict_

    @classmethod
    def from_dict(cls, dict_):
        return cls(
            None if "bet_id" not in dict_ else dict_['bet_id'],
            None if "event_id" not in dict_ else dict_['event_id'],
            None if "bet_type" not in dict_ else dict_['bet_type'],
            None if "outcome" not in dict_ else dict_['outcome'],
            None if "url" not in dict_ else dict_['url'],
            None if "sport" not in dict_ else dict_['sport'],
            None if "teams" not in dict_ else dict_['teams']
        )
