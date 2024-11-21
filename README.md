# arbitrage-betting-bot-demo
A Python script that can open and use multiple chrome tabs, each being a different sport betting website. 
It is capable of: 
  1. logging in your account [not in the demo]
  2. read the balance
  3. match the live events odds betwhen sportbooks until it finds an arbitrage opportunity
  4. select the bet to place on the interested websites and pay the calculated amount to happen. 

There are more steps and functions in the actual lifetime of the websites, mainly checks to make sure that all bets are still open and not closed or suspended. 
This is because live events odds are much more volatile.

The various function each website must run are:
1. [X] logout, to ensure fresh session.
2. [X] login
3. prep, get the balance of your profile [X] and do various things in order to prepare the website.
4. odds matching, each tab scrape the website odds trough the network as this websites use AJAX request/wss to update data.
4. place bet, once an arbitrgae opportunity is found, the interested websites will select their bet and type the right stake.
5. double check (arb checker & website checker), make sure there are no errors and that bets are open
6. pay bet, click on the button to confirm our bets [In this case it flashes a red dot instead of clicking on the element]

the current supported (italian) websites are:
  1. Snai
  2. Sisal
  3. VinciTu
  4. EuroBet
  5. Better
  6. BetSson
  7. BetFlag

if you're pc can handle it you can run all them in parallel.

to try the demo it you will have to:
1. clone the github repo
2. create an envinroment (optional) and run pip install -r requirements.txt
3. edit config.py 
4. run python main.py in the cmd to start the script
5. The scripts ignores the cookies preference pop ups, you should do them yourself as the programm store cookies to remember your choises and it will not ask again.

Being this a demo version some function indicated with [X] like logout and login are not included.
If you want to replicate the complete version or you're interested in this project please feel free to get in contact with me.

I also uploaded a video of the  version run, see "alpha run video.mp4".


