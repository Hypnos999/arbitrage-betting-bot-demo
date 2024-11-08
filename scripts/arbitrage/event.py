from scripts.arbitrage.outcome import Outcome
from scripts.arbitrage.info import Info


class Event:
    def __init__(
        self,
        bet_radar_id: str,
        outcomes: list[Outcome],
        info: Info,
        sportbook: str,
    ):
        self.bet_radar_id = bet_radar_id
        self.outcomes = outcomes
        self.info = info
        self.sportbook = sportbook

    def update_outcomes(self, new_outcomes: list[Outcome]):
        for outcome in new_outcomes:
            outcome_overwritten = False
            for i, ot in enumerate(self.outcomes):
                if ot.bet_type == outcome.bet_type and ot.outcome == outcome.outcome:
                    self.outcomes[i] = outcome
                    outcome_overwritten = True
                    break

            if not outcome_overwritten:
                self.outcomes.append(outcome)

    @property
    def outcomes(self):
        return self._outcomes

    @outcomes.setter
    def outcomes(self, value: list[Outcome]):
        if not isinstance(value, list):
            raise ValueError("outcomes must be a list")

        for odd in value:
            if not isinstance(odd, Outcome):
                raise ValueError("outcomes must be a list of Outcome objects")

        self._outcomes = value

    @property
    def bet_radar_id(self):
        return self._bet_radar_id

    @bet_radar_id.setter
    def bet_radar_id(self, value: str) -> None:
        if not isinstance(value, str):
            raise ValueError("bet_radar_id must be a string")

        try:
            int(value)
            if int(value) < 0 or str(float(value)) == value:
                raise ValueError(f"bet_radar_id must be a string and not negative or a float {value}")

        except:
            raise ValueError("bet_radar_id must be a a numerical string and not negative")

        self._bet_radar_id = value

    @property
    def info(self):
        return self._info

    @info.setter
    def info(self, value: Info):
        if not isinstance(value, Info):
            raise ValueError("info must be an instance of the Info class")

        self._info = value

    @property
    def sportbook(self):
        return self._sportbook

    @sportbook.setter
    def sportbook(self, value: str):
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

    def to_dict(self) -> dict:
        return {
            "bet_radar_id": self.bet_radar_id,
            "outcomes": [outcome.to_dict() for outcome in self.outcomes],
            "info": self.info.to_dict(),
            "sportbook": self.sportbook,
        }

    @classmethod
    def from_dict(cls, data: dict):
        if not isinstance(data, dict):
            print(data)
        return cls(
            bet_radar_id=data["bet_radar_id"],
            outcomes=[Outcome.from_dict(outcome) for outcome in data["outcomes"]],
            info=Info.from_dict(data["info"]),
            sportbook=data["sportbook"],
        )
