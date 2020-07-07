import os

import akshare as ak
import pandas as pd


def get_ak_stock_zh_a_daily(symbol, cache_dir, adjust=None, update=False):
    cache_path = "%s/ak_stock_zh_a_daily-%s.pkl" % (cache_dir, symbol)
    if os.path.isfile(cache_path) and not update:
        stock_data = pd.read_pickle(cache_path)
    else:
        stock_data = ak.stock_zh_a_daily(symbol=symbol, adjust=adjust)
        stock_data.to_pickle(cache_path)
    return stock_data
