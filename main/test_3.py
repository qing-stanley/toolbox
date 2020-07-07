import argparse
import datetime
import os

import backtrader as bt
import matplotlib.pyplot as plt
import akshare as ak

from utils.ak import get_ak_stock_zh_a_daily
from utils.utils import set_matplotlib_font


set_matplotlib_font()


class TestSizer(bt.Sizer):

    params = (
        ("stake", 1),
    )

    def _getsizing(self, comminfo, cash, data, isbuy):
        if isbuy:
            return self.params.stake
        position = self.broker.getposition(data)
        if not position.size:
            return 0
        else:
            return position.size
        return self.params.stakeclass


class TestStrategy(bt.Strategy):

    params = (
        ("printlog", False),
    )

    def log(self, txt, dt=None, doprint=False):
        if self.params.printlog or doprint:
            dt = dt or self.datas[0].datetime.date(0)
            print("%s, %s" % (dt.isoformat(), txt))

    def __init__(self):
        self.dataclose = self.datas[0].close
        self.datahigh = self.datas[0].high
        self.datalow = self.datas[0].low

        self.order = None
        self.buyprice = 0
        self.buycomm = 0

        self.newstake = 0
        self.buytime = 0

        # 参数计算，唐奇安通道上轨、唐奇安通道下轨、ATR
        self.DonchianHi = bt.indicators.Highest(self.datahigh(-1), period=20, subplot=False)
        self.DonchianLo = bt.indicators.Lowest(self.datalow(-1), period=10, subplot=False)
        self.TR = bt.indicators.Max((self.datahigh(0)- self.datalow(0)), abs(self.dataclose(-1) -   self.datahigh(0)), abs(self.dataclose(-1)  - self.datalow(0) ))
        self.ATR = bt.indicators.SimpleMovingAverage(self.TR, period=14, subplot=True)

        # 唐奇安通道上轨突破、唐奇安通道下轨突破
        self.CrossoverHi = bt.ind.CrossOver(self.dataclose(0), self.DonchianHi)
        self.CrossoverLo = bt.ind.CrossOver(self.dataclose(0), self.DonchianLo)

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status in [order.Completed]:
            if order.isbuy():
                self.log("BUY EXECUTED, Price: %.2f, Cost: %.2f, Comm %.2f" % (
                    order.executed.price,
                    order.executed.value,
                    order.executed.comm
                ), doprint=True)
                self.buyprice = order.executed.price
                self.buycomm = order.executed.comm
            else:
                self.log("SELL EXECUTED, Price: %.2f, Cost: %.2f, Comm %.2f" % (
                    order.executed.price,
                    order.executed.value,
                    order.executed.comm
                ), doprint=True)
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

        # 入场
        if self.CrossoverHi > 0 and self.buytime == 0:
            self.newstake = self.broker.getvalue() * 0.01 / self.ATR
            self.newstake = int(self.newstake / 100) * 100
            self.sizer.p.stake = self.newstake
            self.buytime = 1
            self.order = self.buy()
        # 加仓
        elif self.datas[0].close >self.buyprice+0.5*self.ATR[0] and self.buytime > 0 and self.buytime < 5:
            self.newstake = self.broker.getvalue() * 0.01 / self.ATR
            self.newstake = int(self.newstake / 100) * 100
            self.sizer.p.stake = self.newstake
            self.order = self.buy()
            self.buytime = self.buytime + 1
        # 出场
        elif self.CrossoverLo < 0 and self.buytime > 0:
            self.order = self.sell()
            self.buytime = 0
        # 止损
        elif self.datas[0].close < (self.buyprice - 2*self.ATR[0]) and self.buytime > 0:
            self.order = self.sell()
            self.buytime = 0

    def stop(self):
        self.log("Ending Value %.2f" % self.broker.getvalue(), doprint=True)


if __name__ == "__main__":

    """

# 恒生电子
python -m main.test_3 --symbol sh600570

# 万华化学
python -m main.test_3 --symbol sh600309

# 中航沈飞
python -m main.test_3 --symbol sh600760

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

    date_start = datetime.datetime(2020, 3, 1)
    date_final = datetime.datetime(2020, 6, 29)
    data = bt.feeds.PandasData(
        dataname=stock_data,
        fromdate=date_start,
        todate=date_final
    )
    cerebro.adddata(data)

    cerebro.broker.setcash(20000)
    cerebro.addsizer(TestSizer)
    cerebro.broker.setcommission(commission=0.002)

    cerebro.addanalyzer(bt.analyzers.SharpeRatio,_name = 'SharpeRatio')
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='DW')


    portfolio_start = cerebro.broker.getvalue()
    results = cerebro.run()
    portfolio_final = cerebro.broker.getvalue()

    rate_of_return = (portfolio_final - portfolio_start) / portfolio_start * 100
    total_days = (date_final - date_start).days
    annualized_rate_of_return = rate_of_return / total_days * 365
    print("Start Portfolio Value: %.2f" % portfolio_start)
    print("Final Portfolio Value: %.2f" % portfolio_final)
    print("Rate of Return: %.2f%%" % rate_of_return)
    print("Annualized Rate of Return: %.2f%% (%s days)" % (annualized_rate_of_return, total_days))

    strategy = results[0]
    print("SR:", strategy.analyzers.SharpeRatio.get_analysis())
    print("DW:", strategy.analyzers.DW.get_analysis())

    cerebro.plot()
