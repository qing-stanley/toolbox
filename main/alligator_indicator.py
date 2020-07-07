import numpy as np

# +------------+
# | Initialize |
# +------------+
# Function for Moving Average
def calculate_sma(price, n, m=0):
    """
    n: n period - calculate period
    m: m period - moving period
    """
    if m != 0: price = price[:-m]
    price = price[-n:]
    sma = price.mean()
    return sma


def calculate_ema(price, n, m=0):
    """
    n: n period - calculate period
    m: m period - moving period
    """
    if m != 0: price = price[:-m]
    price = price[-n:]
    
    ema_i = price[0]
    
    for i in range(n):
        
        day = i+1
        alpha = 2./(day+1)
        
        ema_i = ema_i*(1-alpha) + price[i]*alpha

    return ema_i


def calculate_ma(price, n, m, mode='sma'):
    if mode == 'sma':
        ma = calculate_sma(price, n, m)
    if mode == 'ema':
        ma = calculate_ema(price, n, m)
    return ma

# Function for Alligator Indicator
def check_sleeping(stock, nday):
    
    is_sleeping = False

    close = attribute_history(security=stock, count=30+nday, unit='1d', fields='close', df=False)['close']

    for day in range(nday):
        # Blue  Alligator’s Jaw   [13 bars SMMA(SMA) moved into the future by 8 bars]
        ma_b = calculate_ma(price=close, n=13, m=8, mode='sma')
        # Red   Alligator’s Teeth [ 8 bars SMMA(SMA) moved into the future by 5 bars]
        ma_r = calculate_ma(price=close, n=8,  m=5, mode='sma')
        # Green Alligator’s Lips  [ 5 bars SMMA(SMA) moved into the future by 3 bars]
        ma_g = calculate_ma(price=close, n=5,  m=3, mode='sma')

        if abs(ma_b/ma_r-1) < 0.02 and abs(ma_r/ma_g-1) < 0.02:
            
            is_sleeping = True
            
            break

        close = close[:-1] # check nday before

    return is_sleeping
    

# Function Excuted Monthly
def check_monthly(context):
    
    # Excute Every 3 Month
    month_current = context.current_dt.month
    if (month_current - g.month_start) % 3 != 0: return

    # Reset Position
    for stock in g.stock_list_bought:
        order_target(security=stock, amount=0)
        log.info('[Reset Position] {}'.format(stock))

    # Reset Global Parameters
    g.price_high = {}   # 向上碎形最高价
    g.price_low  = {}   # 向下碎形最低价
    
    g.fractal_up   = {} # 判断有效向上碎形
    g.fractal_down = {} # 判断有效向下碎形
    
    g.AO_indicator = {} # 存放连续的AO指标数据
    g.AC_indicator = {} # 存放连续的AC指标数据
    g.amount       = {} # 满仓仓位
    
    g.stock_list_bought = []

    # Get History Record (Duration: 30 days, Interval: 1 day)
    for stock in g.stock_list:

        is_sleeping = check_sleeping(stock, nday=20)
        
        if is_sleeping:
            
            g.stock_list_bought.append(stock)
            
            # Initial Stock Info
            g.price_high[stock] = 0 # 向上碎形最高价
            g.price_low[stock]  = 0 # 向下碎形最低价

            g.fractal_up[stock]   = False # 判断有效向上碎形
            g.fractal_down[stock] = False # 判断有效向下碎形
            
            g.AO_indicator[stock] = [0] # 存放连续的AO指标数据
            g.AC_indicator[stock] = [0] # 存放连续的AC指标数据
            g.amount[stock]       = 0   # 满仓仓位
    
    return None


# Main
def initialize(context):

    g.price_high = {}           # 向上碎形最高价
    g.price_low  = {}           # 向下碎形最低价
    
    g.fractal_up   = {}         # 判断有效向上碎形
    g.fractal_down = {}         # 判断有效向下碎形
    
    g.AO_indicator = {}         # 存放连续的AO指标数据
    g.AC_indicator = {}         # 存放连续的AC指标数据

    g.amount = {}               # 满仓仓位
    g.stock_list_bought = []
    
    g.market_index = '000300.XSHG' # 沪深300
    g.stock_list = get_index_stocks(g.market_index)   
    
    set_benchmark(g.market_index)
    
    g.month_start = context.current_dt.month
    
    run_monthly(check_monthly, 1, 'open')

    return


