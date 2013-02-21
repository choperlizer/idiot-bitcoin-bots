import decimal

import json
import sys
import urllib
import urllib2
import random
import hashlib
import base64
from decimal import Decimal
import decimal
import warnings
import time
import hmac
import math
import datetime

from mtgox_requester import requester

from settings import *

mtgox_req=requester(mtgox_key, mtgox_secret)

def get_json(url, data={}):
    try:
        if data:
            f = urllib2.urlopen(
                url, data=data)
        else:
            f = urllib2.urlopen(
                url)
        result=f.read()
        final_json=json.loads(result)
        return final_json
    except Exception as inst:
        print "Unexpected error:", inst
        time.sleep(bs_seconds)
        return None

def get_optimal_price(target_price, bids):
    max_bid_below_target=Decimal("0")
    for bid in bids:
        bid_amount=Decimal(str(bid[0]))
        if bid_amount>max_bid_below_target and Decimal(str(bid[0]))<target_price:
            max_bid_below_target=Decimal(str(bid[0]))
        elif Decimal(str(bid[0]))==target_price:
            return target_price
    if max_bid_below_target==Decimal("0"):
        return target_price
    return max_bid_below_target+Decimal("0.01")

def place_bid(price, amount):
    print "placing bid", price, amount
    price=price.quantize(Decimal('.01'))
    amount=amount.quantize(Decimal('.00000001'), rounding=decimal.ROUND_DOWN)
    if not DEBUG:
        buy_order=get_json(u"https://www.bitstamp.net/api/buy/", 
            data=urllib.urlencode({
                'user': bs_user, 
                'password': bs_pw, 
                'amount': str(amount), 
                'price': str(price)}))
        print "buy_order", buy_order
    else:
        print "DEBUG: buy order"

def place_ask(price, amount):
    print "placing ask", price, amount
    price=price.quantize(Decimal('.01'))
    amount=amount.quantize(Decimal('.00000001'), rounding=decimal.ROUND_DOWN)
    if not DEBUG:
        sell_order=get_json(u"https://www.bitstamp.net/api/sell/", 
            data=urllib.urlencode({
                'user': bs_user, 
                'password': bs_pw, 
                'amount': str(amount), 
                'price': str(price)}))
        print "sell_order", sell_order
    else:
        print "DEBUG: sell order"

def mtgox_query(url, data={}):
    nonce=str(time.time()*1000)
    data['nonce']=nonce

    hmac_sha512=hmac.new(base64.b64decode(mtgox_secret), data, hashlib.sh512())
    try:
        if data:
            f = urllib2.urlopen(
                url, data=data)
        else:
            f = urllib2.urlopen(
                url)
        result=f.read()
        final_json=json.loads(result)
        return final_json
    except Exception as inst:
        print "Unexpected error:", inst
        time.sleep(bs_seconds)
        return None

