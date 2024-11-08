from scripts.functions import get_logger
from scripts.arbitrage.bet import Bet
from scripts.arbitrage.event import Event
from scripts.config import Config
from scripts.bots.utils import click_element
import base64
import msgpack
from nodriver import Tab, Element, cdp, start
from multiprocessing import Event as Event_MP, Value, Queue
import json
import pickle
import time
import asyncio

try:
    import uvloop # type: ignore
except:
    pass


class BotBedrock:

    def __init__(
        self,
        name: str,
        browser_port: int,

        finished_prep: Event_MP,
        finished_place_bet: Event_MP,
        finished_pay_bet: Event_MP,
        wait_for_prep: Event_MP,
        wait_for_arb: Event_MP,
        wait_for_place_bets: Event_MP,
        wait_for_pay_bets: Event_MP,

        all_prep_success: Value,

        prep_success: Value,
        place_bet_succes: Value,

        odd_value: Value,
        final_check: Value,

        data_queue: Queue,
        bets_queue: Queue,
        logs_queue: Queue,
    ):
        self.name = name
        self.browser_port = browser_port

        self.finished_prep = finished_prep
        self.finished_place_bet = finished_place_bet
        self.finished_pay_bet = finished_pay_bet
        
        self.wait_for_prep = wait_for_prep
        self.wait_for_arb = wait_for_arb
        self.wait_for_place_bets = wait_for_place_bets
        self.wait_for_pay_bets = wait_for_pay_bets

        self.all_prep_success = all_prep_success

        self.prep_success = prep_success
        self.place_bet_success = place_bet_succes
        self.odd_value = odd_value
        self.updated_odd = None
        self.final_check = final_check

        self.data_queue = data_queue
        self.bets_queue = bets_queue
        self.logs_queue = logs_queue

        config = Config()
        self.sport_to_use = config.sport_to_use
        self.results_path = config.results_path
        self.images_path = config.images_path

        # these variables will be used later in the functions that will be overwritten or in process()
        self.arb_finder_http_response_body: dict | None = None
        self.arb_finder_websocket_response_body: dict | list | None = None
        self.arb_finder_request_ids: list[cdp.network.RequestId] = []
        self.arb_finder_http_response_ids: list[cdp.network.RequestId] = []
        self.arb_finder_websocket_responses: list[dict | list] = []  # used for websocket

        self.arb_checker_http_response_body: dict | None = None
        self.arb_checker_websocket_response_body: dict | list | None = None
        self.arb_checker_request_ids: list[cdp.network.RequestId] = []
        self.arb_checker_http_response_ids: list[cdp.network.RequestId] = []
        self.arb_checker_websocket_responses: list[dict | list] = []

        self.tree_response_body: dict | None = None
        self.tree_request_ids: list[cdp.network.RequestId] = []
        self.tree_response_ids: list[cdp.network.RequestId] = []

        self.pay_bet_button: Element | None = None
        self.website_checker_element: Element | None = None  # used by arb_checker() to check if bet is closed
        self.events = None
        self.tree_initialized = False
        self.tree: dict | None = None
        self.page: Tab | None = None
        self.bet: Bet | bool = False

        # used to avoid empty requests or wrong ones
        # as some websites uses the same url for tree and arb_finder requests
        self.empty_http_response_body = False
        self.empty_events_tree = False
        self.empty_tree_response_body = False
        self.wrong_tree_request = False
        self.empty_wss_response_body = False

        # run stats
        self.logout_time = False
        self.login_time = False
        self.prep_time = False
        self.place_bet_time = False
        self.pay_bet_time = False
        self.odd_average: list | bool = False

        # logger setup
        self.logger = get_logger(name, f'{config.logs_path}{name}.log')
        self.logger.info("")
        self.logger.info("")
        self.logger.info(f'Started {name.capitalize()} process')

        # load needed files
        with open(config.links_path, 'r') as f:
            data = json.loads(f.read())

            self.betting_urls = data[name]['betting-urls']
            self.arb_finder_urls = data[name]['arb-finder-urls']
            self.arb_checker_urls = data[name]['arb-checker-urls']
            self.login_url = None  # used to go directly to login page without interacting with the website
            self.tree_request_url = None  # used to make a tree of results that will be updated or used to connect results data

            if 'login-url' in data[name]:
                self.login_url = data[name]['login-url']
            if 'event-tree-request-url' in data[name]:
                self.tree_request_url = data[name]['event-tree-request-url']

        self.logger.info("Loaded data")

    @property
    def events(self):
        return self._events

    @events.setter
    def events(self, value: list[Event] | None):
        if not isinstance(value, list) and value is not None:
            raise ValueError('events must be a list or None')

        if value is not None:
            for e in value:
                if not isinstance(e, Event):
                    raise ValueError("events must be a list of Event")

        self._events = value

    @property
    def bet(self):
        return self._bet

    @bet.setter
    def bet(self, value: Bet | bool):
        if not isinstance(value, (Bet, bool)):
            raise ValueError(f'bet must be a Bet or bool: {value}')

        self._bet = value

    @property
    def pay_bet_button(self):
        return self._pay_bet_button

    @pay_bet_button.setter
    def pay_bet_button(self, value: Element | None):
        if not isinstance(value, (Element, type(None))):
            raise ValueError(f'pay_bet_button must be a Element or None: {value}')

        self._pay_bet_button = value

    @property
    def website_checker_element(self):
        return self._website_checker_element

    @website_checker_element.setter
    def website_checker_element(self, value: Element | None):
        if not isinstance(value, (Element, type(None))):
            raise ValueError(f'pay_bet_button must be a Element or None: {value}')

        self._website_checker_element = value

    def write_events(self):
        if self.events is None or len(self.events) == 0:
            return

        with open(f'{self.results_path}{self.name}_events.json', 'w') as f:
            f.write(json.dumps([e.to_dict() for e in self.events], indent=2))

    async def connect_to_browser(self):
        # initialize nodriver
        browser = await start(host='127.0.0.1', port=self.browser_port)
        await browser
        await browser.sleep(2)

        self.page = await browser.get(self.betting_urls[self.sport_to_use], new_window=True)
        await self.page()
        await self.page.sleep(5)
        self.logger.info('Initialized Nodriver instance')

        # network monitor part
        await self.page.send(cdp.network.enable())
        self.page.add_handler(cdp.network.RequestWillBeSent, lambda event: self.request_handler(event))
        self.page.add_handler(cdp.network.LoadingFinished, lambda event: self.response_handler(event))
        self.page.add_handler(cdp.network.WebSocketCreated, lambda event: self.websocket_creation_handler(event))
        self.page.add_handler(cdp.network.WebSocketFrameReceived, lambda event: self.websocket_message_handler(event))

        # wait for pgae to load
        timer = time.time()
        while True:
            if time.time() - timer > 60:
                raise Exception('Failed to connect to browser')

            try:
                await self.page.select('body', timeout=20)
                break
            except:
                pass

        await self.page.maximize()
        await self.page

    async def tree_maker(self):
        while self.tree_response_ids:
            await self.page

            tree_response_id = self.tree_response_ids[-1]
            self.tree_response_ids = self.tree_response_ids[self.tree_response_ids.index(tree_response_id) + 1:]
            # tree_response_id = self.tree_response_ids.pop(0)  # this doesn't work for snai

            response = await self.page.send(cdp.network.get_response_body(tree_response_id))
            if response is None:
                await self.page.send(cdp.network.replay_xhr(tree_response_id))  # this doesn't really do anything
                continue

            try:
                self.tree_response_body = json.loads(response[0])
            except:
                # self.logger.info(f"Tree request {tree_response_id}: response is null")
                continue

            if self.tree_response_body:
                self.make_tree()

                if self.empty_tree_response_body:
                    self.empty_tree_response_body = False
                    # self.logger.info(f"Tree request {tree_response_id}: response is empty")  # there is a response json but it doens't have data in it

                elif self.wrong_tree_request:  # some website have the same url for arb finder and tree
                    self.wrong_tree_request = False

                else:
                    # send results to main
                    self.data_queue.put(pickle.dumps({self.name: [e.to_dict() for e in self.events]}))
                    self.logger.info(f"Tree request {tree_response_id}: created tree and found n.{len(self.events)} events")  # there is a response json but it doens't have data in it
                    self.tree_initialized = True

                    # if self.tree is not None:
                    #     with open(f'files/results/tree_{self.name}.json', 'w') as f:
                    #         f.write(json.dumps(self.tree, indent=2))

    async def arb_finder_http(self):
        while self.arb_finder_http_response_ids:  # http responses
            if self.wait_for_arb.is_set():  # avoid that replay of xhr keep the loop running infinately
                break

            await self.page

            # response_id = self.arb_finder_http_response_ids[-1]
            # self.arb_finder_http_response_ids = self.arb_finder_http_response_ids[self.arb_finder_http_response_ids.index(response_id) + 1:]
            # with [-1] websites like vincitu which only have odds thatt changes could lead to errors
            # for example if odd starts at 4, then goes to 2 and then down to 1.5:
            #  - iterating with [-1] we would have 2 has final odd value
            #  - iterating with [0] we would have 1.5 has final odd value [correct]
            # or if not this we could lose some odd variations as we discard the older requests [see how self.arb_cheecker_https_response_ids was sliced]

            response_id = self.arb_finder_http_response_ids.pop(0)
            response = await self.page.send(cdp.network.get_response_body(response_id))
            if response is None:
                continue

            try:
                self.arb_finder_http_response_body = json.loads(response[0])
            except:
                # self.logger.info(f"Arb finder request {response_id}: response is null")
                continue

            old_events = 0 if self.events is None else len(self.events)
            self.arb_finder()

            if self.events is not None:
                self.data_queue.put(pickle.dumps({self.name: [e.to_dict() for e in self.events]}))

                if len(self.events) != old_events or self.tree_initialized:
                    self.logger.info(f"Arb finder request {response_id}: found n.{len(self.events)} events")
                    self.tree_initialized = False
                    # self.write_events()

            # if the response didn't have content --> don't send results to main.py
            if self.empty_http_response_body:
                self.empty_http_response_body = False
                # self.logger.info(f"Arb finder request {response_id}: is not empty but it doesn't have data in it.")

            elif self.empty_events_tree:
                self.empty_events_tree = False
                # self.logger.info(f"Arb finder request {response_id}: is not empty but the events tree is not yet initialized.")

    async def arb_finder_wss(self):
        while self.arb_finder_websocket_responses:
            # with websocket we take the element from the start of the list since they are updates of the tree
            # taking only the last one like in http request would not make sense
            self.arb_finder_websocket_response_body = self.arb_finder_websocket_responses.pop(0)

            old_events = 0 if self.events is None else len(self.events)
            self.arb_finder()

            if self.events is not None:
                self.data_queue.put(pickle.dumps({self.name: [e.to_dict() for e in self.events]}))

                if len(self.events) != old_events or self.tree_initialized:
                    self.logger.info(f"Arb finder websocket frame: found n.{len(self.events)} events")
                    self.tree_initialized = False
                    # self.write_events()

            if self.empty_wss_response_body:
                self.empty_wss_response_body = False
                # self.logger.info('Arb finder websocket frame: is not empty but it doesn\'t have data in it')

            elif self.empty_events_tree:
                self.empty_events_tree = False
                # self.logger.info(f"Arb finder websocket frame: is not empty but the events tree is not yet initialized.")

    async def arb_checker_http(self):
        while self.arb_checker_http_response_ids:
            # response_id = self.arb_checker_http_response_ids[-1]
            # self.arb_checker_http_response_ids = self.arb_checker_http_response_ids[self.arb_checker_http_response_ids.index(response_id) + 1:]
            # this could lead to errors, see arb_finder_http

            response_id = self.arb_checker_http_response_ids.pop(0)
            response = await self.page.send(cdp.network.get_response_body(response_id))
            if response is None:
                continue

            self.arb_checker_http_response_body = json.loads(response[0])
            self.arb_checker()

            if self.empty_http_response_body:
                self.empty_http_response_body = False
                self.logger.info(f"Arb checker http request: is not empty but it doens\'t have data in it")

    def arb_checker_wss(self):
        while self.arb_checker_websocket_responses:
            self.arb_checker_websocket_response_body = self.arb_checker_websocket_responses.pop(0)
            self.arb_checker()

            if self.empty_wss_response_body:
                self.empty_wss_response_body = False
                self.logger.info(f"Arb checker websocket frame: is not empty but it doesn\'t have data in it")

    def request_handler(self, event: cdp.network.RequestWillBeSent) -> None:
        if self.tree_request_url is not None and (
                event.request.url == self.tree_request_url or self.tree_request_url in event.request.url):
            self.tree_request_ids.append(event.request_id)

        if isinstance(self.arb_finder_urls[self.sport_to_use], str):
            urls = [self.arb_finder_urls[self.sport_to_use]]
        else:
            urls = self.arb_finder_urls[self.sport_to_use]

        for url in urls:
            if url == event.request.url or url in event.request.url:
                self.arb_finder_request_ids.append(event.request_id)

        if isinstance(self.arb_checker_urls[self.sport_to_use], str):
            urls = [self.arb_checker_urls[self.sport_to_use]]
        else:
            urls = self.arb_checker_urls[self.sport_to_use]

        for url in urls:
            if url == event.request.url or url in event.request.url:
                self.arb_checker_request_ids.append(event.request_id)

    def response_handler(self, event: cdp.network.LoadingFinished) -> None:
        if event.request_id in self.tree_request_ids:
            self.tree_response_ids.append(event.request_id)

        if event.request_id in self.arb_finder_request_ids:
            self.arb_finder_http_response_ids.append(event.request_id)

        if event.request_id in self.arb_checker_request_ids:
            self.arb_checker_http_response_ids.append(event.request_id)

    def websocket_creation_handler(self, event: cdp.network.WebSocketCreated):
        if isinstance(self.arb_finder_urls[self.sport_to_use], str):
            urls = [self.arb_finder_urls[self.sport_to_use]]
        else:
            urls = self.arb_finder_urls[self.sport_to_use]

        for url in urls:
            if url == event.url or url in event.url:
                self.arb_finder_request_ids.append(event.request_id)

        if isinstance(self.arb_checker_urls[self.sport_to_use], str):
            urls = [self.arb_checker_urls[self.sport_to_use]]
        else:
            urls = self.arb_checker_urls[self.sport_to_use]

        for url in urls:
            if url == event.url or url in event.url:
                self.arb_checker_request_ids.append(event.request_id)

    def websocket_message_handler(self, event: cdp.network.WebSocketFrameReceived):
        def unpack_multiple_messages(data):
            unpacker = msgpack.Unpacker()
            unpacker.feed(data)
            messages = []
            for message in unpacker:
                messages.append(message)
            return messages

        try:
            decoded_messages = unpack_multiple_messages(base64.b64decode(event.response.payload_data))
            if not decoded_messages: return

            if event.request_id in self.arb_finder_request_ids:
                self.arb_finder_websocket_responses.append(decoded_messages)
            if event.request_id in self.arb_checker_request_ids:
                self.arb_checker_websocket_responses.append(decoded_messages)

        except:
            pass

    def log(self):
        self.odd_average = False
        self.logs_queue.put(pickle.dumps(
            {
                self.name: {
                    'prep_succes': bool(self.prep_success.value),
                    'prep_time': self.prep_time,
                    'place_bet_succes': bool(self.place_bet_success.value),
                    'place_bet_time': self.place_bet_time,
                    'events': False if self.events is None else len(self.events),
                    'odd_average': self.odd_average,
                    'bet': self.bet if self.bet is False or self.bet is None else self.bet.to_dict(),
                    'odd_value': round(self.odd_value.value, 2),
                    'final_check': bool(self.final_check.value)
                }
            }
        ))

        self.logger.info('Sended log to main process')

    async def logout(self, *args, **kwargs):
        raise Exception("Logout fn has not been overriden")

    async def login(self, *args, **kwargs):
        raise Exception("Login fn has not been overriden")

    async def prep(self, *args, **kwargs):
        raise Exception("Prep fn has not been overriden")

    async def place_bet(self, *args, **kwargs):
        raise Exception("Place bet fn has not been overriden")

    def make_tree(self, *args, **kwargs):
        raise Exception("Make tree fn has not been overriden")

    def arb_finder(self, *args, **kwargs):
        raise Exception("Arb finder fn has not been overriden")

    def arb_checker(self, *args, **kwargs):
        raise Exception("Arb checker fn has not been overriden")

    async def website_checker(self):
        raise Exception("Website checker fn has not been overriden")

    async def fake_pay_bet(self):
        # used for demo porpuses
        for _ in range(50):
            await self.page.sleep(0.25)
            await self.pay_bet_button.flash()

    @classmethod
    def run(
            cls,
            *args
    ) -> None:
        """method to run a website with multiprocessing.Process"""
        instance = cls(*args)

        _uvloop = False
        try:
            uvloop.install()
            _uvloop = True
        except:
            pass

        if _uvloop:
            uvloop.run(instance.process())
        else:
            asyncio.run(instance.process())
