from datetime import datetime
import time
from scripts.bots.utils import click_element, write_input
from scripts.bots.bot import Bot
from scripts.arbitrage.bet_id import BetID
from scripts.arbitrage.outcome import Outcome
from scripts.arbitrage.event import Event
from scripts.arbitrage.info import Info


class Sisal(Bot):
    """sisal"""  # DON'T REMOVE THIS
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def prep(self):
        await self.page.get(self.betting_urls[self.sport_to_use])
        await self.page.sleep(5)
    
        # click on close cookie btn
        try:
            cookies_button = await self.page.select('button.onetrust-close-btn-handler.onetrust-close-btn-ui.banner-close-button.ot-close-icon')
            await click_element(cookies_button)
            await self.page.sleep()
        except:
            pass
    
        # delete selected bets
        try:
            clean_bets_button = await self.page.select('button.clearTicketButton_button__hxaes')
            await click_element(clean_bets_button)
            await self.page.sleep()
        except:
            pass
    
        # open closed containers to load all games
        try:
            open_markets_buttons = await self.page.select_all('.icon-Arrow-Down.d-flex.ml-1')
            for btn in open_markets_buttons:
                await btn.apply("(el) => el.click()")
        except:
            pass

    async def place_bet(self):
        bet_el = await self.page.select(f'div[data-qa="{self.bet.bet_id.bet_id}"]')
        self.website_checker_element = bet_el

        # check if bet is closed
        for attr in bet_el.attributes:
            if 'selectionButton_disabled__r71Wu' in attr.split(' '):
                raise Exception('bet is closed')

        await click_element(bet_el)

        # insert amount to bet in amount input
        amount_input = await self.page.select('input.betInput_input__TfB7i')
        timer = time.time()
        while True:
            await click_element(amount_input)
            await write_input(str(int(self.bet.stake)), amount_input)

            if int(amount_input.attributes[-1].replace(',', '.')) == self.bet.stake:
                break

            if time.time() - timer > 10:
                raise Exception('amount input is not correct')

        self.pay_bet_button = await self.page.select("button[data-qa='biglietto_scommetti']")
        self.place_bet_success.value = int(True)
        self.odd_value.value = float(bet_el.children[0].text)

    def arb_checker(self):
        self.updated_odd = self.arb_checker_http_response_body[0]['odd'] / 100

    async def website_checker(self):
        # check if bet is closed
        await self.website_checker_element.update()
        for attr in self.website_checker_element.attributes:
            if 'selectionButton_disabled__r71Wu' in attr.split(' '):
                self.updated_odd = 1
                return

        self.updated_odd = float(self.website_checker_element.children[0].text)

    def arb_finder(self):
        self.events = []
        outcomes_by_br_id = {}
        info_by_br_id = {}

        for bet_group in self.arb_finder_http_response_body['infoAggiuntivaMap']:
            amd_code = "-".join(bet_group.split('-')[0:2])
    
            # this is needed for when parsing function is used for a single event
            k = 'avvenimentoFeMap'
            # if event is not present or there's no bet_radar_id
            if amd_code not in self.arb_finder_http_response_body['avvenimentoFeMap'] or not self.arb_finder_http_response_body['avvenimentoFeMap'][amd_code]['externalProviderInfoList']:
                continue
    
            match self.arb_finder_http_response_body['infoAggiuntivaMap'][bet_group]['descrizione'].strip():
                # football
                case 'GOAL/NOGOAL':
                    # GG/NG: GG, NG
                    sport = 'football'
                    bet_type = 'GG/NG'
                    outcomes = [
                        str(odds_obj['codiceEsitoAAMS'])
                        .replace('1', 'GG')
                        .replace('2', 'NG')
                        for odds_obj in self.arb_finder_http_response_body['infoAggiuntivaMap'][bet_group]['esitoList']
                    ]
    
                case 'ESITO FINALE 1X2':
                    # 1X2: 1, X, 2
                    sport = 'football'
                    bet_type = '1X2'
                    outcomes = [
                        str(odds_obj['codiceEsitoAAMS'])
                        .replace('1', '11')
                        .replace('2', 'XX')
                        .replace('3', '22')[0]
                        for odds_obj in self.arb_finder_http_response_body['infoAggiuntivaMap'][bet_group]['esitoList']
                        # we replaced like this and only took first string char
                        # to avoid possibles double replacements which would mess the outcomes
                    ]
    
                case 'DOPPIA CHANCE':
                    # DC: 1X, X2, 12
                    sport = 'football'
                    bet_type = 'DC'
                    outcomes = [
                        str(odds_obj['codiceEsitoAAMS'])
                        .replace('1', '1X')
                        .replace('2', 'X2')
                        .replace('3', '12')
                        for odds_obj in self.arb_finder_http_response_body['infoAggiuntivaMap'][bet_group]['esitoList']
                    ]
    
                # basketball
                case 'T/T RISULTATO':
                    # T/T: 1, 2
                    sport = 'basketball'
                    bet_type = 'T/T'
                    outcomes = [
                        str(odds_obj['codiceEsitoAAMS'])
                        for odds_obj in self.arb_finder_http_response_body['infoAggiuntivaMap'][bet_group]['esitoList']
                    ]
    
                case 'PARI/DISPARI BASKET':
                    # P/D: P, D
                    sport = 'basketball'
                    bet_type = 'P/D'
                    outcomes = [
                        str(odds_obj['codiceEsitoAAMS'])
                        .replace('1', 'P')
                        .replace('2', 'D')
                        for odds_obj in self.arb_finder_http_response_body['infoAggiuntivaMap'][bet_group]['esitoList']
                    ]
    
                # tennis
                case "T/T MATCH (ESCL. RITIRO)":
                    # T/T: 1, 2
                    sport = 'tennis'
                    bet_type = "T/T"
                    outcomes = [str(odds_obj['codiceEsitoAAMS']) for odds_obj in self.arb_finder_http_response_body['infoAggiuntivaMap'][bet_group]['esitoList']]
    
                case _:
                    continue
            
            if sport != self.sport_to_use:
                continue
    
            bet_radar_id = str(self.arb_finder_http_response_body[k][amd_code]['externalProviderInfoList'][0]['idAvvProviderLive'])
            if bet_radar_id not in outcomes_by_br_id:
                outcomes_by_br_id[bet_radar_id] = []

            for i in range(len(self.arb_finder_http_response_body['infoAggiuntivaMap'][bet_group]['esitoList'])):
                outcomes_by_br_id[bet_radar_id].append(
                    Outcome(
                        odd=self.arb_finder_http_response_body['infoAggiuntivaMap'][bet_group]['esitoList'][i]['quota'] / 100.0,
                        outcome=outcomes[i],
                        bet_id=BetID(
                            bet_id=f'esito_{bet_group.replace("-", "_")}_{self.arb_finder_http_response_body["infoAggiuntivaMap"][bet_group]["esitoList"][i]["codiceEsitoAAMS"]}',
                        ),
                        sportbook=self.name,
                        bet_type=bet_type,
                        sport=sport,
                    )
                )

            try:
                period = self.arb_finder_http_response_body[k][amd_code]['livescore']['statusDescription'].split("°")[0]
                period = int(period)
            except:
                period = None

            info = {
                'sport': sport,
                'name': self.arb_finder_http_response_body[k][amd_code]['descrizione'],
                'start': datetime.fromisoformat(self.arb_finder_http_response_body[k][amd_code]['data']).timestamp(),
                'period': period
            }
    
            try:
                # info['period'] = int(self.arb_finder_http_response_body[k][amd_code]['livescore']['statusDescription'])
                info['score'] = [tuple([int(obj['team1']), int(obj['team2'])]) for obj in self.arb_finder_http_response_body[k][amd_code]['livescore']['scoreList']]

                if len(info['score']) == 0:
                    info.pop('score')
                elif len(info['score']) == 1:
                    info['score'] = info['score'][0]
            except:
                pass

            if bet_radar_id not in info_by_br_id:
                info_by_br_id[bet_radar_id] = Info(**info)

        for bet_radar_id in outcomes_by_br_id:
            self.events.append(
                Event(
                    bet_radar_id=bet_radar_id,
                    info=info_by_br_id[bet_radar_id],
                    outcomes=outcomes_by_br_id[bet_radar_id],
                    sportbook=self.name
                )
            )
