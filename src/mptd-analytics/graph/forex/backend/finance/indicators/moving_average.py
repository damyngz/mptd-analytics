from numpy import cumprod, ones, mean, convolve
from pandas import DataFrame


def MA(d, n):
    """
    returns simple moving average
    :param d: dataset
    :param n: number of datapoints to consider
    :return:
    """
    if len(d) < n:
        return sum(d)/len(d)

    return sum(d[-n:])/n


def EMA(d, n):
    """
    returns exponential moving average
    :param d:
    :param n:
    :return:
    """
    k = 2/(n+1)

    # TODO debug numpy implementation segfault
    # multiplier = ones(d, dtype=float)
    # multiplier[1:] = 1-k
    # multiplier = k * cumprod(multiplier)

    # return convolve(d, multiplier)

    if len(d) <= n:
        return MA(d, n=n)

    else:

    mult = [(1-k) for i in range(len(d))]
    mult[0] = 1

    c =
    for i in range(len(mult)):

        pass


def MACD(ma1, ma2):
    """
    returns moving-average convergence/divergence
    :param ma1: m-day moving average (default=12)
    :param ma2: n-day moving average (default=26)
    :return:
    """

    return ma1-ma2


def MACD_signal_line(macd, n=9):
    if len(macd) < n:
        # return sum(macd)/len(macd)
        return mean(macd)

    else:
        mean(macd[-n:])


