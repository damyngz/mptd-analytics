import logging, re

from backend.finance.indicators import moving_average, candle
from mptd.database.DatabaseSocket import DatabaseSocket
from bokeh.layouts import row, column, gridplot
from bokeh.models import ColumnDataSource, Slider, Select
from bokeh.plotting import curdoc, figure
from bokeh.driving import count

# =====================================================================================================================
source = ColumnDataSource(dict(
        time=[], average=[], low=[], high=[], open=[], close=[],
        ma=[], macd=[], macd9=[], macdh=[], color=[]
    ))

plot_1 = figure(plot_height=500, tools="xpan,reset", x_axis_type=None, y_axis_location="right")
plot_1.x_range.follow = "end"
plot_1.x_range.follow_interval = 100
plot_1.x_range.range_padding = 0

plot_1.line(x='time', y='average', alpha=0.2, line_width=3, color='navy', source=source)
plot_1.line(x='time', y='ma', alpha=0.8, line_width=2, color='orange', source=source)
# candle low/high
plot_1.segment(x0='time', y0='low', x1='time', y1='high', line_width=2, color='black', source=source)
# candle body
plot_1.segment(x0='time', y0='open', x1='time', y1='close', line_width=8, color='color', source=source)

plot_2 = figure(plot_height=250, x_range=plot_1.x_range, tools="xpan,reset", y_axis_location="right")
plot_2.line(x='time', y='macd', color='red', source=source)
plot_2.line(x='time', y='macd9', color='blue', source=source)
plot_2.segment(x0='time', y0=0, x1='time', y1='macdh', line_width=6, color='black', alpha=0.5, source=source)

GLOBAL_MIN_TICK = 0
DBSOCK = DatabaseSocket(host='172.17.0.2', password='1234', user='root', port=3306)
DBSOCK.connect(db='mptd_test')
logger = logging.getLogger(__name__)


# =====================================================================================================================
def set_global_tick():
    global GLOBAL_MIN_TICK
    GLOBAL_MIN_TICK = \
    DBSOCK.pass_query("select tick from oanda_instrument_candles where granularity=\'S5\' order by tick asc limit 1")[1]
    logger.info('GLOBAL_MIN_TICK set to {}'.format(GLOBAL_MIN_TICK))


def advance_poll(t, max_size=100):
    t_ = GLOBAL_MIN_TICK + t
    select_constraint = ['tick', 'open', 'high', 'low', 'close']
    resp = DBSOCK.pass_query("select {1} from oanda_instrument_candles where\
(tick>={0} and tick<({0}+500)) order by tick limit {2}".format(t_,
                                                               re.sub('\[]', '', str(select_constraint)),
                                                               max_size))

    col_names = resp[0]
    resp_body = resp[1:]
    outp = {}
    for col in select_constraint:
        ind = col_names.index(col)
        outp[col] = [x[ind] for x in resp_body]

    outp['average'] = [0 for i in range(len(resp_body))]
    for i in range(len(resp_body)):
        outp['average'][i] = candle.ohlc_average(candle={'open': resp_body['open'][i],
                                                         'high': resp_body['high'][i],
                                                         'low': resp_body['low'][i],
                                                         'close': resp_body['close'][i]})
    return outp


@count()
def update(t):
    data = advance_poll(t)
    open, high, low, close, average = data['open'], data['high'], data['low'], data['close'], data['average']
    color = "green" if open < close else "red"

    new_data = dict(
        time=[t],
        open=[open],
        high=[high],
        low=[low],
        close=[close],
        average=[average],
        color=[color],
    )

    close = source.data['close'] + [close]
    ma12 = moving_average.MA(close, 12)[0]
    ma26 = moving_average.MA(close, 26)[0]
    ema12 = moving_average.EMA(close, 12)[0]
    ema26 = moving_average.EMA(close, 26)[0]

    new_data['ma'] = ma12
    # if   mavg.value == MA12:  new_data['ma'] = [ma12]
    # elif mavg.value == MA26:  new_data['ma'] = [ma26]
    # elif mavg.value == EMA12: new_data['ma'] = [ema12]
    # elif mavg.value == EMA26: new_data['ma'] = [ema26]

    macd = ema12 - ema26
    new_data['macd'] = [macd]

    macd_series = source.data['macd'] + [macd]
    macd9 = moving_average.EMA(macd_series[-26:], 9)[0]
    new_data['macd9'] = [macd9]
    new_data['macdh'] = [macd - macd9]

    source.stream(new_data, 300)


# =====================================================================================================================


#
curdoc().add_root(column(gridplot([[plot_1], [plot_2]], toolbar_location="left", plot_width=1000)))
curdoc().add_periodic_callback(update, 50)
curdoc().title = "OHLC"
