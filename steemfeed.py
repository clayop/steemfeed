import time, calendar, datetime
import dateutil.parser
import requests
import random
from steemapi import SteemWalletRPC

# Config
interval_init  = 60*60*2             # Feed publishing interval in seconds
rand_level     = 0.10                # Degree of randomness of interval
freq           = 60                  # Frequency of parsing trade histories
min_change     = 0.03                # Minimum price change to publish feed
max_age        = 60*60*24            # Maximum age of price feed
manual_conf    = 0.30                # Maximum price change without manual confirmation
use_telegram   = 0                   # If 1, you can confirm manual price feed through Telegram
telegram_token = "telegram_tocken"   # Create your Telegram bot at @BotFather (https://telegram.me/botfather)
telegram_id    = 0                   # Get your telegram id at @MyTelegramID_bot (https://telegram.me/mytelegramid_bot)
rpc_host       = "localhost"
rpc_port       = 8092
witness        = "yourwitness"       # Your witness name

print("Connecting to Steem RPC")
rpc = SteemWalletRPC(rpc_host, rpc_port, "", "")
print("Connected")
if use_telegram == 1:
    import telegram
    print("Connecting to Telegram")
    bot = telegram.Bot(token=telegram_token)
    print("Connected")

def utc_time():
    t = calendar.timegm(datetime.datetime.utcnow().utctimetuple())
    return t

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

def rand_interval(intv):
    intv += intv*rand_level*random.uniform(-1, 1)
    if intv < 60*60:
        intv = 60*60
    elif intv > 60*60*24*7:
        intv = 60*60*24*7
    return(int(intv))

def confirm(pct, p):
    if use_telegram == 0:
        conf = input("Your price feed change is over " + format(pct*100, ".1f") + "% (" + p + "USD/STEEM) If you confirm this, type 'confirm': ")
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
        last_update_id = bot.getUpdates()[-1].update_id
        custom_keyboard = [["deny"]]
        reply_markup = {"keyboard":custom_keyboard, "resize_keyboard": True}
        conf_msg = ("Your price feed change is over " + format(pct*100, ".1f") + "% (" + p + "USD/STEEM) If you confirm this, type 'confirm'")
        bot.sendMessage(chat_id=telegram_id, text=conf_msg, reply_markup=reply_markup)
        while True:
            updates = bot.getUpdates(offset=last_update_id, limit = 30)[-1]
            chat_id = updates.message.chat_id
            update_id = updates.update_id
            cmd = updates.message.text
            if update_id > last_update_id:
                if chat_id == telegram_id and cmd.lower() == "confirm":
                    bot.sendMessage(chat_id=telegram_id, text="Publishing confirmed")
                    last_update_id = update_id
                    return True
                elif chat_id == telegram_id and cmd.lower() == "deny":
                    bot.sendMessage(chat_id=telegram_id, text="Publishing denied")
                    last_update_id = update_id
                    return False
            time.sleep(3)


if __name__ == '__main__':
    steem_q = 0
    btc_q = 0
    last_update_t = 0
    interval = rand_interval(interval_init)
    try:
        last_price = (requests.get("https://bittrex.com/api/v1.1/public/getticker?market=BTC-STEEM").json()["result"]["Last"])*btc_usd()
        print("The current market price is " + format(last_price, ".3f") + " USD/STEEM")
    except:
        last_price = float(rpc.get_feed_history()["current_median_history"]["base"].split()[0])/float(rpc.get_feed_history()["current_median_history"]["quote"].split()[0])
        print("Failed to fetch market price. Current median feed price " + format(last_price, ".3f") + " USD/STEEM will be used")

    start_t = (utc_time()//freq)*freq - freq
    last_t = start_t - 1
    print("Please be advised that your first price feed will be published when the price changes over " + format(min_change*100, ".1f") + "% or after " + format(max_age/3600, ".0f") + " hours")
    init_pub = input("Will you publish this price feed (" + format(last_price, ".3f") + " USD/STEEM)? (y/N) ")
    if init_pub.lower() == "y":
        rpc.publish_feed(witness, {"base": format(last_price, ".3f") +" SBD", "quote":"1.000 STEEM"}, True)
        print("Published price feed: " + format(last_price, ".3f") + " USD/STEEM at " + time.ctime())
        last_update_t = (utc_time()//freq)*freq - freq
    else:
        last_price = 0.0001
        print("Please confirm your first feed price after " + str(int(interval/60)) + " minutes")

    while True:
        curr_t = (utc_time()//freq)*freq - freq
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
                print("Error in fetching Bittrex market history")
                pass
        if curr_t - start_t >= interval:
            if steem_q > 0:
                price = btc_q/steem_q*btc_usd()
                price_str = format(price, ".3f")
                if (abs(1 - price/last_price) < min_change) and ((curr_t - last_update_t) < max_age):
                    print("No significant price change or the feed is not obsolete")
                    print("Last price: " + format(last_price, ".3f") + "  Current price: " + price_str + "  " + format((price/last_price*100 - 100), ".1f") + "%  / Feed age: " + str(int((curr_t - last_update_t)/3600)) + " hours")
                else:
                    if abs(1 - price/last_price) > manual_conf:
                        if confirm(manual_conf, price_str) is True:
                            rpc.publish_feed(witness, {"base": price_str +" SBD", "quote":"1.000 STEEM"}, True)
                            print("Published price feed: " + price_str + " USD/STEEM at " + time.ctime())
                            last_price = price
                    else:
                        rpc.publish_feed(witness, {"base": price_str +" SBD", "quote":"1.000 STEEM"}, True)
                        print("Published price feed: " + price_str + " USD/STEEM at " + time.ctime())
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
