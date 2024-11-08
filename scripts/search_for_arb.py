from scripts.arbitrage.highest_odds import HighestOdds
from scripts.config import Config
from scripts.arbitrage.arb import Arb
from scripts.arbitrage.event import Event
from multiprocessing import Queue
import pickle
from copy import deepcopy


def run(
    data_queue: Queue,
    events: dict[str: list[Event]],
    config: Config,
) -> bool | list[dict[str: list[Event]] | list[HighestOdds] | list[Arb] | Arb]:
    """This function run a loop until if find at least one arbitrage opportunity"""

    # retrieve all new data from the queue
    events: dict[str: list[Event]] = events
    updated_data = []
    while not data_queue.empty():
        updated_data.append(pickle.loads(data_queue.get()))

    if not updated_data:
        return False

    for website_data in updated_data:
        website = list(website_data.keys())[0]

        # delete website events from events data
        for bet_radar_id in deepcopy(events):
            for i, event in enumerate(events[bet_radar_id]):
                if event.sportbook == website:
                    events[bet_radar_id].pop(i)
                    break

        if website_data[website] is None:
            continue

        website_events = list(map(
            lambda dict_: Event.from_dict(dict_),
            website_data[website]
        ))

        for event in website_events:
            if event.bet_radar_id not in events:
                events[event.bet_radar_id] = []

            events[event.bet_radar_id].append(event)

    arbs: list[Arb] = []
    highest_odds_list = []
    for bet_radar_id in events:

        highest_odds_list.append(HighestOdds(events[bet_radar_id], bet_radar_id))
        if not highest_odds_list[-1].status:
            continue

        new_arbs = Arb.from_highest_odds(
            highest_odds_list[-1],
            config.probability_treshold,
            config.bet_round_up,
            config.total_amount,
        )

        arbs += [arb for arb in new_arbs]

    # select the arb with the highest score
    if not arbs:
        return [events, highest_odds_list]

    lowest_prob = 1
    index = None

    for i, arb in enumerate(arbs):
        if not arb.status:
            continue

        if arb.probability < lowest_prob:
            index = i

    if index is None:
        return [events, highest_odds_list, arbs]

    return [events, highest_odds_list, arbs, arbs[index]]
