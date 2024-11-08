from datetime import datetime

from scripts.arbitrage.event import Event
from scripts.bots.bot import Bot
from scripts.bots.utils import click_element, write_input
from scripts.arbitrage.bet_id import BetID
from scripts.arbitrage.outcome import Outcome
from scripts.arbitrage.event import Event
from scripts.arbitrage.info import Info
import time


class Betflag(Bot):
    """betflag"""  # DON'T REMOVE THIS

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def prep(self):
        # We don't select spport page in prep as the reload of the page make it come back to football page
        await self.page.get(self.betting_urls[self.sport_to_use])
        await self.page
        await self.page.sleep(5)

        # close ad pop up
        try:
            close_ad = await self.page.select('.btn-close')
            await click_element(close_ad)
        except:
            pass

        # delete all bets selected
        try:
            delete_bets_button = await self.page.select('[data-testid="CloseIcon"]', 20)
            await click_element(delete_bets_button.parent)

        except:
            self.logger.info("Close bets beutton not found, line 141 in prep()")

        await self.page.sleep(5)
        await self.page

    async def place_bet(self):
        # click on the selected sport page
        await self.page
        sport_id = self.sport_to_use.replace("football", "1").replace("basketball", "2").replace("tennis", "5")
        sport_page = await self.page.select(f'div[id="{sport_id}"]')
        await click_element(sport_page)

        # click on the event page
        event_id = self.bet.bet_id.event_id
        event_page = await self.page.select(f"[id='{event_id}']", 60)
        await click_element(event_page)
        await self.page.sleep()
        await self.page

        bets_containers = await self.page.select_all(".css-zji253")
        find_bet = False
        bet_clickable = None
        for bets_container in bets_containers:
            if find_bet:
                break
            if bets_container is None:
                continue

            bet_type = await bets_container.query_selector(".css-1qgjvfo")
            if self.bet.bet_id.bet_type.lower() != bet_type.text.lower().strip():
                continue

            bets_el = await bets_container.query_selector_all(".MuiGrid-root.MuiGrid-item.MuiGrid-grid-xs-4")
            for bet_el in bets_el:
                if bet_el is None:
                    continue

                outcome = await bet_el.query_selector("p")
                if self.bet.bet_id.outcome.lower() != outcome.text.lower().strip():
                    continue

                bet_clickable = await bet_el.query_selector("div")
                self.website_checker_element = bet_clickable

                # detect if the bet is closed
                for attr in bet_clickable.attributes:
                    if "css-10p8x5d" in attr.split(" "):
                        raise Exception("Bet is suspended")
                    elif "css-1fz7udc" in attr.split(" "):
                        raise Exception("Bet is closed")

                await click_element(bet_clickable)
                await self.page
                find_bet = True
                break

        if not find_bet or bet_clickable is None:
            raise Exception("Could not find bet element")

        timer = time.time()
        while True:
            amount_input = await self.page.select('.MuiInputBase-input.MuiInput-input')
            await click_element(amount_input)
            await write_input(str(int(self.bet.stake)), amount_input)

            amount_input_value = await amount_input.apply('(el) => el.value')
            if int(amount_input_value.replace(',', '.')) == int(self.bet.stake):
                break

            if time.time() - timer > 10:
                raise Exception("Failed to write the right amount in the input box")

        # find pay bet button ( scommetti btn )
        # self.pay_bet_button = await self.page.select(f'button.MuiButtonBase-root.MuiButton-root.MuiButton-text.MuiButton-textPrimary.MuiButton-sizeMedium.MuiButton-textSizeMedium.MuiButton-colorPrimary.MuiButton-root.MuiButton-text.MuiButton-textPrimary.MuiButton-sizeMedium.MuiButton-textSizeMedium.MuiButton-colorPrimary.css-1jhkro7')
        # self.pay_bet_button = await self.page.select(f'button.MuiButtonBase-root.MuiButton-root.MuiButton-text.MuiButton-textPrimary.MuiButton-sizeMedium.MuiButton-textSizeMedium.MuiButton-colorPrimary.MuiButton-root.MuiButton-text.MuiButton-textPrimary.MuiButton-sizeMedium.MuiButton-textSizeMedium.MuiButton-colorPrimary.css-12vzwcg')
        self.pay_bet_button = await self.page.select(f'button.MuiButtonBase-root.MuiButton-root.MuiButton-text.MuiButton-textPrimary.MuiButton-sizeMedium.MuiButton-textSizeMedium.MuiButton-colorPrimary.MuiButton-root.MuiButton-text.MuiButton-textPrimary.MuiButton-sizeMedium.MuiButton-textSizeMedium.MuiButton-colorPrimary')
        self.odd_value.value = float(bet_clickable.children[-1].text)
        self.place_bet_success.value = int(True)

    def arb_checker(self) -> None | bool:
        if 'mktWbD' not in self.arb_checker_http_response_body:
            self.empty_http_response_body = True
            return
    
        for odds_id in self.arb_checker_http_response_body['mktWbD']:
            if self.arb_checker_http_response_body['mktWbD'][odds_id]['mn'] != self.bet.bet_id.bet_type: continue
            for outcome_obj in self.arb_checker_http_response_body['mktWbD'][odds_id]['ms']['0.0']['asl']:
                if outcome_obj['sn'] != self.bet.bet_id.outcome:
                    continue
    
                self.updated_odd = outcome_obj['ov']
                return

        self.updated_odd = 1

    async def website_checker(self):
        # check if odd element has class that indicate it's closed
        await self.website_checker_element.update()
        for attr in self.website_checker_element.attributes:
            if "css-10p8x5d" in attr.split(" ") or "css-1fz7udc" in attr.split(" "):
                self.updated_odd = 1
                return

        self.updated_odd = float(self.website_checker_element.children[2].text)

    def arb_finder(self):
        self.events = []

        for event_obj in self.arb_finder_http_response_body['leo']:
            sport = event_obj['snm'].lower().strip()
            if sport == 'calcio':
                sport = 'football'
            elif sport == 'tennis':
                sport = 'tennis'
            
            if sport != self.sport_to_use:
                continue
    
            market = 'mktWbG'
            if market not in event_obj:
                continue
    
            if 'scrbrd' not in event_obj:
                continue
            if event_obj['scrbrd']['eventPhaseDesc'] == 'NOT_STARTED': 
                continue  # bets are closed
    
            bet_radar_id = str(event_obj['eprId'])
            try:
                float(bet_radar_id)
            except:
                continue

            outcomes = []
            for odds_id in event_obj[market]:
    
                # football
                # 1X2: 1, X, 2
                # DC: 1X, 12, X2
                # GG/NG: GG, NG
                if event_obj['snm'] == 'Calcio':
                    if event_obj[market][odds_id]['mn'] not in ['1X2', 'Doppia Chance', 'Gol/Nogol']: continue
                    bet_type = event_obj[market][odds_id]['mn'].replace('Doppia Chance', 'DC').replace('Gol/Nogol', 'GG/NG')
    
                # basketball
                # T/T: 1, 2
                elif event_obj['snm'] == 'Basket':
                    if event_obj[market][odds_id]['mn'] not in ['Testa A Testa']: continue
                    bet_type = "T/T"
    
                # tennis
                # T/T
                elif event_obj['snm'] == 'Tennis':
                    if event_obj[market][odds_id]['mn'] not in ["Vincente Incontro (escl. ritiro)"]: continue
                    bet_type = "T/T"
    
                else:
                    continue

                for outcome_obj in event_obj[market][odds_id]['ms']['0.0']['asl']:
                    outcomes.append(
                        Outcome(
                            odd=float(outcome_obj['ov']),
                            outcome=outcome_obj['sn'],
                            sportbook=self.name,
                            bet_id=BetID(
                                bet_id=str(outcome_obj['si']),
                                event_id=str(event_obj['eprId']),
                                bet_type=event_obj[market][odds_id]['mn'],
                                outcome=outcome_obj['sn']
                            ),
                            bet_type=bet_type,
                            sport=sport,
                        )
                    )

            if not outcomes:
                continue

            period = event_obj['scrbrd']['eventPhaseDesc'].replace("FIRST_HALF", "1").replace("SECOND_HALF", "2")
            try:
                period = int(period)
                # assert 1 <= period <= 2
            except:
                period = None

            info = {
                'sport': sport,
                'name': event_obj['enm'].lower(),
                'start': datetime.fromisoformat(event_obj['ed']).timestamp(),
                'score': (int(event_obj['scrbrd']['mS1']), int(event_obj['scrbrd']['mS2'])),  # for tennis it considers only the current set/game
                'time': int(event_obj['scrbrd']['eT'].split("'")[0]),  # for football i goes from 0 to 90 (or more), for tennis its like "2' Set"
                'period': period
            }

            info = Info(**info)

            self.events.append(
                Event(
                    bet_radar_id,
                    outcomes,
                    info,
                    self.name,
                )
            )

            # check odds and add them to results dict, this function is imported from scraper.py so it can be generalized for all scrapers
            # self.check_odds_and_append(odds, bet_radar_id, info)
