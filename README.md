### Preparation
To use this price feed script, the following dependencies and packages should be installed.

    sudo apt-get install libffi-dev libssl-dev python3-dev python3-pip
    sudo pip3 install python-dateutil
    sudo pip3 install websocket-client
    sudo pip3 install steem

In addition, you should run cli_wallet by using the following command,

    cli_wallet -s ws://localhost:8090 -H 127.0.0.1:8092 --rpc-http-allowip=127.0.0.1

And unlock your cli_wallet.


### Installation
Copy the code in [this link](https://github.com/clayop/steemfeed/blob/master/steemfeed.py) and paste as `steemfeed.py` in your witness server.


### Configuration
Then, edit the `steemfeed.py` to configure. We have some items under Config category in the code.

* `interval`: Interval of publishing price feed. The default value is one hour (3600 seconds)
* `freq`: Frequency of parsing trade history. Please be noticed that it can parse only 200 last trading history (Bittrex), so as trading is active you may need to decrease this frequency value.
* `min_change`: Minimum price change percentage to publish feed
* `max_age`: Maximum age of price feed
* `manual_conf`: Maximum price change without manual confirmation. If price change exceeds this, you will be asked to confirm
* `use_telegram`: If you want to use Telegram for confirmation, enter 1
* `telegram_token`: Create your Telegram bot at @BotFather (https://telegram.me/botfather)
* `telegram_id`: Get your telegram id at @MyTelegramID_bot (https://telegram.me/mytelegramid_bot)
* `rpc_host`: Your RPC host address
* `rpc_port`: Your RPC host port
* `witness`: Enter ***YOUR WITNESS ID*** here
 

### Run
Then, run this code in a separate screen

    screen -S steemfeed
    python3 ./steemfeed.py
