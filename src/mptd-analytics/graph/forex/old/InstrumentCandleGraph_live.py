import logging, copy, re, time, threading, v20
import pandas as pd
from backend.finance.indicators import moving_average, candle
from backend.buffer import DataBuffer
from mptd.database.DatabaseSocket import DatabaseSocket
from mptd.lang.OANDA.view.time import RFC3339
from mptd.lang.OANDA.action.stream import to_dict, instrument_candle_request
from mptd.lang.OANDA.api import build_api_instance
from bokeh.layouts import column, gridplot
from bokeh.models import ColumnDataSource
from bokeh.plotting import curdoc, figure, show
from bokeh.driving import count

# =====================================================================================================================
DEBUG = True
CANDLE_OFFSET = 0.00000001
GRANULARITY = "M5"

# =====================================================================================================================
# =====================================================================================================================
logger = logging.getLogger(__name__)
data_dict = dict(
    time=[], average=[], low=[], high=[], open=[], close=[],
    ma=[], ema=[], color=[], macd=[], macd9=[], macdh=[]
)
source = ColumnDataSource(dict(
    time=[], average=[], low=[], high=[], open=[], close=[],
    ma=[], ema=[], color=[], macd=[], macd9=[], macdh=[]
))

plot_1 = figure(plot_height=500, tools="pan, reset", x_axis_type='datetime', y_axis_location="right")
plot_1.x_range.follow = "end"
plot_1.x_range.follow_interval = 100
plot_1.x_range.range_padding = 5

plot_1.line(x='time', y='average', alpha=0.2, line_width=3, color='navy', source=source)
plot_1.line(x='time', y='ma', alpha=0.8, line_width=2, color='orange', source=source)
plot_1.line(x='time', y='ema', alpha=0.7, line_width=2, color='mediumaquamarine', source=source)

# candle low/high
plot_1.segment(x0='time', y0='low', x1='time', y1='high', line_width=2, color='black', source=source)
# candle body
plot_1.segment(x0='time', y0='open', x1='time', y1='close', line_width=8, color='color', source=source)

plot_2 = figure(plot_height=250, x_range=plot_1.x_range, tools="pan, reset", y_axis_location="right")
plot_2.line(x='time', y='macd', color='red', source=source)
plot_2.line(x='time', y='macd9', color='blue', source=source)
plot_2.segment(x0='time', y0=0, x1='time', y1='macdh', line_width=6, color='black', alpha=0.5, source=source)


def init_data():
    candles = instrument_candle_request(api=api,
                                        instrument="EUR_USD",
                                        granularity=GRANULARITY,
                                        count=500,
                                        force_complete=False,
                                        )

    new_data = copy.deepcopy(data_dict)
    for candle_ in candles:
        c_dict = to_dict(candle_)

        new_data['time'] += [RFC3339.to_obj(c_dict['date_time'])]
        new_data['open'] += [c_dict['open']]
        new_data['high'] += [c_dict['high']]
        new_data['low'] += [c_dict['low']]
        new_data['close'] += [c_dict['close']]
        new_data['average'] += [candle.ohlc_average({'o': c_dict['close'],
                                                     'h': c_dict['high'],
                                                     'l': c_dict['low'],
                                                     'c': c_dict['close']})]

        if c_dict['close'] > c_dict['open']:
            color = 'green'

        elif c_dict['close'] == c_dict['open']:
            color = 'black'

        else:
            color = 'red'

        new_data['color'] += [color]

        close = source.data['close'] + [c_dict['close']]
        ma = moving_average.MA(close, 12)
        ema = moving_average.EMA(close, 10)

        macd = moving_average.EMA(close, 12) - moving_average.EMA(close, 26)
        macd_series = source.data['macd'] + [macd]
        macd9 = moving_average.EMA(macd_series, 9)
        macdh = [macd - macd9]

        new_data['ma'] += [ma]
        new_data['ema'] += [ema]
        new_data['macd'] += [macd]
        new_data['macd9'] += [macd9]
        new_data['macdh'] += [macdh]

    source.data = new_data