# +-------------+
# | Handle Data |
# +-------------+
# Function for Market Return
def calculate_market_return(market_index, duration):
    """
    计算大盘n日收益率
    """
    hist = attribute_history(security=market_index, count=duration+1, unit='1d', fields='close', df=False)
    
    close_t = hist['close'][-1]
    close_0 = hist['close'][0]
    
    market_return = (close_t-close_0)/close_0
    
    return market_return


def conduct_market_stop_loss(market_index, duration, min_return):
    """
    大盘止损
    """
    market_return = calculate_market_return(market_index, duration)
    
    if market_return <= min_return:
        for stock in g.stock_list_bought:
            order_target(security=stock, amount=0)
            log.info('[Stop Loss] Sell {}'.format(stock))
        return True
    
    else:
        return False


# Function for Stock Return
def calculate_stock_return(context, data, stock):
    """
    计算个股累计收益率
    """
    stock_return = None

    if stock in context.portfolio.positions:

        price_bought  = context.portfolio.positions[stock].avg_cost
        price_current = data[stock].avg

        if price_bought != 0:
            stock_return = (price_current-price_bought)/price_bought
    
    return stock_return


def conduct_stock_stop_loss(context, data, stock, min_return):
    """
    个股止损
    """
    stock_return = calculate_stock_return(context, data, stock)

    if stock_return is not None and stock_return < min_return:
        order_target(security=stock, amount=0)
        log.info('[Stop Loss] Sell {}'.format(stock))
        return True
    
    else:
        return False


def conduct_stock_take_profit(context, data, stock, max_return):
    """
    个股止盈
    """
    stock_return = calculate_stock_return(context, data, stock)
    
    if stock_return is not None and stock_return > max_return:
        order_target(security=stock, amount=0)
        log.info('[Take Profit] Sell {}'.format(stock))
        return True
    
    else:
        return False


# Function for AO Indicator
def calculate_AO_indicator(stock):
    """
    MEDIAN = (HIGH + LOW) / 2
    AO = SMA (MEDIAN, 5) - SMA (MEDIAN, 34)
    """
    hist = attribute_history(security=stock, count=35, unit='1d', fields=['high', 'low'], df=False)
    price_median = (hist['high']+hist['low'])/2

    mid_sma_5d  = calculate_sma(price=price_median, n=5,  m=0)
    mid_sma_34d = calculate_sma(price=price_median, n=34, m=0)

    AO = mid_sma_5d - mid_sma_34d

    g.AO_indicator[stock].append(AO)

    return


# Function for AC Indicator
def calculate_AC_indicator(stock):
    """
    AC = AO - SMA (AO, 5)
    """
    calculate_AO_indicator(stock)

    if len(g.AO_indicator[stock]) >= 5:

        AO = g.AO_indicator[stock][-1]

        price_AO = np.array(g.AO_indicator[stock])

        sma_AO_5d = calculate_sma(price=price_AO, n=5)

        AC = AO - sma_AO_5d

        g.AC_indicator[stock].append(AC)

    return


# Function for Fractal Indicator
def check_fractal_indicator(stock, direction):

    hist_close = attribute_history(security=stock, count=30, unit='1d', fields='close', df=False)['close']
    
    # Red Alligator’s Teeth [ 8 bars SMMA(SMA) moved into the future by 5 bars]
    ma_r = calculate_ma(price=hist_close, m=8, n=5, mode='sma')

    if direction == 'up':
        
        hist_high  = attribute_history(security=stock, count=5, unit='1d', fields='high', df=False)['high']

        if max(hist_high) == hist_high[2] and sum(hist_high==hist_high[2]) == 1:
            
            high = hist_high[2]
            
            g.price_high[stock] = high

            if high > ma_r:
                g.fractal_up[stock] = True
            else:
                g.fractal_up[stock] = False

    if direction == 'down':
        
        hist_low  = attribute_history(security=stock, count=5, unit='1d', fields='low', df=False)['low']

        if min(hist_low) == hist_low[2] and sum(hist_low==hist_low[2]) == 1:
            
            low = hist_low[2]

            g.price_low[stock] = low
        
            if low < ma_r:
                g.fractal_down[stock] = True
            else:
                g.fractal_down[stock] = False

    return


