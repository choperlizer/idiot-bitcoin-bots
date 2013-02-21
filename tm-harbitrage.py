#!/usr/bin/python

# The Money Hoard 0.00.01 - bitcoin arbitrage bot
# Copyright by Toni Heinonen <toni.heinonen@iki.fi>
# No rights reserved, in the public domain

import urllib2
import json

exchanges = [
  { 'name': 'mtgox',
    'fee': 0.006,
    'usdurl': 'https://mtgox.com/api/0/data/getDepth.php' },
  { 'name': 'tradehill',
    'fee': 0.006,
     'usdurl': 'https://api.tradehill.com/APIv1/USD/Orderbook' },
  { 'name': 'bitcoin7',
    'fee': 0.0057,
     'usdurl': 'http://bitcoin7.com/api/public/getDepth.php?currency=usd' },
  { 'name': 'exchb',
    'fee': 0.0054,
     'usdurl': 'https://www.exchangebitcoins.com/data/depth' },
# TODO how does the api of this exchange work...
#  { 'name': 'btcex',
#    'fee': %,
#     'usdurl': '' },
  { 'name': 'campbx',
    'fee': 0.0055,
     'usdurl': 'http://CampBX.com/api/xdepth.php' }
  ]

asks = []
bids = []

for exchange in exchanges:
    data = json.load(urllib2.urlopen(exchange['usdurl']))
    for key in data.keys():
        if 'ask' in key.lower():
            for ask in data[key]:
                asks.append({
                    'usd': float(ask[0]),
                    'btc': float(ask[1]),
                    'exchange': exchange['name']})
        elif 'bid' in key.lower():
            for bid in data[key]:
                bids.append({
                    'usd': float(bid[0]),
                    'btc': float(bid[1]),
                    'exchange': exchange['name']})
        else:
            print 'strange key [%s] in JSON data from exchange [%s]' % (key, exchange['name'])

sorted_asks = sorted(asks, key=lambda k: k['usd'])
sorted_bids = sorted(bids, key=lambda k: k['usd'], reverse=True)

for i in range(10):
    print "ask usd [%f] btc [%f] exchange [%s]" % (sorted_asks[i]['usd'], sorted_asks[i]['btc'], sorted_asks[i]['exchange'])
for i in range(10):
    print "bid usd [%f] btc [%f] exchange [%s]" % (sorted_bids[i]['usd'], sorted_bids[i]['btc'], sorted_bids[i]['exchange'])