def patch_candles(c, stream=False):
    new_data = copy.deepcopy(data_dict)

    print(len(c))
    for candle_ in c:
        c_dict = to_dict(candle_)
        new_data['time'] += [RFC3339.to_obj(c_dict['date_time'])]
        new_data['open'] += [c_dict['open']]
        new_data['high'] += [c_dict['high']]
        new_data['low'] += [c_dict['low']]
        new_data['close'] += [c_dict['close']]
        new_data['average'] += [candle.ohlc_average({'o': c_dict['close'],
                                                     'h': c_dict['high'],
                                                     'l': c_dict['low'],
                                                     'c': c_dict['close']})]

        if c_dict['close'] > c_dict['open']:
            color = 'green'

        elif c_dict['close'] == c_dict['open']:
            color = 'black'

        else:
            color = 'red'

        new_data['color'] += [color]

        close = source.data['close'] + [c_dict['close']]
        ma = moving_average.MA(close, 12)
        ema = moving_average.EMA(close, 10)

        macd = moving_average.EMA(close, 12) - moving_average.EMA(close, 26)
        macd_series = source.data['macd'] + [macd]
        macd9 = moving_average.EMA(macd_series, 9)
        macdh = [macd - macd9]

        new_data['ma'] += [ma]
        new_data['ema'] += [ema]
        new_data['macd'] += [macd]
        new_data['macd9'] += [macd9]
        new_data['macdh'] += [macdh]


    source.data = new_data
    # if stream:
    #     source.stream(new_data)
    #
    # if not stream:
    #     s = slice(500)
    #     source.patch({
    #         'time': [(s, new_data['time'])],
    #         'open': [(s, new_data['open'])],
    #         'high': [(s, new_data['high'])],
    #         'low': [(s, new_data['low'])],
    #         'close': [(s, new_data['close'])],
    #         'average': [(s, new_data['average'])],
    #         'ma': [(s, new_data['ma'])],
    #         'ema': [(s, new_data['ema'])],
    #         'macd': [(s, new_data['macd'])],
    #         'macd9': [(s, new_data['macd9'])],
    #         'macdh': [(s, new_data['macdh'])]
    #     })


@count()
def update_candle(t):
    # candles = instrument_candle_request(api=api,
    #                                     instrument="EUR_USD",
    #                                     granularity=GRANULARITY,
    #                                     count=500,
    #                                     force_complete=False)

    # if t == 0:
    #     patch_candles([candles[t]], True)
    # else:
    #     patch_candles([candles[t]])
    pass


# =====================================================================================================================
api = build_api_instance("~/cfg/.v20.conf")
candles = instrument_candle_request(api=api,
                                    instrument="EUR_USD",
                                    granularity=GRANULARITY,
                                    count=500,
                                    force_complete=False)

patch_candles(candles)
# insert_candles(c=instrument_candle_request(api=api,
#                                            instrument="EUR_USD",
#                                            granularity=GRANULARITY,
#                                            count=500,
#                                            force_complete=False,
#                                            ),
#                data_source=source,
#                patch=False)
# print(source.data)


def update():
    # print(source.data)
    update_candle()


# =====================================================================================================================
curdoc().add_periodic_callback(update, 5000)
curdoc().add_root(column(gridplot([[plot_1], [plot_2]], toolbar_location="left", plot_width=1000)))
curdoc().title = "OHLC Live"
# show(plot_1)

###
import logging, copy, re, time, threading, v20
import pandas as pd
from datetime import timedelta
from backend.finance.indicators import moving_average, candle
from backend.buffer import DataBuffer
from mptd.database.DatabaseSocket import DatabaseSocket
from mptd.lang.OANDA.view.time import RFC3339
from mptd.lang.OANDA.action.stream import to_dict, instrument_candle_request, get_tick
from mptd.lang.OANDA.api import build_api_instance
from bokeh.layouts import column, gridplot
from bokeh.models import ColumnDataSource, DatetimeTickFormatter, Range1d
from bokeh.plotting import curdoc, figure, show
from bokeh.driving import count


# =====================================================================================================================
DEBUG = True
GRANULARITY = "M5"
COUNT = 100
api = build_api_instance("~/cfg/.v20.conf")


