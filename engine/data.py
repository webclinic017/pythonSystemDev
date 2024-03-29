#!/usr/bin/python
# -*- coding: utf-8 -*-

import datetime
import os, os.path
import numpy as np
import pandas as pd

from abc import ABCMeta, abstractmethod
from event import MarketEvent

class DataHandler(object):
 #interface for data handlers (live and historic)
 #generates set of bars (OHLCVI)

 __metaclass__ = ABCMeta #lets Python know its Abstract Class

 @abstractmethod # lets Python know method will be overridden in subclasses
 def get_latest_bar(self, symbol, N=1):
  # returns the last bar updated
  raise NotImplementedError("Should implement get_latest_bar()")

 @abstractmethod
 def get_latest_bars(self, symbol, N=1):
  #returns the last N bars updated
  raise NotImplementedError("Should implement get_latest_bars()")

 @abstractmethod
 def get_latest_bar_datetime(self, symbol):
  #returns datetime object for last bar
  raise NotImplementedError("Should implement get_latest_bar_datetime()")

 @abstractmethod
 def get_latest_bar_value(self, symbol, val_type):
  #returns one of OHLCVI from last bar
  raise NotImplementedError("Should implement get_latest_bar_value()")

 @abstractmethod
 def get_latest_bars_values(self, symbol, val_type, N=1):
  #returns the last N bar values, or N-k if less available
  raise NotImplementedError("Should implement get_latest_bars_values()")

 @abstractmethod
 def update_bars(self):
  #pushes latest bars to bars_queue for each symbol in a tuple OHLCVI
  raise NotImplementedError("Should implement update_bars()")

class HistoricCSVDataHandler(DataHandler):
 #read and process CSV files
 def __init__(self, events, csv_dir, symbol_list):
  #assumes all files are of the form 'symbol.csv'
  self.events = events # the event queue
  self.csv_dir = csv_dir #absolute path to dir
  self.symbol_list = symbol_list #list of symbol strings
  self.symbol_data = {}
  self.latest_symbol_data = {}
  self.continue_backtest = True
  self._open_convert_csv_files()

 def _open_convert_csv_files(self):
  #opens csv files and converts into pandas dataframes (DTN IQfeed format)
  comb_index = None
  for s in self.symbol_list:
   #load csv, indexed on date
   self.symbol_data[s] = pd.io.parsers.read_csv(os.path.join(self.csv_dir,'%s.csv' %s), header=0, index_col=0, parse_dates=True, names=['datetime','open','low','high','close','volume','oi']).sort()
   #combine the index to pad forward values
   if comb_index is None:
    comb_index = self.symbol_data[s].index
   else:
    comb_index.union(self.symbol_data[s].index)
   
   self.symbol_data[s]['returns'] = self.symbol_data[s]['close'].pct_change()
   #set the latest symbol_data to None
   self.latest_symbol_data[s]=[]

  #reindex the dataframes
  for s in self.symbol_list:
   self.symbol_data[s] = self.symbol_data[s].reindex(index=comb_index, method='pad').iterrows()

 def _get_new_bar(self, symbol):
 #returns the latest bar from the datafeed
  for b in self.symbol_data[symbol]:
   yield b

 def get_latest_bar(self,symbol):
 #returns the last bar from the latest_symbol list
  try:
   bars_list = self.latest_symbol_data[symbol]
  except KeyError:
   print "That symbol is not available in the historical dataset."
   raise
  else:
   return bars_list[-1]

 def get_latest_bars(self, symbol, N=1):
  #returns the last N bars from the latest_symbol list
  try:
   bars_list = self.latest_symbol_data[symbol]
  except KeyError:
   "That symbol is not available in the historical dataset."
   raise
  else:
   return bars_list[-N:]

 def get_latest_bar_datetime(self, symbol):
 # returns a python datetime object for last bar
  try:
   bars_list = self.latest_symbol_data[symbol]
  except KeyError:
   print "That symbol is not available in the historical dataset."
   raise
  else:
   return bars_list[-1][0]

 def get_latest_bar_value(self, symbol, val_type):
  # returns one of the OHLCVI values from the pandas bar series object
  try:
   bars_list = self.latest_symbol_data[symbol]
  except KeyError:
   print "That symbol is not available in the historical dataset"
   raise
  else:
   return getattr(bars_list[-1][1], val_type)

 def get_latest_bars_values(self, symbol, val_type, N=1):
  #returns the N bars values from the latest symbol list
  try:
   bars_list = self.get_latest_bars(symbol, N)
  except KeyError:
   print "That symbol is not available in the historical dataset"
   raise
  else:
   return np.array([getattr(b[1], val_type) for b in bars_list])

 def update_bars(self):
  #pushes the latest bar to the latest_symbol_data for all symbols in list
  for s in self.symbol_list:
   try:
    bar = self._get_new_bar(s).next()
   except StopIteration:
    self.continue_backtest = False
   else:
    if bar is not None:
     self.latest_symbol_data[s].append(bar)
  self.events.put(MarketEvent())

 def prime_bars(self):
  """ Primes the bars for the indicator calculations. No MarketEvent Signal
  generated.
  """
  for s in self.symbol_list:
   try:
    bar = self._get_new_bar(s).next()
   except StopIteration:
    self.continue_backtest = False
   else:
    if bar is not None:
     self.latest_symbol_data[s].append(bar)
