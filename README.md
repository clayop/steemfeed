### Supported Exchanges
* Bittrex
* Poloniex
* Openledger (BTS-STEEM, Open.BTC-STEEM)

### BTC Price Sources
* Bitfinex
* Gdax(coinbase)
* Okcoin
* Bitstamp

### Preparation
To use this price feed script, the following dependencies and packages should be installed.

    sudo apt-get install libffi-dev libssl-dev python3-dev python3-pip
    sudo pip3 install python-dateutil
    sudo pip3 install websocket-client
    sudo pip3 install requests
    sudo pip3 install pycrypto
    sudo pip install -U steem

(if you got an error during installing steem, run ``sudo pip3 install upgrade pip``)

_You can find more info about `steem` [here](https://github.com/steemit/steem-python)_

Then, edit `~/witness_node_data_dir/config.ini` and make sure to add required APIs:
```
public-api = database_api login_api network_broadcast_api
```


### Installation
Copy the code in [this link](https://github.com/clayop/steemfeed/blob/master/steemfeed.py) and paste as `steemfeed.py` in your witness server.


### Configuration
Then, edit `steemfeed_config.yml` to configure. It has some items under Config category in the code.

* `discount`: Discount rate (e.g. 0.10 means published price feed is 10% smaller than market price)
* `interval_init`: Feed publishing interval in seconds
* `rand_level`: Degree of randomness of interval
* `freq`: Frequency of parsing trade history. Please be noticed that it can parse only 200 last trading history (Bittrex), so as trading is active you may need to decrease this frequency value.
* `min_change`: Minimum price change percentage to publish feed
* `max_age`: Maximum age of price feed
* `bts_ws` : List of BitShares Websocket servers
* `witness`: Enter ***YOUR WITNESS ID*** here
 * `wif`: Leave it empty. You will add your key with encryption when run the script first time

### Run
Then, run this code in a separate screen

    screen -S steemfeed
    python3 ./steemfeed.py
(If it gives you permission error, run in `sudo`)
