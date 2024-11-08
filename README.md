# arbitrage-betting-bot-demo
A Python multi process based programm to controll multiple live betting websites in parallel. It is capable of logging in your account, match the odds betwhen sportbooks, select the bet to place and pay the right amount for the arbitrage to happen. 

This is a demo version released for demonstration porpuses,
to try it you will have to:
1. clone the github repo
2. create an envinroment (optional) and run pip install -r requirements.txt
3. edit config.py to change the software options
4. run python main.py in the cmd to start the script
5. if you se pop ups in your chrome tabs you should close them yourself as the programm store cookies to remember your choises.

The various function each website must run are:
1. logout, to ensure fresh cookies.
2. log in, for later when it will eventually pay a bet.
3. prep, do various things in order to prepare the website.
4. odds matching, each website intercept their odds and send them to the main process.
4. place bet, one an arbitrgae opportunity is found, the interested websites will select their bet.
5. double check, make sure there are no errors and that bets are open
6. pay bet, click on the button to confirm our bets

Being this a demo version some function like logout and login are not included.

If you want to replicate the alpha version or you're interested in this project please feel free to get in contact with me.
I also uploaded a video of the alpha version run.