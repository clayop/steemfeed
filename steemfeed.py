from steem import Steem
import time, datetime
import dateutil.parser
import requests
import random
import json
import websocket
from websocket import create_connection
from Crypto.Cipher import XOR
import base64
import yaml
import getpass


def encrypt(key, plaintext):
  cipher = XOR.new(key)
  return base64.b64encode(cipher.encrypt(plaintext))

def decrypt(key, ciphertext):
  cipher = XOR.new(key)
  return cipher.decrypt(base64.b64decode(ciphertext))

def rand_interval(intv):
    intv += intv*rand_level*random.uniform(-1, 1)
    if intv < 60*60:
        intv = 60*60
    elif intv > 60*60*24*7:
        intv = 60*60*24*7
    return(int(intv))

def btc_usd():
    prices = {}
    try:
        r = requests.get("https://api.bitfinex.com/v1/pubticker/BTCUSD").json()
        prices['bitfinex'] = {'price': float(r['last_price']), 'volume': float(r['volume'])}
    except:
        pass
    try:
        r = requests.get("https://api.gdax.com/products/BTC-USD/ticker").json()
        prices['coinbase'] = {'price': float(r['price']), 'volume': float(r['volume'])}
    except:
        pass
    try:
        r = requests.get("https://www.okcoin.com/api/v1/ticker.do?symbol=btc_usd").json()["ticker"]
        prices['okcoin'] = {'price': float(r['last']), 'volume': float(r['vol'])}
    except:
        pass
    try:
        r = requests.get("https://www.bitstamp.net/api/v2/ticker/btcusd/").json()
        prices['bitstamp'] = {'price': float(r['last']), 'volume': float(r['volume'])}
    except:
        pass
    if not prices:
       return 0
    total_usd = 0
    total_btc = 0
    for p in prices.values():
        total_usd += p['price'] * p['volume']
        total_btc += p['volume']
    avg_price = total_usd / total_btc
    return avg_price

def bts_dex_hist(address):
    for s in address:
        try:
            ws = create_connection(s)
            login = json.dumps({"jsonrpc": "2.0", "id":1,"method":"call","params":[1,"login",["",""]]})
            hist_api = json.dumps({"jsonrpc": "2.0", "id":2, "method":"call","params":[1,"history",[]]})
            btc_hist = json.dumps({"jsonrpc": "2.0", "id": 3, "method": "call", "params": [2, "get_fill_order_history", ["1.3.861", "1.3.973", 50]]})
            bts_hist = json.dumps({"jsonrpc": "2.0", "id": 4, "method": "call", "params": [2, "get_fill_order_history", ["1.3.0", "1.3.973", 50]]})
            bts_feed = json.dumps({"jsonrpc": "2.0", "id": 5, "method": "call", "params": [0, "get_objects", [["2.4.3"]]]})
            ws.send(login)
            ws.recv()
            ws.send(hist_api)
            ws.recv()
            ws.send(btc_hist)
            dex_btc_h = json.loads(ws.recv())["result"]
            ws.send(bts_hist)
            dex_bts_h = json.loads(ws.recv())["result"]
            ws.send(bts_feed)
            bts_btc_feed = json.loads(ws.recv())["result"][0]["current_feed"]["settlement_price"]
            bts_btc_p = bts_btc_feed["base"]["amount"]/bts_btc_feed["quote"]["amount"]/10**3
            ws.close()
            return (dex_btc_h, dex_bts_h, bts_btc_p)
        except:
            return (0, 0, 0)

def publish_feed(base, quote, account):
    steem.commit.witness_feed_publish(base, quote=quote, account=account)
    print("Published price feed: " + format(base/quote, ".3f") + " USD/STEEM at " + time.ctime()+"\n")


