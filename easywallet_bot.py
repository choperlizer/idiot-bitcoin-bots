Import os
import os.path
import urllib
import json
import socket
import re
import select
import sys
import codecs
import commands
import urllib2
import random
from time import sleep
import datetime
import math
from decimal import Decimal
import subprocess

from ewsettings import SITE_URL

API_URL = SITE_URL+'/api/v1/'
LINE_DELIMITER = '\r\n'

def call_api(url_suffix, data = None):
    f = urllib.urlopen(API_URL + url_suffix, data)
    data = f.read()
    print data
    return json.loads(data)

def initiate_payment(cmd, wallet_id):
    params = cmd.split(" ")
    if not len(params) > 2:
        return "Not enough parameters"
    try:
        address = params[1]
        amount = str(params[2])
    except ValueError:
        return "Unable to parse amount"

    post_data = urllib.urlencode({'address': address, 'amount': amount})
    result = call_api('w/%s/payment' % wallet_id, post_data)
    return result['message']

def format_btc_amount(amount):
    s = "%.8f" % (float(amount))
    return re.sub("\.?0+$", "", s)

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

# check for configuration file to load wallet_id from
conffile = os.path.join(os.environ['HOME'], '.iw-console')
if os.path.isfile(conffile):
    with open(conffile, 'r') as f:
        wallet_id = f.readline().strip()
else:
    # looks like no configuration exists -> create new wallet
    wallet_id = call_api('new_wallet', urllib.urlencode({'a': "a",}))['wallet_id']
    with open(conffile, 'w') as f:
        f.write("%s\n" % wallet_id)

# output info
wallet_bitcoin_address=call_api('w/%s/address' % wallet_id)['address']
print "Using "+SITE_URL+"/w/%s" % wallet_id
print "Bitcoin address is: %s" % wallet_bitcoin_address
# print "To do a payment try: payment <address> <amount in BTC>"

# subscribe to balance updates
#subscription_id = call_api('w/%s/subscription' % wallet_id, "")['subscription_id']
#request = json.dumps({'subscription_id': subscription_id})
#s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#s.connect(('www.instawallet.org', 8202))
#s.send(request + LINE_DELIMITER)

use_currency = "EUR"
use_average = "24h"

weighted_prices=get_json(u"http://bitcoincharts.com/t/weighted_prices.json")
if not weighted_prices:
    print "Error, can't fetch exchange rates"
    exit(0)

rate=Decimal(weighted_prices[use_currency][use_average])

min_wallet_amount=Decimal("30")
max_wallet_amount=Decimal("60")

balance_array = call_api('w/%s/balance_unconfirmed' % wallet_id)
balance=balance_array['balance_unconfirmed']
bal=Decimal(balance)
bal_currency=(bal*rate)
print "Balance (unconfirmed): %s BTC (%.2f %s)" % (format_btc_amount(balance), bal_currency, use_currency)

if bal_currency<min_wallet_amount:
    transfer_amount_currency=Decimal(str(random.uniform(float(min_wallet_amount-bal_currency), float(max_wallet_amount-bal_currency)))).quantize(Decimal("0.01"))
    transfer_amount=(transfer_amount_currency/rate).quantize(Decimal("0.01"))
    print "Initiating outgoing transfer of amount %.2f BTC (%.2f %s)" % (transfer_amount, transfer_amount_currency, use_currency)
    p = subprocess.Popen(['bitcoind', 'sendtoaddress', wallet_bitcoin_address,  str(transfer_amount)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = p.communicate()
    print out
    print "Payment complete"
    exit(0)

balance=balance_array['balance']
print "Balance (confirmed): %s BTC (%.2f %s)" % (format_btc_amount(balance), bal_currency, use_currency)
bal=Decimal(balance)
bal_currency=(bal*rate)

if bal_currency>max_wallet_amount:
    transfer_amount_currency=Decimal(str(random.uniform(float(bal_currency-min_wallet_amount), float(bal_currency-max_wallet_amount)))).quantize(Decimal("0.01"))
    transfer_amount=(transfer_amount_currency/rate).quantize(Decimal("0.01"))
    print "Initiating incoming transfer of amount %.2f BTC (%.2f %s)" % (transfer_amount, transfer_amount_currency, use_currency)
    p = subprocess.Popen(['bitcoind', 'getnewaddress'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = p.communicate()
    print out
    my_bitcoin_address=out.strip()
    print "my own bitcoin address", my_bitcoin_address
    initiate_payment("payment "+my_bitcoin_address+" "+str(transfer_amount), wallet_id)
    print "withdraw initiated: "+my_bitcoin_address+" "+str(transfer_amount)
    exit(0)
    # p = subprocess.Popen('ls', shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    # for line in p.stdout.readlines():
    #     print line,
    # retval = p.wait()

print "Balance good, nothing to do."

# enter select loop: check both for keyboard
# input and balance updates on the socket
# while True:
#     cmd=raw_input('Command: ')
#     if cmd.startswith('payment'):
#         print initiate_payment(cmd, wallet_id)
#     elif cmd.startswith('bal'):
#         balance = call_api('w/%s/balance' % wallet_id)['balance']
#         print "Balance: %s BTC" % format_btc_amount(balance)
#     else:
#         print "Command not recognized"
