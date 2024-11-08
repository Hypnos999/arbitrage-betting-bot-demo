import logging
from multiprocessing import Queue
import json
import pickle


def get_logger(name, path, console=False) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel('DEBUG')
    f = logging.Formatter("%(asctime)s: %(message)s")

    file_info = logging.FileHandler(path, mode="a")
    file_info.setFormatter(f)
    logger.addHandler(file_info)

    if console:
        console_info = logging.StreamHandler()
        console_info.setFormatter(f)
        logger.addHandler(console_info)

    return logger


def get_websites_log(path: str, logs_queue: Queue):
    old_logs = {}
    try:
        with open(path + 'websites_logs.json', 'r') as f:
            old_logs = json.loads(f.read())
    except:
        pass

    logs = {}
    while not logs_queue.empty():
        logs |= pickle.loads(logs_queue.get())

    with open(path + 'websites_logs.json', 'w') as f:
        f.write(json.dumps(old_logs | {str(len(old_logs)+1): logs}, indent=2))