# =====================================================================================================================
logger = logging.getLogger(__name__)
# source = ColumnDataSource(dict(
#     time=[], average=[], low=[], high=[], open=[], close=[],
#     ma=[], ema=[], color=[], macd=[], macd9=[], macdh=[], dt=[]
# ))

candles = instrument_candle_request(api=api,
                                    instrument="EUR_USD",
                                    granularity=GRANULARITY,
                                    count=COUNT,
                                    force_complete=True)

source_dict = dict(
    time=[], average=[], low=[], high=[], open=[], close=[],
    ma=[], ema=[], color=[], macd=[], macd9=[], macdh=[], tick=[]
)
starting_data = copy.deepcopy(source_dict)


for candle_ in candles:
    c_dict = to_dict(candle_)
    starting_data['time'] += [RFC3339.to_obj(c_dict['date_time'])]
    starting_data['tick'] += [get_tick(candle_, GRANULARITY)]
    starting_data['open'] += [c_dict['open']]
    starting_data['high'] += [c_dict['high']]
    starting_data['low'] += [c_dict['low']]
    starting_data['close'] += [c_dict['close']]
    starting_data['average'] += [candle.ohlc_average({'o': c_dict['close'],
                                                 'h': c_dict['high'],
                                                 'l': c_dict['low'],
                                                 'c': c_dict['close']})]

    if c_dict['close'] > c_dict['open']:
        color = 'green'

    elif c_dict['close'] == c_dict['open']:
        color = 'black'

    else:
        color = 'red'

    starting_data['color'] += [color]

    close = starting_data['close'] + [c_dict['close']]
    ma = moving_average.MA(close, 12)
    ema = moving_average.EMA(close, 10)

    macd = moving_average.EMA(close, 12) - moving_average.EMA(close, 26)
    macd_series = starting_data['macd'] + [macd]
    macd9 = moving_average.EMA(macd_series, 9)
    macdh = [macd - macd9]

    starting_data['ma'] += [ma]
    starting_data['ema'] += [ema]
    starting_data['macd'] += [macd]
    starting_data['macd9'] += [macd9]
    starting_data['macdh'] += [macdh]

source = ColumnDataSource(data=starting_data)


# class CandleHolder:
#     def __init__(self, poll_rate):
#         candles = CandleHolder._req_candles(False)
#
#         self.poll_rate = poll_rate
#         self.candle = candles[-1]
#         self.tick = get_tick(self.candle, GRANULARITY)
#         self.queue = []
#
#     @staticmethod
#     def _req_candles(complete, c=5):
#         return instrument_candle_request(api=api,
#                                             instrument="EUR_USD",
#                                             granularity=GRANULARITY,
#                                             count=c,
#                                             force_complete=complete)
#
#     def poll(self):
#         candles = CandleHolder._req_candles(False)
#
#         last_tick = get_tick(candles[-1], GRANULARITY)
#         if candles[-1] == self.candle:
#             pass
#
#         elif last_tick == self.tick:
#             self.candle = candles[-1]
#             self.queue.append([self.candle])
#
#         elif last_tick > self.tick:
#             if abs(last_tick - self.tick) > 1:
#                 logger.warning("latest poll ahead of current graph by more than 1 tick, might result in incoherence")
#             self.candle = candles[-1]
#             self.queue.append(candles[-2:])
#
#     def start(self):
#         def _subproc():
#             while True:
#                 self.poll()
#                 time.sleep(self.poll_rate)
#
#         threading.Thread(target=_subproc).start()
#         logger.info("live polling started...")
#
#     def get_result(self):
#         if len(self.queue) > 0:
#             return self.queue.pop(0)
#         return []
#

# =====================================================================================================================
plot_1 = figure(plot_height=500,
                tools="pan, reset",
                x_axis_type="datetime",
                y_axis_location="right")
