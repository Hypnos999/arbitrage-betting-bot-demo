from datetime import datetime
from scripts.bots.utils import click_element, write_input
from scripts.bots.bot import Bot
from scripts.arbitrage.bet_id import BetID
from scripts.arbitrage.event import Event
from scripts.arbitrage.info import Info
from scripts.arbitrage.outcome import Outcome
from nodriver.core.connection import ProtocolException
import time


class Vincitu(Bot):
    """vincitu"""  # DO NOT DELETE THIS

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def prep(self) -> None:
        await self.page.get(self.betting_urls[self.sport_to_use])
        await self.page.sleep(5)
        await self.page

        # delete selected bets
        try:
            clean_bets_btn = await self.page.select('.ib_delscom')
            await click_element(clean_bets_btn)
            await self.page.sleep()
        except:
            pass

    async def place_bet(self):
        t = time.time()
        while True:
            try:
                await self.page.evaluate(f'''document.getElementsByClassName("aggiornata {self.bet.bet_id.bet_id}")[0].click()''')
                await self.page.sleep()
                break
            except ProtocolException:
                pass

            if time.time() - t > 10:
                raise Exception("Could not find bet element or bet is closed")

        amount_input = await self.page.select('#cstake')
        await click_element(amount_input)
        await write_input(str(int(self.bet.stake)), amount_input)
        amount_input_value = await amount_input.apply("(el) => {el.dispatchEvent(new Event('keyup')); return el.value}")
        if int(amount_input_value.replace(',', '.')) != int(self.bet.stake):
            raise Exception("Failed to write amount input")

        self.pay_bet_button = await self.page.select("a[title='Piazza la scommessa']")
        self.place_bet_success.value = int(True)

        self.website_checker_element = await self.page.select("#ioval")
        self.odd_value.value = float(self.website_checker_element.text.replace(',', '.'))

        # odd_el = await self.page.select("#ioval")
        # self.odd_value.value = float(odd_el.text.replace(',', '.'))

    def arb_checker(self):
        """track AJAX request used for double check before paying bet"""
        updated_odd = None

        for event_obj in self.arb_checker_http_response_body['_ListData']:
            # if event_obj['id'] != event_id: continue ## skip unwanted data

            for odds_obj in event_obj['pkidl']:
                if self.bet.bet_id.bet_id != odds_obj['pkid']:
                    continue
                updated_odd = float(odds_obj['ov'])

        # in this case since the ajax request only has odds which were changed,
        # if we donn't find the odd we can assume the odd has not changed
        # so if we know that before running this func odd was still godd, it will still be
        if updated_odd is None:
            return

        self.updated_odd = updated_odd

    async def website_checker(self):
        await self.page
        try:
            await self.page.evaluate(f'''document.getElementsByClassName("aggiornata {self.bet.bet_id.bet_id}")[0]''')
        except:
            self.updated_odd = 1
            return

        self.updated_odd = float(self.website_checker_element.text.replace(',', '.'))

    def arb_finder(self):
        if self.tree is None:
            self.empty_events_tree = True
            return

        # we clean events only if it is the first time as vincitu use request only to update existing data
        if self.events is None:
            self.events = []

        for event_obj in self.arb_finder_http_response_body['_ListData']:
            amd_code = f'{event_obj["on"]}-{event_obj["id"]}'
            if amd_code not in self.tree:
                continue

            outcomes = []
            for outcome_obj in event_obj['pkidl']:
                outcome_id = str(outcome_obj["pkid"])
                if outcome_id not in list(self.tree[amd_code]['odds'].keys()):
                    continue

                bet_type = self.tree[amd_code]['odds'][outcome_id]['bet_type']
                outcome = self.tree[amd_code]['odds'][outcome_id]['outcome']

                outcomes.append(
                    Outcome(
                        odd=float(outcome_obj['ov']),
                        outcome=outcome,
                        sportbook=self.name,
                        bet_id=BetID(
                            bet_id=str(outcome_id)
                        ),
                        bet_type=bet_type,
                        sport=self.tree[amd_code]["info"].sport
                    )
                )

            bet_radar_id = self.tree[amd_code]["bet_radar_id"]
            event_found = False
            for event in self.events:
                if event.bet_radar_id == bet_radar_id:
                    event.update_outcomes(outcomes)
                    event_found = True
                    break

            if not event_found:
                self.events.append(
                    Event(
                        bet_radar_id=self.tree[amd_code]["bet_radar_id"],
                        outcomes=outcomes,
                        info=self.tree[amd_code]["info"],
                        sportbook=self.name
                    )
                )

    def make_tree(self):
        if self.tree_response_body['_ListData'] is None:
            self.empty_tree_response_body = True
            return

        self.tree = {}
        self.events = []

        for event_obj in self.tree_response_body['_ListData']:
            if "OfferNumber" not in event_obj: continue
            if "cod" not in event_obj: continue

            sport = event_obj["GroupDesc"].lower().strip()
            if sport == 'calcio':
                sport = 'football'
            elif sport == 'basket':
                sport = 'basketball'

            if sport != self.sport_to_use:
                continue

            tree_event = {
                "bet_radar_id": event_obj["BrMatchid"],
                "odds": {}
            }

            outcomes = []
            for odds_obj in event_obj['Class_Data']:
                bet_type = (odds_obj['ClassDesc'].replace('FINALE ', '').replace(" LIVE", "").replace(
                    "ESITO 1X2 T.R. SENZA MARGINE", "1X2").replace("TESTA/TESTA (ESCL.RITIRO)", "T/T"))
                # .replace("TESTA/TESTA SET (ESCL.RITIRO)", "T/T SET"))

                if bet_type in [
                    '1X2',
                    'GG/NG',
                    "T/T",
                ]:
                    for outcome_obj in odds_obj['Odds_Data']:
                        outcome = outcome_obj['GameName'].replace("(tt)", "")
                        outcome_id = str(outcome_obj['GamePkID'])
                        tree_event['odds'][outcome_id] = {
                            "outcome": outcome,
                            "bet_type": bet_type,
                            "odd":  float(outcome_obj['GameOdd'])
                        }

                        outcomes.append(
                            Outcome(
                                odd=float(outcome_obj['GameOdd']),
                                outcome=outcome,
                                sportbook=self.name,
                                bet_id=BetID(
                                    bet_id=str(outcome_id)
                                ),
                                bet_type=bet_type,
                                sport=sport
                            )
                        )

            if self.sport_to_use == "football":
                score = event_obj['ScoreDetails']
                if "|" in score:
                    highest = []
                    for partial_score in score.split('|'):
                        scores = [int(e) for e in partial_score.split('-')]

                        for i, s in enumerate(scores):
                            try:
                                highest[i] += s
                            except:
                                highest.append(s)
                    score = " : ".join([str(e) for e in highest])
                else:
                    score = score.replace('-', ' : ')

                score = score.split(':')
                score = (int(score[0]), int(score[1]))

            else:
                score = [e for e in event_obj['ScoreDetails'].split('|')]

            start = reversed(event_obj['StartDate'].split(' ')[0].split('/'))
            start = f"20{'-'.join(start)}T{event_obj['StartDate'].split(' ')[1]}+02:00"

            info = Info(
                sport=sport,
                name=event_obj["MatchName"].lower(),
                start=datetime.fromisoformat(start).timestamp(),
                tournament=event_obj["ManiDesc"].lower(),
                period=int(event_obj['Period']),
                time=int(event_obj['Current_Time']),  # from 0 to 90
                score=score,
                status=True if event_obj['Status'] == "0" else False
            )

            tree_event['info'] = info
            if tree_event["odds"]:
                amd_code = f'{event_obj["OfferNumber"]}-{event_obj["cod"]}'
                self.tree[amd_code] = tree_event

            bet_radar_id = str(event_obj['BrMatchid'])
            self.events.append(
                Event(
                    bet_radar_id=bet_radar_id,
                    outcomes=outcomes,
                    info=info,
                    sportbook=self.name
                )
            )
