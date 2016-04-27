### Preparation
To use this price feed script, the following dependencies and packages should be installed.

    sudo apt-get install libffi-dev libssl-dev python3-dev python3-pip
    sudo pip3 install python-dateutil
    sudo pip3 install steem
   
In addition, you should run cli_wallet by using the following command,

    cli_wallet -s ws://localhost:8090 -H 127.0.0.1:8092 --rpc-http-allowip=127.0.0.1

And unlock your cli_wallet.


### Installation
Copy the code in [this link](https://github.com/clayop/steemfeed/blob/master/steemfeed.py) and paste as `steemfeed.py` in your witness server.


### Configuration
Then, edit the `steemfeed.py` to configure. We have four items under Config category in the code. interval, freq, null_price, witness

* `interval`: Interval of publishing price feed. The default value is one hour (3600 seconds)
* `freq`: Frequency of parsing trade history. Please be noticed that it can parse only 200 last trading history (Bittrex), so as trading is active you may need to decrease this frequency value.
* `witness`: Enter ***YOUR WITNESS ID*** here
* `null_price`: Set this manually to the current price.

### Run
Then, run this code in a separate screen

    screen -dmS steemfeed python3 ./steemfeed.py
