import json
from copy import deepcopy
from scripts.arbitrage.event import Event
from scripts.arbitrage.outcome import Outcome


class HighestOdds:
    def __init__(
        self,
        events: list[Event],
        bet_radar_id: str
    ):
        self.bet_radar_id = bet_radar_id
        self.info = {}

        self.events = events
        self.status = None
        self.good_events = None
        self.highest_odds = None

    @property
    def highest_odds(self):
        return self._highest_odds

    @highest_odds.setter
    def highest_odds(self, value: None):
        if value is not None:
            raise ValueError('highest_odds value can\'t be set manually')

        highest_odds: list[Outcome] = []
        for event in self.good_events:
            for outcome in event.outcomes:
                higher_odd_found = False

                i = 0
                for ot in deepcopy(highest_odds):
                    if ot.sport == outcome.sport and ot.bet_type == outcome.bet_type and ot.outcome == outcome.outcome:
                        if ot.odd > outcome.odd:
                            highest_odds.pop(i)

                        elif ot.odd < outcome.odd:
                            higher_odd_found = True
                            break

                        else:
                            i += 1

                if not higher_odd_found:
                    highest_odds.append(outcome)

        self._highest_odds = highest_odds

    @property
    def status(self):
        return self._status

    @status.setter
    def status(self, value: None) -> None:
        if not isinstance(value, type(None)):
            raise ValueError('status value can\'t be set, provide a None value please')

        value = self.update_status()
        if not isinstance(value, bool):
            raise ValueError(f'status value from update_status() must be a boolean: {value}')

        self._status = value

    def update_status(self) -> bool:
        return True

    @property
    def good_events(self):
        return self._good_events

    @good_events.setter
    def good_events(self, value: None):
        if value is not None:
            raise ValueError('good_events value can\'t be set manually')

        good_events = []
        for event in self.events:
            if event.info.status is not None and not event.info.status:
                continue

            good_events.append(event)

        self._good_events = good_events

    @property
    def events(self):
        return self._events

    @events.setter
    def events(self, value: list[Event]):
        if not isinstance(value, list):
            raise ValueError("events must be a list")

        events = []
        for event in value:
            if not isinstance(event, Event):
                raise ValueError(f"events must be a list of Event: {events}")

            if event.bet_radar_id != self.bet_radar_id:
                raise ValueError(f"events must have the same bet_radar_id: {json.dumps([e.to_dict() for e in events], indent=2)}")

            events.append(event)

        self._events = events

    @property
    def bet_radar_id(self):
        return self._bet_radar_id

    @bet_radar_id.setter
    def bet_radar_id(self, value: str):
        if not isinstance(value, str):
            raise ValueError(f"bet_radar_id must be a string: {value}")

        if '.' in value:
            raise ValueError(f'bet_radar_id must be a numerical string with not ".": {value}')

        try:
            int(value)
            if int(value) <= 0:
                raise
        except:
            raise ValueError(f"bet_radar_id must be a numerical string but not negative: {value}")

        self._bet_radar_id = value

    def to_dict(self):
        return {
            "bet_radar_id": self.bet_radar_id,
            "status": self.status,
            "info": self.info,
            "highest_odds": [outcome.to_dict() for outcome in self.highest_odds],
        }
