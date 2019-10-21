def _candle_avg(candle, iterable):
    a = 0
    for i in iterable:
        a += candle[i]
    return a/len(iterable)


def ohlc_average(candle):
    return _candle_avg(candle, ['o', 'h', 'l', 'c'])


def hlc_average(candle):
    return _candle_avg(candle, ['h', 'l', 'c'])


def hl_average(candle):
    return _candle_avg(candle, ['h', 'l'])
