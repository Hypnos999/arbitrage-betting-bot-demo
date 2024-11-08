from scripts.arbitrage.arb import Arb
from scripts.arbitrage.event import Event
from scripts.arbitrage.highest_odds import HighestOdds
from scripts.bots.websites.better import Better
from scripts.bots.websites.vincitu import Vincitu
from scripts.bots.websites.sisal import Sisal
from scripts.bots.websites.snai import Snai
from scripts.bots.websites.eurobet import Eurobet
from scripts.bots.websites.betflag import Betflag
from scripts.bots.websites.betsson import Betsson
from scripts.search_for_arb import run as find_arb
from scripts.config import Config
from scripts.functions import get_logger, get_websites_log
import psutil
import time
import json
from multiprocessing import Process, Event as Event_MP, Queue, Value
import os
from nodriver import start
import pickle
import shutil
import asyncio

try:
    import uvloop # type: ignore
except:
    pass


async def main(app_runner: str):
    # load files & config
    config = Config()

    # clean directory from the old run files
    for directory in [config.logs_path, config.images_path, config.results_path]:
        for filename in os.listdir(directory):
            file_path = os.path.join(directory, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except:
                pass
                # print(f'Failed to delete {file_path}. Reason: {e}')

    # logger setup
    logger = get_logger("main", f'{config.logs_path}main.log', console=True)
    logger.info(f'Started application with {app_runner}')
    logger.info('Loaded needed files and cleaned logs')
    logger.info(f'Config: \n{json.dumps(config.to_json(), indent=2)}\n')

    main_loop = True
    while main_loop:
        main_timer = time.time()

        browser = await start(
            browser_executable_path=config.browser_executable_path,
            user_data_dir=config.browser_user_data_dir,
            sandbox=True,

        )
        browser_port = browser.config.port

        # start nodriver browser
        processes: list[Process] = []
        signals: dict[str: Event_MP] = {}
        websites_place_bet_success: dict[str: Value] = {}
        websites_prep_success: dict[str: Value] = {}
        websites_balances: dict[str: Value] = {}
        websites_odd_value: dict[str: Value] = {}
        wait_for_prep = Event_MP()
        wait_for_arb = Event_MP()
        wait_for_place_bets = Event_MP()
        wait_for_pay_bets = Event_MP()
        data_queue = Queue()
        bets_queue = Queue()
        logs_queue = Queue()
        final_check = Value('i', int(False))
        mp_all_prep_success = Value('i', int(False))
        bots = [Vincitu, Better, Sisal, Snai, Eurobet, Betflag, Betsson]
        
        logger.info(f'Initializing nodrivers processes')
        for website in config.website_to_use:
            signals[website] = {
                "finished_logout": Event_MP(),
                "finished_login": Event_MP(),
                "finished_prep": Event_MP(),
                "finished_place_bet": Event_MP(),
                "finished_pay_bet": Event_MP(),
            }
            websites_place_bet_success[website] = Value('i', int(False))  # 0 False, 1 True
            websites_prep_success[website] = Value('i', int(False))
            websites_balances[website] = Value('f', 0.0)
            websites_odd_value[website] = Value('f', 1.0)

            args = (
                website,
                browser_port,

                signals[website]["finished_prep"],
                signals[website]["finished_place_bet"],
                signals[website]["finished_pay_bet"],
                wait_for_prep,
                wait_for_arb,
                wait_for_place_bets,
                wait_for_pay_bets,

                mp_all_prep_success,

                websites_prep_success[website],
                websites_place_bet_success[website],

                websites_odd_value[website],
                final_check,

                data_queue,
                bets_queue,
                logs_queue,
            )

            # for b in bots:
            #     print(b.__doc__)
            bot = [b for b in bots if b.__doc__ == website][0]
            p = Process(target=bot.run, args=args, daemon=True, name=bot.__doc__)
            p.start()

            processes.append(p)
            await browser.sleep()

        await browser.sleep(5)
        await browser.tabs[0].close()  # close empty tab
        await browser

        # wait for websites to finish preparation
        logger.info(f'Waiting for websites to finish prep() function')
        for websie in signals:
            signals[websie]["finished_prep"].wait(timeout=config.website_timeout)

        # check if all websites finished prep function
        websites_prep_success_set = set(map(lambda x: bool(x.value), websites_prep_success.values()))
        all_prep_success = len(websites_prep_success_set) == 1 and list(websites_prep_success_set)[0]
        mp_all_prep_success.value = int(all_prep_success)
        wait_for_prep.set()

        if all_prep_success is False:
            # things to do to make the websites process continue and finish on their own
            wait_for_arb.set()
            for _ in config.website_to_use:
                bets_queue.put(pickle.dumps({}))

            for website in websites_prep_success:
                if bool(websites_prep_success[website].value) is False:
                    logger.info(f'Website {website} failed to finish prep() function in the selected timeout of {config.website_timeout / 60} min.')
            logger.info("Restarting the process since some website/s didn't finished prep() func")

        else:
            logger.info("Starting main loop")
            arb_timer = time.time()
            last_events = 0

            arb: Arb | None = None
            events: dict[str: list[Event]] = {}
            while True:
                result = find_arb(data_queue, events, config)
                if result is False:
                    continue

                events: dict[str: list[Event]] = result[0]
                highest_odds: list[HighestOdds] = result[1]
                if len(events) != last_events or len(result) > 2:  # so that it write events that generates arb
                    logger.info(f"Found: n.{len(events)} events")
                    last_events = len(events)

                    with open(f'{config.results_path}events.json', 'w') as f:
                        f.write(json.dumps([[e.to_dict() for e in events[brid]] for brid in events], indent=2))

                    with open(f'{config.results_path}highest_odds.json', 'w') as f:
                        f.write(json.dumps([h.to_dict() for h in highest_odds], indent=2))

                if len(result) > 2:
                    arbs: list[Arb] = result[2]
                    logger.info(f"Found: n.{len(arbs)} arbs")

                    with open(f'{config.results_path}arbs.json', 'w') as f:
                        f.write(json.dumps([a.to_dict() for a in arbs], indent=2))

                if len(result) > 3:
                    arb: Arb = result[3]
                    logger.info(f"Selected an arb with implied probability of {round(arb.probability*100, 2)}%, total stake: {sum([b.stake for b in arb.bets])}.00 €, ~win: {round(sum([b.win for b in arb.bets]) / len(arb.bets), 2)} €")
                    # logger.info(json.dumps(arb.to_dict(), indent=2))

                    with open(f'{config.results_path}arb.json', 'w') as f:
                        f.write(json.dumps(arb.to_dict(), indent=2))

                    break

                # check if too much time has passed without finding arbs
                if time.time() - arb_timer > config.restart_time:
                    # return False
                    break

            wait_for_arb.set()

            if isinstance(arb, Arb):
                logger.info(f'Arb: {json.dumps(arb.to_dict(), indent=2)}')
                # send bets to (all) websites
                for _ in config.website_to_use:
                    bets_queue.put(pickle.dumps([b.to_dict() for b in arb.bets]))

                # wait for all websites to place bets
                logger.info("Waiting for websites to place bets")
                for bet in arb.bets:
                    signals[bet.sportbook]["finished_place_bet"].wait(timeout=config.website_timeout)

                # proceed to pay bet only if all websites could find the bet and the check for arb is True
                websites_place_bet_success = {k: bool(v.value) for k, v in websites_place_bet_success.items() if k in [b.sportbook for b in arb.bets]}
                logger.info(f"Websites place_bet() succes run: {json.dumps(websites_place_bet_success, indent=2)}")

                websites_odd_value = [v.value for k, v in websites_odd_value.items() if k in [b.sportbook for b in arb.bets]]
                logger.info(f"Updated odds value: {websites_odd_value}")

                probability = sum([1/odd if odd > 0 else 1 for odd in websites_odd_value])
                logger.info(f"The updated value of arb's implied probability is {probability}")

                if config.probability_treshold[0] < probability < config.probability_treshold[1] and all(websites_place_bet_success.values()):
                    final_check.value = int(True)
                else:
                    final_check.value = int(False)
                logger.info(f'Final check: {bool(final_check.value)}')
                
                wait_for_place_bets.set()  # make website stop checking arb and procede to either pay the bet or close

                if bool(final_check.value):
                    for bet in arb.bets:
                        signals[bet.sportbook]["finished_pay_bet"].wait(timeout=config.website_timeout)
                    
                    wait_for_pay_bets.set()    
                    
                    try:
                        # write results
                        with open(f'{config.results_path}events.json', 'w') as f:
                            f.write(json.dumps([[e.to_dict() for e in events[brid]] for brid in events], indent=2))

                        with open(f'{config.results_path}arb.json', 'w') as f:
                            f.write(json.dumps(arb.to_dict(), indent=2))
                    except:
                        logger.info('Couldn\'t write results')
                    

                    # make sure the loop doesn't restart
                    main_loop = False
                    input('Confirm exit, press ENTER: ')

                else:
                    # means either the bet is no more good or some websites failed to run place_bet()
                    logger.info("Restarting the process since the bet final check is negative")
            else:
                # means too much time has passed, restarting the websites processes
                logger.info("Restarting the process since to much time has passed while searching for an arb")

                # send empty bets to (all) websites
                for _ in config.website_to_use:
                    bets_queue.put(pickle.dumps([{}]))

        # make sure to kill websites processes and release their resources
        all_process_closed = True
        for process in processes:
            if process.is_alive():
                process.join(timeout=5)
                process.terminate()
                process.join(timeout=15)

                if process.is_alive():
                    process.kill()
                    process.join(timeout=30)

            if process.is_alive() is False:
                process.close()
            else:
                logger.info(f'Website {process.name} process didn\'t close correctly')
                main_loop = all_process_closed = False

        if all_process_closed:
            logger.info("All websites processes terminated")
        else:
            logger.info('Some website didn\'t terminate, aborting the program')
            main_loop = False

        get_websites_log(config.results_path, logs_queue)
        logger.info('Saved websites logs')

        # make sure to close browser connection
        try:
            browser_process = psutil.Process(browser._process_pid)
        except:
            browser_process = None
            
        browser.stop()

        while browser_process is not None and browser_process.is_running():
            browser_process.terminate()
            browser_process.kill()
            browser_process.wait(timeout=60)
        logger.info('Stopped browser process')

        logger.info(f'Finished in {time.time() - main_timer:.2f}s\n\n')
        time.sleep(5)

    logger.info("")
    logger.info("The program has terminated running.")

if __name__ == "__main__":
    _uvloop = False

    try:
        uvloop.install()
        _uvloop = True
    except:
        pass

    if _uvloop:
        uvloop.run(main('uvloop'))
    else:
        asyncio.run(main('asyncio'))