plot_1.x_range.follow = "end"
plot_1.x_range.follow_interval = timedelta(hours=5)
plot_1.x_range.default_span = timedelta(minutes=15)
plot_1.x_range.range_padding = 0.02
plot_1.xaxis.formatter = DatetimeTickFormatter(hours=["%H:%M"],
                                               days=["%H:%M"],
                                               months=["%H:%M"],
                                               years=["%H:%M"]
)
plot_1.y_range.max_interval = 0.0035
plot_1.y_range.min_interval = 0.002
plot_1.y_range.default_span = 0.0005
# plot_1.y_range.follow = "end"
# plot_1.y_range.follow_interval = 0.0025

plot_1.line(x='time', y='average', alpha=0.2, line_width=3, color='navy', source=source)
plot_1.line(x='time', y='ma', alpha=0.8, line_width=2, color='orange', source=source)
plot_1.line(x='time', y='ema', alpha=0.7, line_width=2, color='mediumaquamarine', source=source)

# candle low/high
plot_1.segment(x0='time', y0='low', x1='time', y1='high', line_width=2, color='black', source=source)
# candle body
plot_1.segment(x0='time', y0='open', x1='time', y1='close', line_width=8, color='color', source=source)

plot_2 = figure(plot_height=250, x_range=plot_1.x_range, tools="pan, reset",  x_axis_type="datetime", y_axis_location="right")

plot_2.x_range.default_span = timedelta(minutes=15)

plot_2.line(x='time', y='macd', color='red', source=source)
plot_2.line(x='time', y='macd9', color='blue', source=source)
plot_2.segment(x0='time', y0=0, x1='time', y1='macdh', line_width=6, color='black', alpha=0.5, source=source)


# =====================================================================================================================
# def update():
#     r = ch.get_result()
#     if len(r) == 0:
#         return
#
#     new_data = copy.deepcopy(source_dict)
#     for candle_ in r:
#         c_dict = to_dict(candle_)
#         new_data['time'] += [RFC3339.to_obj(c_dict['date_time'])]
#         new_data['tick'] += [get_tick(candle_, GRANULARITY)]
#         new_data['open'] += [c_dict['open']]
#         new_data['high'] += [c_dict['high']]
#         new_data['low'] += [c_dict['low']]
#         new_data['close'] += [c_dict['close']]
#         new_data['average'] += [candle.ohlc_average({'o': c_dict['close'],
#                                                      'h': c_dict['high'],
#                                                      'l': c_dict['low'],
#                                                      'c': c_dict['close']})]
#
#         if c_dict['close'] > c_dict['open']:
#             color = 'green'
#
#         elif c_dict['close'] == c_dict['open']:
#             color = 'black'
#
#         else:
#             color = 'red'
#
#         new_data['color'] += [color]
#
#         close = new_data['close'] + [c_dict['close']]
#         ma = moving_average.MA(close, 12)
#         ema = moving_average.EMA(close, 10)
#
#         macd = moving_average.EMA(close, 12) - moving_average.EMA(close, 26)
#         macd_series = new_data['macd'] + [macd]
#         macd9 = moving_average.EMA(macd_series, 9)
#         macdh = [macd - macd9]
#
#         new_data['ma'] += [ma]
#         new_data['ema'] += [ema]
#         new_data['macd'] += [macd]
#         new_data['macd9'] += [macd9]
#         new_data['macdh'] += [macdh]
#
#     if len(r) == 1:
#         patch_dict = copy.deepcopy(source_dict)
#         for k in patch_dict:
#             patch_dict[k] = [(COUNT-1, [new_data[k][0]])]
#
#         print(patch_dict)
#         source.patch(patch_dict)
#
#     if len(r) == 2:
#         patch_dict, stream_dict = copy.deepcopy(source_dict), copy.deepcopy(source_dict)
#         for k in patch_dict:
#             patch_dict[k] = [(COUNT-1, [new_data[k][0]])]
#
#         print(patch_dict)
#         source.patch(patch_dict)
#
#         for k in stream_dict:
#             stream_dict[k] = [new_data[k][1]]
#
#         source.stream(stream_dict, COUNT)
#

# =====================================================================================================================
# ch = CandleHolder(1)
# ch.start()
#
# curdoc().add_periodic_callback(update, 1000)
curdoc().add_root(column(gridplot([[plot_1], [plot_2]], toolbar_location="left", plot_width=1200)))
curdoc().title = "OHLC Live"

