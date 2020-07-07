import argparse
import datetime
import os

import backtrader as bt
import matplotlib.pyplot as plt
import akshare as ak

from utils.ak import get_ak_stock_zh_a_daily
from utils.utils import set_matplotlib_font


set_matplotlib_font()


class TestStrategy(bt.Strategy):

    params = (
        ("maperiod", 15),
        ("printlog", False),
    )

    def log(self, txt, dt=None, doprint=False):
        if self.params.printlog or doprint:
            dt = dt or self.datas[0].datetime.date(0)
            print("%s, %s" % (dt.isoformat(), txt))

    def __init__(self):
        self.dataclose = self.datas[0].close

        self.order = None
        self.buy_price = None
        self.buy_comm = None

        self.sma = bt.indicators.SimpleMovingAverage(
            self.datas[0], period=self.params.maperiod
        )

        bt.indicators.ExponentialMovingAverage(self.datas[0], period=25)
        bt.indicators.WeightedMovingAverage(self.datas[0], period=25, subplot=True)
        bt.indicators.StochasticSlow(self.datas[0])
        bt.indicators.MACDHisto(self.datas[0])
        rsi = bt.indicators.RSI(self.datas[0])
        bt.indicators.SmoothedMovingAverage(rsi, period=10)
        bt.indicators.ATR(self.datas[0], plot=False)

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status in [order.Completed]:
            if order.isbuy():
                self.log("BUY EXECUTED, Price: %.2f, Cost: %.2f, Comm %.2f" % (
                    order.executed.price,
                    order.executed.value,
                    order.executed.comm
                ))
                self.buyprice = order.executed.price
                self.buycomm = order.executed.comm
            elif order.issell():
                self.log("SELL EXECUTED, Price: %.2f, Cost: %.2f, Comm %.2f" % (
                    order.executed.price,
                    order.executed.value,
                    order.executed.comm
                ))
            self.bar_executed = len(self)

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log("Order Canceled/Margin/Rejected")

        self.order = None

    def notify_trade(self, trade):
        if not trade.isclosed:
            return
        self.log("OPERATION PROFIT, GROSS %.2f, NET %.2f" % (trade.pnl, trade.pnlcomm))

    def next(self):
        self.log("Close, %.2f" % self.dataclose[0])

        if self.order:
            return

        if not self.position:
            if self.dataclose[0] > self.sma[0]:
                self.log("BUY CREATE, %.2f" % self.dataclose[0])
                self.order = self.buy()
        else:
            if self.dataclose[0] < self.sma[0]:
                self.log("SELL CREATE, %.2f" % self.dataclose[0])
                self.order = self.sell()
        return

    def stop(self):
        self.log("(MA Period %2d) Ending Value %.2f" % (self.params.maperiod, self.broker.getvalue()), doprint=True)


def main():

if __name__ == "__main__":

    """

# 恒生电子
python -m main.test_1 --symbol sh600570

# 万华化学
python -m main.test_1 --symbol sh600309

# 中航沈飞
python -m main.test_1 --symbol sh600760

    """

    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", type=str, required=True)
    parser.add_argument("--cache_dir", type=str, default="D:/Qingyu/Repos/stock/cache")
    parser.add_argument("--update", action="store_true")
    args = parser.parse_args()

    if not os.path.isdir(args.cache_dir):
        os.mkdir(args.cache_dir)
        print("=" * 80)
        print("mkdir => %s" % args.cache_dir)

    stock_data = get_ak_stock_zh_a_daily(symbol=args.symbol, cache_dir=args.cache_dir, adjust="qfq", update=args.update)
    print("Fetch Date (%s)" % args.symbol)

    # Main
    cerebro = bt.Cerebro()

    cerebro.addstrategy(TestStrategy)

    date_start = datetime.datetime(2020, 1, 1)
    date_final = datetime.datetime(2020, 6, 24)
    data = bt.feeds.PandasData(
        dataname=stock_data,
        fromdate=date_start,
        todate=date_final
    )
    cerebro.adddata(data)

    cerebro.broker.setcash(10000)
    cerebro.addsizer(bt.sizers.FixedSize, stake=100)
    cerebro.broker.setcommission(commission=0.002)

    portfolio_start = cerebro.broker.getvalue()
    cerebro.run()
    portfolio_final = cerebro.broker.getvalue()

    rate_of_return = (portfolio_final - portfolio_start) / portfolio_start * 100
    total_days = (date_final - date_start).days
    annualized_rate_of_return = rate_of_return / total_days * 365
    print("Start Portfolio Value: %.2f" % portfolio_start)
    print("Final Portfolio Value: %.2f" % portfolio_final)
    print("Rate of Return: %.2f%%" % rate_of_return)
    print("Annualized Rate of Return: %.2f%% (%s days)" % (annualized_rate_of_return, total_days))

    cerebro.plot()
