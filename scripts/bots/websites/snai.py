from datetime import datetime
from scripts.arbitrage.sport import Sport
from scripts.bots.bot import Bot
from scripts.bots.utils import click_element, write_input
from scripts.arbitrage.bet_id import BetID
from scripts.arbitrage.event import Event
from scripts.arbitrage.info import Info
from scripts.arbitrage.outcome import Outcome
import time


class Snai(Bot):
    """snai"""  # DO NOT DELETE THIS

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def prep(self):
        # goes to the right sport page
        await self.page.get(self.betting_urls[self.sport_to_use])
        await self.page
        await self.page.sleep(2)

        # delete selected bets
        try:
            open_ticket_btn = await self.page.select('.CarrelloTrigger_bigliettoActive__V3bG4')
            await click_element(open_ticket_btn)
            await self.page
        except:
            pass
    
        try:
            clean_bets_btn = await self.page.select('.SportTicketRemoveAllItems_cancelBtn__fHV2P')
            await click_element(clean_bets_btn)
            await self.page.sleep()
        except:
            pass

    async def place_bet(self):
        await self.page

        # find bet html element
        bet_element = await self.page.select(f'[data-testid="{self.bet.bet_id.bet_id}"]')
        self.website_checker_element = bet_element

        # check if the bet is closed
        for attr in bet_element.attributes:
            if "ScommesseEsitoSkeleton_container___crym" in attr:
                raise Exception("Bet is closed")

        # click on bet and save odd value
        await click_element(bet_element.children[0])

        # write amount in the input form
        # the while loop makes shure that it is correct or it raise and exception
        amount_input = await self.page.select('input.CarrelloInputImporto_input__cbmTA')
        t = time.time()

        while True:
            await click_element(amount_input)
            await write_input(str(int(self.bet.stake)), amount_input)
            amount_input_value = await amount_input.apply("(el) => {el.dispatchEvent(new Event('keyup')); return el.value}")

            if int(amount_input_value) == int(self.bet.stake):
                break

            if t > 10:
                raise Exception("Failed to write amount input")

        self.pay_bet_button = await self.page.select('button.Button_primary___NwMH.Button_buttonContainer__X4FDJ.Button_medium__kUPhE.SportTicketActionScommetti_button__T7dyQ.CarrelloEditQuotaInput_button__vYwMo')
        for attr in self.pay_bet_button.attributes:
            if "Button_disabled__dBLYL" in attr:
                raise Exception("Pay bet button is disabled")

        self.place_bet_success.value = int(True)
        self.odd_value.value = float(bet_element.children[0].text)

    def arb_checker(self):
        try:
            self.arb_checker_websocket_response_body[2][4][2]["data"]
        except:
            self.empty_wss_response_body = True
            return

        for msg in self.arb_checker_websocket_response_body[2][4][2]["data"]:
            if msg["message"] != "UpdateQuote": continue

            for outcome_id in msg["event"]:
                if outcome_id != self.bet.bet_id.bet_id: continue

                # odd is closed
                if not msg["event"][outcome_id]["isActive"] or "quota" not in msg["event"][outcome_id]:
                    self.updated_odd = 1
                    return

                self.updated_odd = msg["event"][outcome_id]["quota"]

    async def website_checker(self):
        # check if pay bet button is disabled
        await self.pay_bet_button.update()
        for attr in self.pay_bet_button.attributes:
            if "Button_disabled__dBLYL" in attr:
                self.updated_odd = 1
                return

        # check if odd element has class that indicate it's closed
        await self.website_checker_element.update()
        for attr in self.website_checker_element.attributes:
            if "ScommesseEsitoSkeleton_container___crym" in attr:
                self.updated_odd = 1
                return

        self.updated_odd = float(self.website_checker_element.children[0].text)

    def arb_finder(self):
        try:
            self.arb_finder_websocket_response_body[2][4][2]["data"]
        except:
            self.empty_wss_response_body = True
            return

        if self.tree is None:
            self.empty_events_tree = True
            return

        for msg in self.arb_finder_websocket_response_body[2][4][2]["data"]:
            if msg["message"] != "UpdateQuote":
                continue

            for outcome_id in msg["event"]:
                if outcome_id not in self.tree:
                    continue

                bet_type = self.tree[outcome_id]["bet_type"]
                outcome = self.tree[outcome_id]['outcome']
                bet_radar_id = self.tree[outcome_id]["bet_radar_id"]

                outcome_obj = Outcome(
                    outcome=outcome,
                    odd=1.0,
                    sportbook=self.name,
                    bet_id=self.tree[outcome_id]['bet_id'],
                    bet_type=bet_type,
                    sport=self.tree[outcome_id]['sport']
                )

                if "quota" in msg["event"][outcome_id] and msg["event"][outcome_id]["isActive"]:
                    outcome_obj.odd = float(msg["event"][outcome_id]["quota"])

                for event in self.events:
                    if event.bet_radar_id == bet_radar_id:
                        event.update_outcomes([outcome_obj])
                        break

    def make_tree(self):
        bet_radar_ids = {}
        info_by_br_id = {}
        outcomes_by_br_id = {}
        self.tree = {}
        self.events = []

        for event_obj in self.tree_response_body["avvenimentoList"]:
            # if not event_obj['isActive']: continue
            if "key" not in event_obj or 'live' not in event_obj or "betRadarMatchId" not in event_obj["live"] or event_obj["live"]["betRadarMatchId"] == 0 or event_obj["live"]["betRadarMatchId"] is None:
                continue

            sport = str(event_obj["slugDisciplina"].lower().strip())
            if sport == 'calcio':
                sport = 'football'
            elif sport == 'basket':
                sport = 'basketball'

            if sport != self.sport_to_use:
                continue

            try:
                period = int(event_obj["live"]["status"].split("°")[0])
            except:
                period = None

            try:
                time = int(event_obj["live"]["matchTime"].replace('-', "45"))
            except:
                time = None

            info = Info(
                sport=sport,
                name=event_obj["slugAvvenimento"],
                start=datetime.fromisoformat(f'{event_obj["dataOra"]}+02:00').timestamp(),
                period=period,
                time=time,
                score=(int(event_obj["live"]["score"]['firstCompetitor']), int(event_obj["live"]["score"]['secondCompetitor'])),
                status=event_obj["scommesseAttive"]
            )

            bet_radar_id = str(event_obj["live"]["betRadarMatchId"])
            bet_radar_ids[event_obj["key"]] = [bet_radar_id, sport]
            info_by_br_id[bet_radar_id] = info

        for outcome_id in self.tree_response_body["esitoMap"]:
            if "idProgramma" not in self.tree_response_body["esitoMap"][outcome_id] or "idAvvenimento" not in self.tree_response_body["esitoMap"][outcome_id]:
                continue

            key = f"{self.tree_response_body["esitoMap"][outcome_id]['idProgramma']}-{self.tree_response_body["esitoMap"][outcome_id]['idAvvenimento']}"
            if key not in bet_radar_ids:
                continue

            if not self.tree_response_body["esitoMap"][outcome_id]["isActive"]:
                continue

            match self.tree_response_body["esitoMap"][outcome_id]["descrizioneTipoScommessaWithInfoAgg"]:

                # football
                case "1X2 FINALE":  # 1X2: 1, X, 2
                    bet_type = "1X2"
                    outcome = self.tree_response_body["esitoMap"][outcome_id]["descrizione"]

                case "DOPPIA CHANCE IN":  # DC: 1X
                    if self.tree_response_body["esitoMap"][outcome_id]["descrizione"] != "1X": continue
                    bet_type = "DC"
                    outcome = self.tree_response_body["esitoMap"][outcome_id]["descrizione"]

                case "DOPPIA CHANCE OUT":  # DC: X2
                    if self.tree_response_body["esitoMap"][outcome_id]["descrizione"] != "X2": continue
                    bet_type = "DC"
                    outcome = self.tree_response_body["esitoMap"][outcome_id]["descrizione"]

                case "DOPPIA CHANCE IN/OUT":  # DC: 12
                    if self.tree_response_body["esitoMap"][outcome_id]["descrizione"] != "12": continue
                    bet_type = "DC"
                    outcome = self.tree_response_body["esitoMap"][outcome_id]["descrizione"]

                # tennis
                case "T/T MATCH (ESCL. RITIRO)":  # T/T: 1, 2
                    bet_type = "T/T"
                    outcome = self.tree_response_body["esitoMap"][outcome_id]["descrizione"]

                # basketball
                case "T/T MATCH":  # T/T: 1, 2
                    bet_type = "T/T"
                    outcome = self.tree_response_body["esitoMap"][outcome_id]["descrizione"]

                case _:
                    continue

            # make tree for websocket arb finder
            bet_radar_id = bet_radar_ids[key][0]
            sport = bet_radar_ids[key][1]
            self.tree[outcome_id] = {
                'sport': sport,
                "bet_radar_id": bet_radar_id,
                "bet_type": bet_type,
                "outcome": outcome,
                "bet_id": BetID(
                    bet_id=self.tree_response_body["esitoMap"][outcome_id]["key"]
                )
            }

            if bet_radar_id not in outcomes_by_br_id:
                outcomes_by_br_id[bet_radar_id] = []
            outcomes_by_br_id[bet_radar_id].append(
                Outcome(
                    odd=float(self.tree_response_body["esitoMap"][outcome_id]["quota"]),
                    outcome=outcome,
                    sportbook=self.name,
                    bet_id=BetID(
                        bet_id=self.tree_response_body["esitoMap"][outcome_id]["key"]
                    ),
                    bet_type=bet_type,
                    sport=sport,
                )
            )

        for bet_radar_id in outcomes_by_br_id:
            self.events.append(
                Event(
                    bet_radar_id=bet_radar_id,
                    outcomes=outcomes_by_br_id[bet_radar_id],
                    info=info_by_br_id[bet_radar_id],
                    sportbook=self.name,
                )
            )
