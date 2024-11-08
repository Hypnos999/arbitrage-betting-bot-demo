from scripts.arbitrage.sport import Sport


class Info:
    def __init__(
        self,
        *,
        sport: str,
        status: bool | None = None,
        time: int | None = None,
        period: int | None = None,
        start: float | int | None = None,
        score: tuple[int, ...] | None = None,
        name: str | None = None,
        tournament: str | None = None,
    ):
        self.sport = sport
        self.status = status
        self.time = time
        self.period = period
        self.start = start
        self.score = score
        self.name = name
        self.tournament = tournament

    @property
    def start(self) -> str | None:
        return self._start

    @start.setter
    def start(self, value: float | int | None):
        if not isinstance(value, (float, int)) and value is not None:
            raise ValueError(f'start should be a float, int or None: {value}')

        self._start = value

    @property
    def status(self) -> bool | None:
        return self._status

    @status.setter
    def status(self, value: bool | None):
        if not isinstance(value, bool) and value is not None:
            raise ValueError(f'status should be a boolean or None: {value}')

        self._status = value

    @property
    def sport(self) -> str:
        return self._sport

    @sport.setter
    def sport(self, value: str):
        try:
            sport = Sport(value)
        except:
            raise ValueError(f"invalid sport: {value}")

        self._sport = sport.sport

    @property
    def score(self):
        return self._score

    @score.setter
    def score(self, value: tuple[int, int] | None):
        try:
            if value is not None:
                if not isinstance(value, tuple):
                    raise ValueError("score should be a tuple or None")

                if len(value) != 2:
                    raise ValueError("score should have exactly two elements")

                for e in list(value):
                    if not isinstance(e, int):
                        raise ValueError("score elements should be a tuple of integers")

        except ValueError as e:
            raise ValueError(f"score value of {value} raise an exeption: {e}")

        self._score = value

    @property
    def time(self) -> int | None:
        return self._time

    @time.setter
    def time(self, value: int | None):
        if not isinstance(value, int) and value is not None:
            raise ValueError(f'time should be an integer or None: {value}')

        self._time = value

    @property
    def period(self) -> int | None:
        return self._period

    @period.setter
    def period(self, value: int | None):
        if not isinstance(value, int) and value is not None:
            raise ValueError(f'period should be an integer or None: {value}')

        self._period = value

    def to_dict(self):
        dict_ = {}
        for attr in self.__dict__:
            if self.__dict__[attr] is None:
                continue

            dict_[attr[1:] if attr[0] == "_" else attr] = self.__dict__[attr]

        return dict_

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            sport=data["sport"],
            status=None if "status" not in data else data["status"],
            time=None if "time" not in data else data["time"],
            period=None if "period" not in data else data["period"],
            start=None if "start" not in data else data["start"],
            score=None if "score" not in data else data["score"],
            name=None if "name" not in data else data["name"],
            tournament=None if "tournament" not in data else data["tournament"],
        )
