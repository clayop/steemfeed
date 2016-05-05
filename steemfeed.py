import time, datetime
import dateutil.parser
import requests
import random
import json
import websocket
from websocket import create_connection
from steemapi import SteemWalletRPC

# Config

interval_init  = 60*60*2             # Feed publishing interval in seconds
rand_level     = 0.10                # Degree of randomness of interval
freq           = 60                  # Frequency of parsing trade histories
min_change     = 0.03                # Minimum price change to publish feed
max_age        = 60*60*24            # Maximum age of price feed
manual_conf    = 0.30                # Maximum price change without manual confirmation
use_telegram   = 0                   # If 1, you can confirm manual price feed through Telegram
telegram_token = "telegram_token"    # Create your Telegram bot at @BotFather (https://t$
telegram_id    = 00000000            # Get your telegram id at @MyTelegramID_bot (https://telegram.me/mytelegramid_bot)
bts_ws         = ["wss://dele-puppy.com/ws", "wss://bitshares.openledger.info/ws", "wss://valen-tin.fr:8090/ws"]
rpc_host       = "localhost"
rpc_port       = 8092
witness        = "yourwitness"       # Your witness name

def rand_interval(intv):
    intv += intv*rand_level*random.uniform(-1, 1)
    if intv < 60*60:
        intv = 60*60
    elif intv > 60*60*24*7:
        intv = 60*60*24*7
    return(int(intv))

def confirm(pct, p, last_update_id=None):
    if use_telegram == 0:
        conf = input("Your price feed change is over " + format(pct*100, ".1f") + "% (" + p + " USD/STEEM) If you confirm this, type 'confirm': ")
        if conf.lower() == "confirm":
            return True
        else:
            reconf = input("You denied to publish this feed. Are you sure? (Y/n): ")
            if reconf.lower() == "n":
                conf = input("If you confirm this, type 'confirm': ")
                if conf.lower() == "confirm":
                    return True
                else:
                    print("Publishing denied")
                    return False
            else:
                print("Publishing denied")
                return False
    elif use_telegram == 1:
        custom_keyboard = [["deny"]]
        reply_markup = json.dumps({"keyboard":custom_keyboard, "resize_keyboard": True})
        conf_msg = ("Your price feed change is over " + format(pct*100, ".1f") + "% (" + p + " USD/STEEM) If you confirm this, type 'confirm'")
        payload = {"chat_id":telegram_id, "text":conf_msg, "reply_markup":reply_markup}
        m = telegram("sendMessage", payload)
        while True:
            updates = telegram("getUpdates", {"offset":last_update_id, "limit": 100})["result"][-1]
            chat_id = updates["message"]["from"]["id"]
            update_id = updates["update_id"]
            cmd = updates["message"]["text"]
            if update_id > last_update_id:
                if chat_id == telegram_id and cmd.lower() == "confirm":
                    payload = {"chat_id":telegram_id, "text":"Publishing confirmed"}
                    m = telegram("sendMessage", payload)
                    last_update_id = update_id
                    return True
                elif chat_id == telegram_id and cmd.lower() == "deny":
                    payload = {"chat_id":telegram_id, "text":"Publishing denied"}
                    m = telegram("sendMessage", payload)
                    last_update_id = update_id
                    return False
            time.sleep(3)

def telegram(method, params=None):
    url = "https://api.telegram.org/bot"+telegram_token+"/"
    params = params
    r = requests.get(url+method, params = params).json()
    return r

def btc_usd():
    prices = {}
    try:
        r = requests.get("https://api.bitfinex.com/v1/pubticker/BTCUSD").json()
        prices['bitfinex'] = {'price': float(r['last_price']), 'volume': float(r['volume'])}
    except:
        pass
    try:
        r = requests.get("https://api.exchange.coinbase.com/products/BTC-USD/ticker").json()
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
       raise Exception("All BTC price feeds failed")
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
            bts_btc_p = bts_btc_feed["base"]["amount"]/bts_btc_feed["quote"]["amount"]/1000
            ws.close()
            return (dex_btc_h, dex_bts_h, bts_btc_p)
        except:
            pass
    raise Exception("All DEX websocket servers are down")


