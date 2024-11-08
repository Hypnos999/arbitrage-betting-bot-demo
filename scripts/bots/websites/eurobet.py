from scripts.arbitrage.event import Event
from scripts.arbitrage.outcome import Outcome
from scripts.bots.bot import Bot
from scripts.bots.utils import click_element, write_input
from scripts.arbitrage.bet_id import BetID
from scripts.arbitrage.info import Info
import json


class Eurobet(Bot):
    """eurobet"""  # DON'T REMOVE THIS

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def prep(self) -> None:
        await self.page.get(self.betting_urls[self.sport_to_use])
    
        try:
            empty_bet_buttons = await self.page.select_all('span.Euicoico_elimina')
            for button in empty_bet_buttons:
                await click_element(button)
                await self.page.sleep()
        except:
            pass
    
        await self.page.sleep(5)

    async def place_bet(self):
        await self.page.get(self.bet.bet_id.url)
        await self.page

        containers = await self.page.select_all('.box-container:has(.title-event.info-match)')

        for c in containers:
            bet_type = await c.query_selector('.title-event.info-match div')

            if bet_type.text.lower() != self.bet.bet_id.bet_type.lower():
                continue

            # select only active bets (thanks to ":not(.disable-quote)")
            bet_containers = await c.query_selector_all('.containerQuota:not(.disable-quote)')

            if not bet_containers:
                raise Exception('Bet is closed')

            for bet_container in bet_containers:
                bet_type_element = await bet_container.query_selector('[class="quotaType"]')

                if bet_type_element.text.lower() != self.bet.bet_id.outcome.lower():
                    continue

                self.website_checker_element = bet_container
                await click_element(bet_container)

                # this element doesn't use click_element() or write_input()
                # because otherwise it won't correctly update the inserted value
                amount_input = await self.page.select(".bet-amount-set form input")
                await amount_input.scroll_into_view()
                await amount_input.mouse_move()
                await amount_input.focus()
                await amount_input.clear_input()
                await amount_input.send_keys(str(int(self.bet.stake)))
                await amount_input.apply("(el) => el.blur()")

                await self.page.sleep()

                self.pay_bet_button = await self.page.select("a.btn-betslip.btn-bet")
                self.place_bet_success.value = int(True)
                odd_container = await bet_container.query_selector('[class="quota"]')
                self.odd_value.value = float(odd_container.text)
                return

        raise Exception('Bet not found')

    def arb_checker(self):
        updated_outcomes = None
        for sport_obj in self.arb_checker_http_response_body['result']['itemList']:
            if sport_obj['discipline'].lower() != self.bet.bet_id.sport.lower():
                continue
    
            for event_obj in sport_obj['itemList']:
                if len(event_obj['betGroupList']) == 0 or 'programBetradarInfo' not in event_obj['eventInfo'] or 'matchId' not in event_obj['eventInfo']['programBetradarInfo']:
                    continue
    
                code = str(event_obj['eventInfo']['programBetradarInfo']['matchId'])
                if code != self.bet.bet_radar_id:
                    continue
    
                updated_outcomes = make_outcomes(event_obj['betGroupList'][0]['oddGroupList'], url=False, sport=self.sport_to_use, sportbook=self.name)

        if not updated_outcomes or updated_outcomes is None:
            # self.logger.info('Arb check: no odd for current event were found --> False')
            self.updated_odd = 1

      
        else:
            for outcome in updated_outcomes:
                if self.bet.bet_type == outcome.bet_type and self.bet.outcome == outcome.outcome:
                    self.updated_odd = outcome.odd
                    return
                
            self.updated_odd = 1  # if no update is found it means bet is closed

    async def website_checker(self):
        await self.website_checker_element.update()
        for attr in self.website_checker_element.attributes:
            if "disable-quote" in attr.split(' '):
                self.updated_odd = 1
                return

        odd_container = await self.website_checker_element.query_selector('.quota')
        self.updated_odd = float(odd_container.text)

    def arb_finder(self):
        self.events = []
    
        for sport_obj in self.arb_finder_http_response_body['result']['itemList']:
            sport = sport_obj['discipline'].lower().strip()
            sport = sport.replace('calcio', 'football')
            sport = sport.replace('basket', 'basketball')

            if sport != self.sport_to_use:
                continue

            for event_obj in sport_obj['itemList']:
                if len(event_obj['betGroupList']) == 0 or 'programBetradarInfo' not in event_obj['eventInfo'] or 'matchId' not in event_obj['eventInfo']['programBetradarInfo'] or event_obj['eventInfo']['programBetradarInfo']['matchId'] == 0: continue
    
                url = f"https://www.eurobet.it/it/scommesse-live/#!{event_obj['breadCrumbInfo']['fullUrl']}"
                outcomes = make_outcomes(event_obj['betGroupList'][0]['oddGroupList'], url, sport, self.name)

                try:
                    time = int(event_obj['eventInfo']['timeLive'].split("'")[0])
                except:
                    time = None

                try:
                    score = (int(event_obj['eventInfo']['teamHome']['score']), int(event_obj['eventInfo']['teamAway']['score']))
                except:
                    score = None

                info = {
                    'name': event_obj['eventInfo']['eventDescription'].lower(),
                    'sport': sport,
                    'start': event_obj['eventInfo']['eventData'],
                    'time': time,
                    'score': score

                    # 'period': '1' if 'scoreList' not in event_obj['eventInfo']['teamHome'] else "2"
                }

                info = Info(**info)
                bet_radar_id = str(event_obj['eventInfo']['programBetradarInfo']['matchId'])

                self.events.append(
                    Event(
                        bet_radar_id,
                        outcomes,
                        info,
                        self.name
                    )
                )


def make_outcomes(
    odds_objs,
    url: bool | str = False,
    sport: bool | str = False,
    sportbook: str = "eurobet",
) -> list[Outcome]:
    """Return a dictionary with all the odds for a certain event, without including bet id dictionary (outcome is a float representing the odd)"""

    outcomes = []
    for odds_obj in odds_objs:
        # football
        # 1X2: 1, X, 2
        if 'alternativeDescription' not in odds_obj:
            continue

        if not odds_obj["oddList"]:
            continue

        match odds_obj['oddGroupDescription'].strip():  # don't remove .strip()
            case "1X2":  # football 1X2: 1, X, 2
                bet_type = '1X2'
                ots = ['1', 'X', '2']

            case "T/T":  # basketball T/T: 1, 2
                bet_type = 'T/T'
                ots = ['1', '2']

            case "T/T (ESCL. RITIRO)":  # tennis T/T: 1, 2
                bet_type = 'T/T'
                ots = ['1', '2']

            case _:
                continue

        for i, outcome in enumerate(ots):
            if url:
                bet_id = BetID(
                    url=url,
                    bet_type=odds_obj['oddGroupDescription'].strip(),
                    outcome=odds_obj["oddList"][i]['oddDescription'].strip(),
                    sport=sport
                )
            else:
                bet_id = BetID()

            outcomes.append(
                Outcome(
                    odd=odds_obj['oddList'][i]['oddValue'] / 100.0,
                    outcome=outcome,
                    sportbook=sportbook,
                    bet_id=bet_id,
                    bet_type=bet_type,
                    sport=sport,
                )
            )

    return outcomes
