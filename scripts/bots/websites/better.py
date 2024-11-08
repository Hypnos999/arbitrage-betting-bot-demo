from datetime import datetime

from scripts.bots.utils import click_element, write_input
from scripts.bots.bot import Bot
from scripts.arbitrage.bet_id import BetID
from scripts.arbitrage.outcome import Outcome
from scripts.arbitrage.info import Info
from scripts.arbitrage.event import Event
import time


class Better(Bot):
    """better"""  # DO NOT DELETE THIS

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def prep(self):
        await self.page.get(self.betting_urls[self.sport_to_use])
        await self.page.sleep(5)

        # delete all bets selected
        try:
            number_div = await self.page.select('span.badge.badge-pill.badge-num-evts')

            while True:
                try:
                    empty_btn = await self.page.select("#trash-widget-ticket")
                    await click_element(empty_btn)
                    await self.page.sleep()
                    break
                except:
                    number_of_bets = int(number_div.get_attribute('innerText'))
                    if number_of_bets == 0:
                        break
        except:
            pass

    async def place_bet(self):
        # activate fast bet (bet will be placed when bet element is clicked, way faster!)
        fast_bet_slider = await self.page.select('label.toggle')
        await click_element(fast_bet_slider)
        await self.page.sleep(3)
        await self.page

        amount_input = await self.page.select("input.showCaret")
        t = time.time()
        while True:
            # type amount [better uses "." as decimal separator]
            await click_element(amount_input)
            await write_input(str(int(self.bet.stake)), amount_input)

            # check amount typed
            amount_input_value = await amount_input.apply('(el) => el.value')

            if int(amount_input_value.replace(',', '.')) == int(self.bet.stake):
                break

            if time.time() - t > 10:
                raise Exception("Failed to write the right amount in the input box")

        # find odd elements
        self.pay_bet_button = await self.page.select(f'div[data-idselection="{self.bet.bet_id.bet_id}"]')
        for attr in self.pay_bet_button.attributes:
            if 'disable' in attr.split(' '):
                raise Exception('Bet is closed')

        self.place_bet_success.value = int(True)
        self.odd_value.value = float(self.pay_bet_button.children[-3].children[0].text)

    def arb_checker(self):
        if 'mktWbD' not in self.arb_checker_http_response_body:
            self.empty_http_response_body = True
            return

        new_odd_value = False
        for odds_id in self.arb_checker_http_response_body['mktWbD']:
            if self.arb_checker_http_response_body['mktWbD'][odds_id]['mn'] != self.bet.bet_id.bet_type: continue
            for outcome_obj in self.arb_checker_http_response_body['mktWbD'][odds_id]['ms']['0.0']['asl']:
                if outcome_obj['sn'] != self.bet.bet_id.outcome: continue

                new_odd_value = outcome_obj['ov']

        if new_odd_value is False:
            self.updated_odd = 1
        else:
            self.updated_odd = new_odd_value

    async def website_checker(self):
        await self.pay_bet_button.update()
        for attr in self.pay_bet_button.attributes:
            if 'disable' in attr.split(' '):
                self.updated_odd = 1
                return

        self.updated_odd = float(self.pay_bet_button.children[2].text)

    def arb_finder(self):
        if "leo" not in self.arb_finder_http_response_body:
            return

        self.events = []

        for event_obj in self.arb_finder_http_response_body['leo']:
            sport = event_obj['snm'].lower().strip()
            if sport == 'calcio':
                sport = 'football'
            elif sport == 'basket':
                sport = 'basketball'

            if sport != self.sport_to_use:
                continue

            market = 'mktWbG'
            if market not in event_obj:
                continue

            bet_radar_id = str(event_obj['eprid'])
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
                    bet_type = event_obj[market][odds_id]['mn'].replace('Doppia Chance', 'DC').replace('Gol/Nogol',
                                                                                                       'GG/NG')

                # basketball
                # T/T: 1, 2
                elif event_obj['snm'] == 'Basket':
                    if event_obj[market][odds_id]['mn'] not in ['Testa A Testa']: continue
                    bet_type = "T/T"

                # tennis
                # T/T: 1, 2
                elif event_obj['snm'] == 'Tennis':
                    if event_obj[market][odds_id]['mn'] not in ["Vincente Incontro (escl. ritiro)"]: continue
                    bet_type = "T/T"

                else:
                    continue

                # create odds dict
                for outcome_obj in event_obj[market][odds_id]['ms']['0']['asl']:
                    outcomes.append(
                        Outcome(
                            odd=float(outcome_obj['ov']),
                            outcome=outcome_obj['sn'],
                            bet_id=BetID(
                                bet_id=str(outcome_obj['si']),  # used in place_bet()
                                event_id=str(event_obj['aid']),  # used in place_bet()
                                bet_type=event_obj[market][odds_id]['mn'],
                                outcome=outcome_obj['sn']
                            ),
                            sportbook=self.name,
                            bet_type=bet_type,
                            sport=sport,
                        )
                    )

            info = Info(
                sport=sport,
                name=event_obj['enm'].lower(),
                time=int(event_obj['scrbrd']['eT'].split("'")[0]),
                score=(int(event_obj['scrbrd']['mS1']), int(event_obj['scrbrd']['mS2'])),
                start=None if 'edt' not in event_obj['scrbrd'] else datetime.fromisoformat(f"{event_obj['scrbrd']['edt'].replace(' ', 'T')}+02:00").timestamp()
            )

            if not outcomes:
                continue

            self.events.append(
                Event(
                    bet_radar_id,
                    outcomes,
                    info,
                    self.name
                )
            )