while True:
    last_total_btc=Decimal(0)
    try:
        weighted_prices=get_json(u"http://bitcoincharts.com/t/weighted_prices.json")
        if not weighted_prices:
            continue
        
        mtgox_order_book=get_json(u"https://mtgox.com/api/0/data/getDepth.php")
        if not mtgox_order_book:
            continue
        # mtgox_trades=get_json(u"https://mtgox.com/api/0/data/getDepth.php")
        # if not mtgox_trades:
        #     continue
        
        mtgox_order_book_eur=get_json(u"https://mtgox.com/api/0/data/getDepth.php?Currency=EUR")
        if not mtgox_order_book:
            continue

        bitstamp_ticker=get_json(u"https://www.bitstamp.net/api/ticker/")
        if not bitstamp_ticker:
            continue

        bitstamp_balance=get_json(u"https://www.bitstamp.net/api/balance/", 
            data=urllib.urlencode({
                'user': bs_user, 
                'password': bs_pw}))

        mtgox_info=mtgox_req.perform("info.php", {})
        if not mtgox_info:
            continue
        print mtgox_info

        eur24h_avg=Decimal(weighted_prices['EUR']['24h'])

        eur_balance=Decimal(mtgox_info['Wallets']['EUR'][u'Balance'][u'value'])
        btc_balance=Decimal(mtgox_info['Wallets']['BTC'][u'Balance'][u'value'])

        total_eur=btc_balance*eur24h_avg+eur_balance
        total_btc=btc_balance+(eur_balance/eur24h_avg)

        btc_tradable_balance=max(Decimal(0), btc_balance)

        print "btc_tradable_balance", btc_tradable_balance

        if last_total_btc!=round(total_btc, 5):
            status_output_file = open('trading_results.txt', 'a')

            status_output_file.write(str(round(total_eur, 2))+"\t"+str(round(total_btc, 5))+"\t"+\
                str(round(eur_balance, 2))+"\t"+str(round(btc_balance, 5))+"\t"+
                str(datetime.datetime.now())+"\n")
            
            status_output_file.close()

        last_total_btc=round(total_btc, 5)

        print "doing bitstamp trades"

        if Decimal(bitstamp_balance['usd_available'])<Decimal('5') and Decimal(bitstamp_balance['usd_balance'])>Decimal(50):
            print "canceling bitstamp buy orders"
            bitstamp_orders=get_json(u"https://www.bitstamp.net/api/open_orders/", 
                data=urllib.urlencode({
                'user': bs_user, 
                'password': bs_pw}))
            for order in bitstamp_orders:
                if int(order['type'])==0:
                    bitstamp_orders=get_json(u"https://www.bitstamp.net/api/cancel_order/", 
                        data=urllib.urlencode({
                        'user': bs_user, 
                        'password': bs_pw,
                        'id': order['id']}))

        if Decimal(bitstamp_balance['btc_available'])<Decimal('10') and Decimal(bitstamp_balance['btc_balance'])>Decimal(10):
            print "canceling bitstamp sell orders"
            bitstamp_orders=get_json(u"https://www.bitstamp.net/api/open_orders/", 
                data=urllib.urlencode({
                'user': bs_user, 
                'password': bs_pw}))
            for order in bitstamp_orders:
                if int(order['type'])==1:
                    bitstamp_orders=get_json(u"https://www.bitstamp.net/api/cancel_order/", 
                        data=urllib.urlencode({
                        'user': bs_user, 
                        'password': bs_pw,
                        'id': order['id']}))

        highest_bid=Decimal(bitstamp_ticker['bid'])
        lowest_ask=Decimal(bitstamp_ticker['ask'])

        usd24h_avg=Decimal(weighted_prices['USD']['24h'])
        usd7d_avg=Decimal(weighted_prices['USD']['24h'])

        final_bid=min(usd24h_avg*Decimal("0.995"), usd7d_avg*Decimal("0.995"), highest_bid)
        final_ask=max(usd24h_avg*Decimal("1.025"), usd7d_avg*Decimal("1"), lowest_ask)

        place_bid(final_bid, Decimal("0.6"))
        # place_ask(final_ask, Decimal("0.4"))

        print "bitstamp trades done"

        print "canceling mtgox trades..."
        mtgox_orders=mtgox_req.perform("getOrders.php", {})
        if not mtgox_orders:
            continue
        print mtgox_orders
        for o in mtgox_orders['orders']:
            print mtgox_req.perform("cancelOrder.php", {'oid': o['oid'], 'type': o['type']})

        print "canceled orders, now setup new orders"

        mtgox_max_bid_eur=Decimal(0)
        bids=mtgox_order_book_eur["bids"]
        total_bid_amount=Decimal(0)
        for bid in reversed(bids):
            bid_price=Decimal(str(bid[0]))
            bid_amount=Decimal(str(bid[1]))
            total_bid_amount+=Decimal(str(bid[0]))*Decimal(str(bid[1]))
            if total_bid_amount>Decimal(5):
                #print "bid", bid
                mtgox_max_bid_eur=bid_price-Decimal("0.00005")
                print "max bid", mtgox_max_bid_eur
                break
        
        mtgox_min_ask_eur=Decimal(0)
        asks=mtgox_order_book_eur["asks"]
        total_bid_amount=Decimal(0)
        for ask in asks:
            ask_price=Decimal(str(ask[0]))
            ask_amount=Decimal(str(ask[1]))
            total_bid_amount+=Decimal(str(ask[0]))*Decimal(str(ask[1]))
            if total_bid_amount>Decimal(5):
                #print "bid", bid
                mtgox_min_ask_eur=ask_price+Decimal("0.00005")
                print "min ask", mtgox_min_ask_eur
                break
        
        bid_value=min(mtgox_max_bid_eur+Decimal("0.00001"), eur24h_avg*Decimal("0.995"))
        eur_amount=(min(eur_balance*Decimal("0.19"), Decimal("34.99")))

        percent=Decimal("100.0")
        i=0
        while percent>Decimal(75) and eur_balance>eur_amount:
            real_bid_value=(percent*bid_value)/Decimal("100.0")
            btc_amount=(eur_amount/real_bid_value)
            eur_balance-=eur_amount
            print "doing trade", real_bid_value, eur_amount, btc_amount
            print mtgox_req.perform("buyBTC.php", {'amount': str(btc_amount), 'price': str(real_bid_value), 'Currency': 'EUR'})
            percent-=Decimal(math.log(Decimal(i)+Decimal("1.1")))/3
            eur_amount+=Decimal(math.log(Decimal(i)+Decimal("1.1")))
            if i>10:
                break;
            i+=1
        
        ask_value=max(mtgox_min_ask_eur, eur24h_avg*Decimal("1.03"))
        eur_amount=(min(btc_tradable_balance*Decimal("0.19")*ask_value, Decimal("24.99")))
        btc_amount=eur_amount/ask_value

        print "sellstats", ask_value, eur_amount, btc_amount

        percent=Decimal("100.0")
        i=0
        while percent<Decimal(1000) and btc_tradable_balance>btc_amount:
            real_ask_value=(percent*ask_value)/Decimal("100.0")
            btc_amount=(eur_amount/real_ask_value)
            btc_tradable_balance-=btc_amount
            #print "selling btc", real_ask_value, eur_amount, btc_amount
            #print mtgox_req.perform("sellBTC.php", {'amount': str(btc_amount), 'price': str(real_ask_value), 'Currency': 'EUR'})
            percent+=Decimal(math.log(Decimal(i)+Decimal("1.1")))
            eur_amount+=Decimal(math.log(Decimal(i)+Decimal("1.1")))
            if i>10:
                break;
            i+=1



    except:
        print "some exception", sys.exc_info()[0]

    time.sleep(30+random.randint(0, 3*60))