if __name__ == '__main__':
    config_file = open("steemfeed_config.yml", "r")
    steemfeed_config = yaml.load(config_file)
    pw             = getpass.getpass("Enter your password: ")
    steemnode      = steemfeed_config["steemnode"]
    discount       = float(steemfeed_config["discount"])
    interval_init  = float(steemfeed_config["interval_init"])
    rand_level     = float(steemfeed_config["rand_level"])
    freq           = float(steemfeed_config["freq"])
    min_change     = float(steemfeed_config["min_change"])
    max_age        = float(steemfeed_config["max_age"])
    bts_ws         = steemfeed_config["bts_ws"]
    witness        = steemfeed_config["witness"]
    if steemfeed_config["wif"] == "":
        pw = getpass.getpass("Enter your password: ")
        repw = getpass.getpass("Confirm your password: ")
        if pw == repw:
            config_file.close()
            activekey = getpass.getpass("Enter active private key of your witness: ")
            steemfeed_config["wif"] = encrypt(pw, str(activekey)).decode()
            with open("steemfeed_config.yml", "w") as config_file:
                yaml.dump(steemfeed_config, config_file, default_flow_style=False)
            config_file = open("steemfeed_config.yml", "r")
            steemfeed_config = yaml.load(config_file)
    wif = decrypt(pw, steemfeed_config["wif"]).decode()
    pw = ""
    steem = Steem(nodes=[steemnode], keys=[wif])
    try:
        bh = steem.get_dynamic_global_properties()["head_block_number"]
        print("Connected. Current block height is " + str(bh))
    except:
        print("Connection error. Check your node")
        quit()

    steem_q = 0
    btc_q = 0
    last_update_t = 0
    interval = rand_interval(interval_init)
    time_adj = time.time() - datetime.datetime.utcnow().timestamp()
    start_t = (time.time()//freq)*freq - freq
    last_t = start_t - 1
    my_info = steem.get_witness_by_account(witness)
    if float(my_info["sbd_exchange_rate"]["quote"].split()[0]) == 0:
        last_price = 0
    else:
        last_price = float(my_info["sbd_exchange_rate"]["base"].split()[0]) / float(my_info["sbd_exchange_rate"]["quote"].split()[0])
    print("Your last feed price is " + format(last_price, ".3f") + " USD/STEEM")

    while True:
        curr_t = (time.time()//freq)*freq - freq
        if curr_t > last_t:
# Bittrex
            try:
                bt_h = requests.get("https://bittrex.com/api/v1.1/public/getmarkethistory?market=BTC-STEEM")
                bt_hist = bt_h.json()
                for i in range(200):
                    strf_t = bt_hist["result"][i]["TimeStamp"]
                    unix_t = dateutil.parser.parse(strf_t).timestamp()
                    unix_t += time_adj
                    if unix_t >= curr_t:
                        steem_q += bt_hist["result"][i]["Quantity"]
                        btc_q += bt_hist["result"][i]["Total"]
                        pass
                    else:
                        break
            except:
                print("Error in fetching Bittrex market history")
                pass

# Poloniex
            try:
                po_h = requests.get("https://poloniex.com/public?command=returnTradeHistory&currencyPair=BTC_STEEM&start="+str(curr_t))
                po_hist = po_h.json()
                for i in range(len(po_hist)):
                    steem_q += float(po_hist[i]["amount"])
                    btc_q += float(po_hist[i]["total"])
                    pass
            except:
                print("Error in fetching Poloniex market history")
                pass

# Bitshares DEX
            try:
                dex_btc_h, dex_bts_h, bts_btc_p = bts_dex_hist(bts_ws)
                if dex_btc_h != 0 and dex_bts_h != 0 and bts_btc_p !=0:
                    for i in range(50):
                        if (dateutil.parser.parse(dex_btc_h[i]["time"]).timestamp() + time_adj) >= curr_t:
                            if dex_btc_h[i]["op"]["pays"]["asset_id"] == "1.3.973":
                                steem_q += float(dex_btc_h[i]["op"]["pays"]["amount"])/10**3
                                btc_q += float(dex_btc_h[i]["op"]["receives"]["amount"])/10**8
                            else:
                                steem_q += float(dex_btc_h[i]["op"]["receives"]["amount"])/10**3
                                btc_q += float(dex_btc_h[i]["op"]["pays"]["amount"])/10**8
                    for i in range(50):
                        if (dateutil.parser.parse(dex_bts_h[i]["time"]).timestamp() + time_adj) >= curr_t:
                            if dex_bts_h[i]["op"]["pays"]["asset_id"] == "1.3.973":
                                steem_q += float(dex_bts_h[i]["op"]["pays"]["amount"])/10**3
                                btc_q += (float(dex_bts_h[i]["op"]["receives"]["amount"])/10**5)*bts_btc_p
                            else:
                                steem_q += float(dex_bts_h[i]["op"]["receives"]["amount"])/10**3
                                btc_q += (float(dex_bts_h[i]["op"]["pays"]["amount"])/10**5)*bts_btc_p
            except:
                print("Error in fetching DEX market history")
                pass
# Current time update
            last_t = (time.time()//freq)*freq - freq

        if curr_t - start_t >= interval:
            if steem_q > 0:
                base = btc_q/steem_q*btc_usd()
                quote = 1/(1-discount)
                price = base/quote
                price_str = format(price, ".3f")
                if (abs(1 - price/last_price) < min_change) and ((curr_t - last_update_t) < max_age):
                    print("No significant price change and last feed is still valid")
                    print("Last price: " + format(last_price, ".3f") + "  Current price: " + price_str + "  " + format((price/last_price*100 - 100), ".1f") + "%  / Feed age: " + str(int((curr_t - last_update_t)/3600)) + " hours")
                else:
                    publish_feed(base, quote, witness)
                    last_price = price
                    steem_q = 0
                    btc_q = 0
                    last_update_t = (time.time()//freq)*freq - freq
            else:
                print("No trades occured during this period")
            interval = rand_interval(interval_init)
            start_t = (time.time()//freq)*freq - freq
            with open("steemfeed_config.yml", "r") as config_file:
                steemfeed_config = yaml.load(config_file)
                steemnode      = steemfeed_config["steemnode"]
                discount       = steemfeed_config["discount"]
                interval_init  = steemfeed_config["interval_init"]
                rand_level     = steemfeed_config["rand_level"]
                freq           = steemfeed_config["freq"]
                min_change     = steemfeed_config["min_change"]
                max_age        = steemfeed_config["max_age"]
                bts_ws         = steemfeed_config["bts_ws"]

        left_min = (interval - (curr_t - start_t))/60
        if steem_q > 0:
            print("%s minutes to next update / Volume: %s BTC, %s STEEM / Average Price: %s\r" % (str(int(left_min)), format(btc_q, ".4f"), str(int(steem_q)), format(btc_q/steem_q, ".8f")), end="")
        time.sleep(freq*0.7)
