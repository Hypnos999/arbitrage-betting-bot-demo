from copy import deepcopy
from datetime import datetime
import time
from scripts.bots.bot import Bot
from scripts.bots.utils import write_input, click_element
from scripts.arbitrage.bet_id import BetID
from scripts.arbitrage.outcome import Outcome
from scripts.arbitrage.info import Info
from scripts.arbitrage.event import Event


class Betsson(Bot):
    """betsson"""  # DO NOT DELETE THIS

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def prep(self):
        await self.page.get(self.betting_urls[self.sport_to_use])
        await self.page
        await self.page.sleep(5)

        # delete bets
        # looks like when we change sport page the selected bets are deleted automatically
        try:
            delete_bets_btn = await self.page.select("button.buttons.button--icon_primary.button--small.button--icon-right.ng-star-inserted")
            await click_element(delete_bets_btn)
        except:
            pass

        await self.page.reload()  # realod is usefull as betsson has trouble tracking requests
        await self.page.sleep(10)

    async def place_bet(self):
        await self.page

        teams = await self.page.select_all(".match-row__match__headings__team__label")
        for team in teams:
            if team.text.lower().strip() not in self.bet.bet_id.teams:
                continue

            await click_element(team)
            await self.page
            await self.page.sleep(2)

            try:
                bet_containers = await self.page.select_all("div.card.card--expandable.card--expanded")
            except:
                raise Exception('There are no open bets for the current event')

            for bet_container in bet_containers:
                bet_type = bet_container.children[0].children[1].text.lower().strip()

                if bet_type != self.bet.bet_id.bet_type.lower().strip():
                    continue

                outcomes_container = await bet_container.query_selector_all('div.box-quota.box-quota--min1.ng-star-inserted')
                for outcome_container in outcomes_container:
                    outcome = outcome_container.children[0].text.lower().strip()
                    if outcome != self.bet.bet_id.outcome.lower().strip():
                        continue

                    self.website_checker_element = outcome_container

                    await click_element(outcome_container)
                    await self.page

                    amount_input = await self.page.select('input[name="cartAmount"]')
                    t = time.time()
                    while True:
                        await click_element(amount_input)
                        await write_input(str(int(self.bet.stake)), amount_input)
                        amount_input_value = await amount_input.apply("(el) => {el.dispatchEvent(new Event('keyup')); return el.value}")

                        if int(amount_input_value) == int(self.bet.stake):
                            await self.page
                            break

                        if t > 10:
                            raise Exception("Failed to write amount input")

                    self.pay_bet_button = await self.page.select('div.cart__buttons__others button.buttons.button--primary.button--medium.ng-star-inserted')
                    self.odd_value.value = float(outcome_container.children[3].text)
                    self.place_bet_success.value = int(True)
                    return

        raise Exception('Bet not found')

    def arb_checker(self):
        if self.arb_finder_http_response_body["ResponseData"] is None or self.arb_finder_http_response_body["ResponseData"]['ResultDelta'] is None:
            self.empty_http_response_body = True
            return

        for bet_obj in self.arb_finder_http_response_body["ResponseData"]["ResultDelta"]:
            # check sport is in the possible ones
            sport = bet_obj["Sport_Name"].lower()
            if sport == 'calcio':
                sport = 'footbaal'
            elif sport == 'basket':
                sport = 'basketball'

            if sport != self.sport_to_use:
                continue

            # get bet radar id
            bet_radar_id = bet_obj["Match_IdBetradar"]
            if isinstance(bet_radar_id, int) and bet_radar_id < 0:
                bet_radar_id = bet_radar_id * -1
            bet_radar_id = str(bet_radar_id).strip()

            if bet_radar_id != self.bet.bet_radar_id:
                continue

            bet_type = bet_obj["Type_Naming_Translate"]

            # football
            if bet_type.lower().strip() == "esito finale 1x2":
                bet_type = "1X2"
            elif bet_type.lower().strip() == "doppia chance":
                bet_type = "DC"
            elif bet_type.lower().strip() == "g/ng":
                bet_type = "GG/NG"

            # tennis
            elif sport == "tennis":
                if bet_type.lower().strip() == 't/t match (escl.ritiro)':
                    bet_type = 'T/T'

            # basketball
            elif sport == 'basketball':
                if bet_type.lower().strip() == 't/t risultato':
                    bet_type = 'T/T'

            else:
                continue

            if bet_type != self.bet.bet_type:
                continue

            outcome = bet_obj['Outcome']
            if outcome == "G": outcome = "GG"
            if outcome != self.bet.outcome:
                continue

            odd = bet_obj["QuotaAttuale"]
            self.updated_odd = odd

    async def website_checker(self):
        await self.website_checker_element.update()

        try:
            self.updated_odd = float(self.website_checker_element.children[3].text)
        except:
            self.updated_odd = 1

    def arb_finder(self):
        if self.tree is None:
            self.empty_events_tree = True
            return

        if self.arb_finder_http_response_body["ResponseData"] is None or self.arb_finder_http_response_body["ResponseData"]['ResultDelta'] is None:
            self.empty_http_response_body = True
            return

        if self.events is None:
            self.events = []

        outcomes = {}
        infos = {}
        for bet_obj in self.arb_finder_http_response_body["ResponseData"]["ResultDelta"]:
            if bet_obj["Bet_Stato"] == "chiuso":
                continue

            # check sport is in the possible ones
            sport = bet_obj["Sport_Name"].lower().strip()
            if sport == 'calcio':
                sport = 'football'
            elif sport == 'basket':
                sport = 'basketball'

            if sport != self.sport_to_use:
                continue

            bet_type = bet_obj["Type_Naming_Translate"]

            # football
            if sport == 'football':
                if bet_type.lower().strip() == "esito finale 1x2":
                    bet_type = "1X2"
                elif bet_type.lower().strip() == "doppia chance":
                    bet_type = "DC"
                elif bet_type.lower().strip() == "g/ng":
                    bet_type = "GG/NG"
                else:
                    continue

            # tennis
            elif sport == "tennis":
                if bet_type.lower().strip() == 't/t match (escl.ritiro)':
                    bet_type = 'T/T'
                else:
                    continue

            # basketball
            elif sport == 'basketball':
                if bet_type.lower().strip() == 't/t risultato':
                    bet_type = 'T/T'
                else:
                    continue

            else:
                continue

            outcome = bet_obj['Outcome']
            if outcome == "G":
                outcome = "GG"

            odd = float(bet_obj["QuotaAttuale"])

            home_team = bet_obj["Match_hteam"].lower().strip()
            away_team = bet_obj["Match_ateam"].lower().strip()
            if self.sport_to_use == 'tennis':
                home_team = home_team.replace(',', '')
                away_team = away_team.replace(',', '')

            bet_radar_id = bet_obj["Match_IdBetradar"]
            if isinstance(bet_radar_id, int) and bet_radar_id < 0:
                bet_radar_id = bet_radar_id*-1
            bet_radar_id = str(bet_radar_id).strip()

            outcome_obj = Outcome(
                odd=odd,
                outcome=outcome,
                sportbook=self.name,
                bet_id=BetID(
                    teams=[
                        home_team,
                        away_team
                    ],
                    bet_type=bet_obj["Type_Naming_Translate"].lower().strip(),
                    outcome=bet_obj['Outcome'].lower().strip(),
                ),
                bet_type=bet_type,
                sport=sport,
            )

            if bet_radar_id not in outcomes:
                outcomes[bet_radar_id] = []
            outcomes[bet_radar_id].append(outcome_obj)

            try:
                period = int(bet_obj["ScoreStatus"].replace("1° tempo", "1").replace("2° tempo", "2"))
            except:
                period = None

            try:
                time = int(bet_obj["ScoreMatchTime"])
            except:
                time = None

            try:
                score = tuple([int(s) for s in bet_obj["Score"].split(':')])
            except:
                score = None

            # get info about the match
            info = Info(
                status=True if bet_obj["Bet_Stato_Generale"].lower().strip() == "aperto" else False,
                score=score,  # "0:1" football / "0:1" tennis
                time=time,  # "47" ie for football / "0" for tennis
                period=period,  # "2 Tempo" football / "2 set" tennis
                name=f'{bet_obj["Match_hteam"].lower()} - {bet_obj["Match_ateam"]}',
                sport=sport,
                start=datetime.fromisoformat(f"{bet_obj["Match_Time"]}+02:00").timestamp(),
                tournament=bet_obj["MasterGroup_Name"],
                # tennis scoring has another info "GameScore" which is the current score for the game, the score we save is the one of the set, it may is also not right as it look like it always is either "1:0" or "0:1"
            )

            if bet_radar_id not in infos:
                infos[bet_radar_id] = info

        for bet_radar_id in infos:
            for i, event in enumerate(deepcopy(self.events)):
                if event.bet_radar_id == bet_radar_id:
                    for ot in event.outcomes:
                        outcome_overwritten = False

                        for ot2 in outcomes[bet_radar_id]:
                            if not (ot.bet_type == ot2.bet_type and ot.outcome == ot2.outcome):
                                outcome_overwritten = True

                        if not outcome_overwritten:
                            outcomes[bet_radar_id].append(ot)

                    self.events.pop(i)
                    break

            self.events.append(
                Event(
                    bet_radar_id,
                    outcomes[bet_radar_id],
                    infos[bet_radar_id],
                    self.name
                )
            )

    def make_tree(self):
        if self.tree_response_body['ResponseData'] is None:
            self.empty_tree_response_body = True
            return

        if self.tree_response_body['ResponseData']['IsDelta'] is True:
            self.wrong_tree_request = True
            return

        self.tree = {}
        self.events = []

        for sport_obj in self.tree_response_body["ResponseData"]["ResultGrouped"]['Sports']:
            sport = sport_obj["Sport_Name"].lower().strip()
            if sport == 'calcio':
                sport = 'football'
            elif sport == 'basket':
                sport = 'basketball'

            if sport != self.sport_to_use:
                continue

            for category_obj in sport_obj['Groups']:
                for event_obj in category_obj['Matches']:
                    # get bet radar id
                    bet_radar_id = int(event_obj["Id_Betradar"])
                    if bet_radar_id < 0:
                        bet_radar_id = bet_radar_id * -1
                    bet_radar_id = str(bet_radar_id).strip()

                    try:
                        period = event_obj["Score_Status"].replace("1° tempo", "1").replace("2° tempo", "2")
                        period = int(period)
                    except:
                        period = None

                    try:
                        time = int(event_obj["Score_MatchTime"])
                    except:
                        time = None

                    try:
                        score = tuple([int(s) for s in event_obj["Score"].split(':')])
                    except:
                        score = None

                    # get info about the match
                    info = Info(
                        name=f'{event_obj["Match_HTeam"].lower()} - {event_obj["Match_ATeam"]}',
                        sport=sport,
                        tournament=event_obj["Group_Name"],
                        start=datetime.fromisoformat(f"{event_obj["Match_Time"]}+02:00").timestamp(),
                        status=True if event_obj['Bet_StatoGenerale'].lower().strip() == "aperto" else False,
                        score=score,  # "0:1" football / "0:1" tennis
                        time=time,  # "47" ie for football / "0" for tennis
                        period=period,  # "2 Tempo" football / "2 set" tennis
                    )

                    outcomes = []
                    for bet_group_obj in event_obj['Bets']:
                        for bet_obj in bet_group_obj['Types']:
                            if bet_obj["Bet_Stato"] == "chiuso":
                                continue

                            bet_type = bet_obj["Type_Name"]

                            # football
                            if sport == 'football':
                                if bet_type.lower().strip() == "esito finale 1x2":
                                    bet_type = "1X2"
                                elif bet_type.lower().strip() == "doppia chance":
                                    bet_type = "DC"
                                elif bet_type.lower().strip() == "g/ng":
                                    bet_type = "GG/NG"
                                else:
                                    continue

                            # tennis
                            elif sport == 'tennis':
                                if bet_type.lower().strip() == 't/t match (escl.ritiro)':
                                    bet_type = 'T/T'
                                else:
                                    continue

                            # basketball
                            elif sport == 'basketball':
                                if bet_type.lower().strip() == 't/t risultato':
                                    bet_type = 'T/T'
                                else:
                                    continue

                            else:
                                continue

                            for outcome_obj in bet_obj['Outcomes']:

                                outcome = outcome_obj['Outcome']
                                if outcome == "G": outcome = "GG"

                                home_team = event_obj["Match_HTeam"].lower().strip()
                                away_team = event_obj["Match_ATeam"].lower().strip()
                                if self.sport_to_use == 'tennis':
                                    home_team = home_team.replace(',', '')
                                    away_team = away_team.replace(',', '')

                                outcomes.append(
                                    Outcome(
                                        odd=outcome_obj["Odd"],
                                        outcome=outcome,
                                        sportbook=self.name,
                                        bet_id=BetID(
                                            teams=[
                                                home_team,
                                                away_team
                                            ],
                                            bet_type=bet_obj["Type_Name"].lower().strip(),
                                            outcome=outcome_obj['Outcome'].lower().strip(),
                                        ),
                                        bet_type=bet_type,
                                        sport=sport,
                                    )
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
