# import statements
from .moving_average import MA, EMA
from numpy import mean, sqrt


def _std_dev(d, n):
    m = sum(d[-n:])/(len(d) if len(d) < n else n)
    sumvar = 0
    if n <= len(d):
        r = n

    else:
        r = len(d)

    for i in range(-1, -r-1, -1):
        sumvar += pow((d[i] - m), 2)

    return float(sqrt(sumvar/r))
    # return 0.0001


def bollinger_band(d, n, stddev, avg=EMA):
    """
    :param d:
    :param n:
    :param stddev:
    :param avg:
    :return: [boll_lower, boll_upper]
    """
    # average = EMA(d, 20)
    average = avg(d, n)
    s = _std_dev(d, n)
    s_ = stddev * s
    # print(average, average-s_, average+s_)
    return [average-s_, average, average+s_]
