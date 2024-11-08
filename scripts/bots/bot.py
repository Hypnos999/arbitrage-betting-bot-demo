import time
import json
import pickle
import asyncio
import sys
from scripts.bots.bot_bedrock import BotBedrock
from scripts.arbitrage.bet import Bet


class Bot(BotBedrock):

    def __init__(
        self,
        *args,
        **kwargs
    ):
        super().__init__(*args, **kwargs)

    async def process(self):
        try:
            await self.connect_to_browser()

            # prep
            await self.page
            timer = time.time()
            await self.prep()
            self.prep_time = time.time() - timer
            self.prep_success.value = int(True)
            self.logger.info(f'Finished running prep() function process in {round(self.prep_time, 2)}s')
            # self.logger.info(f'Balance retrieved is {round(self.balance.value, 2)} €')

            self.finished_prep.set()  # send finished signal
            self.wait_for_prep.wait()  # wait for all websites to finish prep

            if bool(self.all_prep_success) is False:
                raise Exception('Some website failed to run prep() function')

            # this is usefull if some resources didn't load correctly
            await self.page
            await self.page.reload()
            await self.page.sleep(10)
            await self.page

            # start listening for odds data
            self.logger.info('Receiving/updating odds data...')
            timer = time.time()
            old_events = 0
            while True:
                await self.page  # without this it doesn't work

                if self.wait_for_arb.is_set():  # receive signal from main that an arb has been found
                    break

                if self.events is not None and len(self.events) != old_events:
                    self.write_events()
                    old_events = len(self.events)

                await self.tree_maker()

                await self.arb_finder_http()
                await self.arb_finder_wss()

                if time.time() - timer > 60 and self.events is None:
                    await self.page.reload()
                    await self.page.sleep(10)
                    await self.page.select("body")
                    timer = time.time()

            # receive bet
            self.logger.info("Waiting for bets")
            bets_json: list[dict] = pickle.loads(self.bets_queue.get())

            # check if website is included in a bet
            try:
                bet_json = [b for b in bets_json if b['sportbook'] == self.name][0]
                self.logger.info('Received bet:')
                self.logger.info(json.dumps(bet_json, indent=2))
            except:
                bet_json = False
                self.logger.info('Received bet: False')

            if bet_json is False:
                raise Exception('No bet found for this website')

            self.bet = Bet.from_dict(bet_json)

            # run place_bet function & send finished signal
            await self.page
            timer = time.time()
            try:
                await self.place_bet()
            except Exception as e:
                await self.page.save_screenshot(f"{self.images_path}failed_to_place_bet_{self.name}_{time.time()}.jpeg")
                self.logger.error("error raised in place_bet:")
                self.logger.exception(e)
                self.place_bet_success.value = int(False)
                
            
            if not bool(self.place_bet_success.value):
                self.pay_bet_button = None
                self.odd_value.value = 1.0
                self.finished_place_bet.set()  # send finished signal
            elif self.pay_bet_button is None:
                raise Exception('pay_bet_button not found')

            self.place_bet_time = time.time() - timer
            self.logger.info(f'Finished running place_bet() function in {round(self.place_bet_time, 2)}s, result: {bool(self.place_bet_success.value)}, odd value: {round(self.odd_value.value, 2)}')

            # while waiting for other websites to finish check if odd is still good (open and with more ore less same odd)
            while bool(self.place_bet_success.value) and self.pay_bet_button is not None:
                await self.page
                old_value = round(self.odd_value.value, 2)

                await self.website_checker()
                after_website_check = self.updated_odd
                if after_website_check is not None:
                    self.logger.info(f'Odd value detected by website_checker: {after_website_check}')

                await self.arb_checker_http()
                self.arb_checker_wss()
                after_arb_check = self.updated_odd
                if after_arb_check is not None:
                    self.logger.info(f"Odd value detected by arb_checker: {after_arb_check}")

                if after_arb_check is not None or after_website_check is not None:
                    min_value = min(e for e in [after_arb_check, after_website_check] if e is not None)  # usefull in case website_checker() detect a higher odd_value
                    if min_value < old_value:
                        self.logger.info(f'Odd value update has been registred: {old_value} --> {min_value}')
                        self.logger.info("")
                        self.odd_value.value = min_value
                        self.updated_odd = min_value
                    else:
                        self.logger.info(f'Odd value update has not been registred as it is a positive increase')  #: {old_value} --> {min_value}')
                        self.updated_odd = old_value

                if not self.finished_place_bet.is_set():
                    self.finished_place_bet.set()

                # if all websites have finished placing bets: break
                if self.wait_for_place_bets.is_set():
                    break

            # send check to main and get general check (True if only all checks are True)
            check = bool(self.final_check.value)
            self.logger.info(f'Final check: {check}')

            if check:
                await self.page
                timer = time.time()
                await self.fake_pay_bet()
                self.pay_bet_time = time.time() - timer
                self.logger.info(f'Finished pay_bet process in {round(self.logout_time, 2)}s')

                self.finished_pay_bet.set()
                self.wait_for_pay_bets.wait()
                
            # closing website page
            self.logger.info("Closing website tab")
            await self.page
            await self.page.close()

            self.write_events()
            self.log()

            self.logger.info('Closing process')
            sys.exit()

        except Exception as e:
            self.logger.exception(e)

            if str(e).lower() != "no bet found for this website":
                try:
                    await self.page
                    await self.page.save_screenshot(f"{self.images_path}{str(e)}_{self.name}_{time.time()}.jpeg")
                    self.logger.info("Saving a screenshot of website tab")
                except:
                    pass

            try:
                await self.page
                await self.page.close()
                self.logger.info("Closed website tab")
            except:
                pass

            self.write_events()
            self.log()

            self.logger.info('Closing process')
            sys.exit()