def is_fractal_broken(stock, direction):
    
    close = attribute_history(security=stock, count=1, unit='1d', fields='close', df=False)['close'][0]

    if direction == 'up':

        if close > g.price_high[stock]:
        
            return True

    if direction == 'down':
        
        if close < g.price_low[stock]:
            
            return True

    return False


def is_up_going(check_list, nday):
    """
    判断n日上行
    """
    if len(check_list) < nday:
        
        return False
    for i in range(nday-1):
        if check_list[i] > check_list[i+1]:
            return False
    return True


def is_down_going(check_list, nday):
    """
    判断n日下行
    """
    if len(check_list) < nday:
        return False
    for i in range(nday-1):
        if check_list[i] < check_list[i+1]:
            return False
    return True


def initial_position(stock, context):

    current_data = get_current_data()
    last_price = current_data[stock].last_price

    available_share = np.floor(context.portfolio.available_cash/last_price)

    if available_share >= 100:
        
        share = 100
        
        g.amount[stock] = share

        order(security=stock, amount=share)

        log.info('[Initial Position] Buy {} shares of {}'.format(share, stock))
    
        g.fractal_down[stock] = False

    return


def clear_position(stock, context):
    
    order_target(security=stock, amount=0)

    log.info('[Clear Position] Sell all shares of {}'.format(stock))

    g.fractal_up[stock] = False

    return


def adjust_position(stock, context, ratio):

    current_data = get_current_data()
    last_price = current_data[stock].last_price

    available_share = np.floor(context.portfolio.available_cash/last_price)
    
    adjust_share = np.ceil(g.amount[stock]*ratio/100)*100

    if adjust_share <= available_share:

        order(security=stock, amount=adjust_share)

        log.info('[Adjust Position] Buy {} shares of {}'.format(adjust_share, stock))

    return


# Main
def handle_data(context, data):
    """
    日常任务
    """
    log.info('[Portfolio] Available Cash {}'.format(context.portfolio.available_cash))

    # [大盘止损]
    is_market_stop_loss = conduct_market_stop_loss(market_index=g.market_index, duration=3, min_return=-0.3)
    
    if is_market_stop_loss: return
    
    for stock in g.stock_list_bought:
        
        # [个股止损]
        is_stock_stop_loss   = conduct_stock_stop_loss(context, data, stock, min_return=-0.1)
        # [个股止盈]
        is_stock_take_profit = conduct_stock_take_profit(context, data, stock, max_return=0.3)
        
        if is_stock_stop_loss or is_stock_take_profit: continue

        # [计算AO & AC指标]
        calculate_AC_indicator(stock)
        
        # [空仓 - 建仓]
        if stock not in context.portfolio.positions:
            
            # [检查向上碎形]
            check_fractal_indicator(stock, 'up')

            # [检查向上碎形是否被突破]
            if g.fractal_up[stock]:

                if is_fractal_broken(stock,'up'):

                    hist_close = attribute_history(security=stock, count=5, unit='1d', fields='close', df=False)['close']
                    
                    if  is_up_going(check_list=g.AO_indicator[stock], nday=5) and \
                        is_up_going(check_list=g.AC_indicator[stock], nday=3) and \
                        is_up_going(check_list=hist_close, nday=2):
                        
                        # [建仓]
                        initial_position(stock, context)
        
        # [持仓 - 调整 or 清仓]
        else:

            # [检查向下碎形]
            check_fractal_indicator(stock, 'down')

            # [检查向下碎形是否被突破]
            if g.fractal_down[stock]:

                if is_fractal_broken(stock,'down'):
                    
                    # [清仓]
                    clear_position(stock,context)
                    
                    return

            hist_close = attribute_history(security=stock, count=5, unit='1d', fields='close', df=False)['close']

            # [加仓10% - AO，AC同时5日上行，且收盘价走高]
            if  is_up_going(check_list=g.AO_indicator[stock], nday=5) and \
                is_up_going(check_list=g.AC_indicator[stock], nday=5) and \
                is_up_going(check_list=hist_close, nday=2):
                
                # [调整]
                adjust_position(stock, context, ratio=0.1)

            # [减仓10% - AO，AC同时3日下行，且收盘价走低]
            if  is_down_going(check_list=g.AO_indicator[stock], nday=3) and \
                is_down_going(check_list=g.AC_indicator[stock], nday=3) and \
                is_down_going(check_list=hist_close, nday=2):
                
                # [调整]
                adjust_position(stock, context, ratio=-0.1)

    return
