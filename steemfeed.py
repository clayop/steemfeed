import time
import dateutil.parser
import requests
from steemapi import SteemWalletRPC

# Config
interval = 3600       # Feed publishing interval in seconds
freq = 60             # Frequency of parsing trade histories
null_price = 0.400    # Current Price (Just in case)
witness = "clayop"    # Your witness name

rpc = SteemWalletRPC("localhost", 8092, "", "")

def btc_usd():
    n = 0
    try:
        bitfinex = float(requests.get("https://api.bitfinex.com/v1/pubticker/BTCUSD").json()["last_price"])
        n += 1
    except:
        bitfinex = 0
    try:
        coinbase = float(requests.get("https://api.exchange.coinbase.com/products/BTC-USD/ticker").json()["price"])
        n += 1
    except:
        coinbase = 0
    try:
        okcoin = float(requests.get("https://www.okcoin.com/api/v1/ticker.do?symbol=btc_usd").json()["ticker"]["last"])
        n += 1
    except:
        okcoin = 0
    try:
        bitstamp = float(requests.get("https://www.bitstamp.net/api/v2/ticker/btcusd/").json()["last"])
        n += 1
    except:
        bitstamp = 0
    res = (bitfinex + coinbase + okcoin + bitstamp)/n
    return res


if __name__ == '__main__':
    steem_q = 0
    btc_q = 0
    try:
        price = (requests.get("https://bittrex.com/api/v1.1/public/getticker?market=BTC-STEEM").json()["result"]["Last"])*btc_usd()
    except:
        price = null_price
    start_t = (time.time()//freq)*freq - freq
    last_t = start_t - 1

    while True:
        curr_t = (time.time()//freq)*freq - freq
        if curr_t > last_t:
            try:
                h = requests.get("https://bittrex.com/api/v1.1/public/getmarkethistory?market=BTC-STEEM")
                hist = h.json()
                last_t = curr_t
                for i in range(200):
                    strf_t = hist["result"][i]["TimeStamp"]
                    unix_t = dateutil.parser.parse(strf_t).timestamp()
                    if unix_t >= curr_t:
                        steem_q += hist["result"][i]["Quantity"]
                        btc_q += hist["result"][i]["Total"]
                    else:
                        break
            except:
                pass
        if curr_t - start_t >= interval:
            if steem_q > 0:
                price = format(btc_q/steem_q*btc_usd(), ".3f")
                rpc.publish_feed(witness, {"base": price +" SBD", "quote":"1.000 STEEM"}, True)
                print("Published price feed: " + price + " USD/STEEM at " + time.ctime())
                steem_q = 0
                btc_q = 0
            start_t = curr_t
        time.sleep(freq*0.7)
