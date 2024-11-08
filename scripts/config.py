from scripts.arbitrage.sport import Sport
import os

class Config:
    """config class, store all settings"""

    def __init__(self):
        if os.name == "posix":
            # linux
            self.links_path = rf"{os.getcwd}/files/data/links.json"
            self.credentials_path = rf'{os.getcwd}/files/data/credentials.json'
            self.logs_path = rf"{os.getcwd}/files/logs/"
            self.results_path = rf"{os.getcwd}/files/results/"
            self.images_path = rf"{os.getcwd}/files/images/"
            self.browser_executable_path = '/opt/google/chrome/google-chrome'  # Chrome for Linux
            # self.browser_executable_path = '/opt/slimjet/flashpeak-slimjet'  # SlimJet for Linux
            self.browser_user_data_dir = rf"{os.getcwd}/files/profile"  # User Dir path for Linux

        elif os.name == "nt":
            # windows
            self.links_path = rf"{os.getcwd()}\files\data\links.json"
            self.credentials_path = rf"{os.getcwd()}\files\data\credentials.json"
            self.logs_path = rf"{os.getcwd()}\files\logs\\"
            self.results_path = rf"{os.getcwd()}\files\results\\"
            self.images_path = rf"{os.getcwd()}\files\images\\"
            self.run_path = rf"{os.getcwd()}\files\run\\"
            
            self.browser_executable_path = r'C:\Program Files\Google\Chrome\Application\chrome.exe'  # Chrome for Windows
            self.browser_user_data_dir = rf"{os.getcwd()}\files\profile"

        # universal configs
        self.website_to_use = [
            'betflag',
            'betsson',
            'better',
            'eurobet',
            'sisal',
            'snai',
            'vincitu',
        ]
        
        # "football" | "tennis" | "basketball"
        self.sport_to_use = Sport("football").sport

        self.website_timeout = 60 * 5  # time to wait before raising an exception within the execution of a website function
        self.total_amount = 100  # general amount to bet, it can vries due to round up of the bet
        self.bet_round_up = 5
        self.probability_treshold = [0.0, 1.0]   # the probability range in which arbs will be considered
        self.restart_time = 60 * 15  # the time after which if we didn't found any arb we restart the websites processes

    def to_json(self):
        json = {}
        for attr in self.__dict__:
            json[attr] = self.__dict__[attr]

        return json