if __name__ == '__main__':
    print("Connecting to Steem RPC")
    rpc = SteemWalletRPC(rpc_host, rpc_port, "", "")
    try:
        bh = rpc.info()["head_block_num"]
        bh = 1
        print("Connected. Current block height is " + str(bh))
    except:
        print("Connection error. Check your cli_wallet")
        quit()
    if use_telegram == 1:
        try:
            print("Connecting to Telegram")
            last_update_id = telegram("getUpdates")["result"][-1]["update_id"]
            payload = {"chat_id":telegram_id, "text":"Connected"}
            m = telegram("sendMessage", payload)
        except:
            print("Connection error. Check that you had any conversation with your bot")
            quit()

    steem_q = 0
    btc_q = 0
    last_update_t = 0
    interval = rand_interval(interval_init)
    time_adj = time.time() - datetime.datetime.utcnow().timestamp()
    start_t = (time.time()//freq)*freq - freq
    last_t = start_t - 1
    last_price = float(rpc.get_feed_history()["current_median_history"]["base"].split()[0])/float(rpc.get_feed_history()["current_median_history"]["quote"].split()[0])
    print("Current median feed price is " + format(last_price, ".3f") + " USD/STEEM")

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
#                print("Error in fetching Poloniex market history")
                pass

# Bitshares DEX
            dex_btc_h, dex_bts_h, bts_btc_p = bts_dex_hist(bts_ws)
            for i in range(50):
                if (dateutil.parser.parse(dex_btc_h[0]["time"]).timestamp() + time_adj) >= curr_t:
                    if dex_btc_h[i]["op"]["pays"]["asset_id"] == "1.3.973":
                        steem_q += dex_btc_h[i]["op"]["pays"]["amount"]/1000
                        btc_q += dex_btc_h[i]["op"]["receives"]["amount"]/100000000
                    else:
                        steem_q += dex_btc_h[i]["op"]["receives"]["amount"]/1000
                        btc_q += dex_btc_h[i]["op"]["pays"]["amount"]/100000000
            for i in range(50):
                if (dateutil.parser.parse(dex_bts_h[0]["time"]).timestamp() + time_adj) >= curr_t:
                    if dex_bts_h[i]["op"]["pays"]["asset_id"] == "1.3.973":
                        steem_q += dex_bts_h[i]["op"]["pays"]["amount"]/1000
                        btc_q += dex_bts_h[i]["op"]["receives"]["amount"]/100000*bts_btc_p
                    else:
                        steem_q += dex_bts_h[i]["op"]["receives"]["amount"]/1000
                        btc_q += dex_bts_h[i]["op"]["pays"]["amount"]/100000*bts_btc_p

            last_t = curr_t

        if curr_t - start_t >= interval:
            if steem_q > 0:
                price = btc_q/steem_q*btc_usd()
                price_str = format(price, ".3f")
                if (abs(1 - price/last_price) < min_change) and ((curr_t - last_update_t) < max_age):
                    print("No significant price change and last feed is still valid")
                    print("Last price: " + format(last_price, ".3f") + "  Current price: " + price_str + "  " + format((price/last_price*100 - 100), ".1f") + "%  / Feed age: " + str(int((curr_t - last_update_t)/3600)) + " hours")
                else:
                    if abs(1 - price/last_price) > manual_conf:
                        if confirm(manual_conf, price_str, last_update_id) is True:
                            rpc.publish_feed(witness, {"base": price_str +" SBD", "quote":"1.000 STEEM"}, True)
                            print("Published price feed: " + price_str + " USD/STEEM at " + time.ctime()+"\n")
                            last_price = price
                    else:
                        rpc.publish_feed(witness, {"base": price_str +" SBD", "quote":"1.000 STEEM"}, True)
                        print("Published price feed: " + price_str + " USD/STEEM at " + time.ctime()+"\n")
                        last_price = price
                    steem_q = 0
                    btc_q = 0
                    last_update_t = curr_t
            else:
                print("No trades occured during this period")
            interval = rand_interval(interval_init)
            start_t = curr_t
        left_min = (interval - (curr_t - start_t))/60
        print(str(int(left_min)) + " minutes to next update   \r", end="")
        time.sleep(freq*0.7)
