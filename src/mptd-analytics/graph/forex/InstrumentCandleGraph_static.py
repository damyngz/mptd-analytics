import logging, copy, re, time, threading
import pandas as pd
from datetime import timedelta, datetime
from v20.errors import V20ConnectionError, V20Timeout
from v20.instrument import Candlestick
from backend.finance.indicators import moving_average, candle, bollinger_band
from backend.buffer import DataBuffer
from mptd.database.DatabaseSocket import DatabaseSocket
from mptd.lang.OANDA.view.time import RFC3339, get_timedelta
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
BOLLINGER_STDDEV = 2
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
                                    count=500,
                                    force_complete=True)

starting_data = dict(
    time=[], average=[], low=[], high=[], open=[], close=[],
    ma=[], ema=[], color=[], macd=[], macd9=[], macdh=[],
    boll_upper=[], boll_lower=[], boll_centre=[]
)

# starting_data = copy.deepcopy(source_dict)

for candle_ in candles:
    c_dict = to_dict(candle_)
    starting_data['time'] += [RFC3339.to_obj(c_dict['date_time'])]
    # starting_data['tick'] += [get_tick(candle_, GRANULARITY)]
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

    # close = starting_data['close'] + [c_dict['close']]
    close = starting_data['close']
    average = starting_data['average']
    ma = moving_average.MA(close, 12)
    ema = moving_average.EMA(close, 10)

    macd = moving_average.EMA(close, 12) - moving_average.EMA(close, 26)
    macd_series = starting_data['macd'] + [macd]
    macd9 = moving_average.EMA(macd_series, 9)
    macdh = macd - macd9
    [boll_lower, boll_centre, boll_upper] = bollinger_band.bollinger_band(average, 20, BOLLINGER_STDDEV)

    starting_data['ma'] += [ma]
    starting_data['ema'] += [ema]
    starting_data['macd'] += [macd]
    starting_data['macd9'] += [macd9]
    starting_data['macdh'] += [macdh]
    starting_data['boll_centre'] += [boll_centre]
    starting_data['boll_upper'] += [boll_upper]
    starting_data['boll_lower'] += [boll_lower]

# print(starting_data)
logging.info(candles[-1].time)
source = ColumnDataSource(starting_data)


class CandleHolder:
    def __init__(self, poll_rate):
        candles = CandleHolder._req_candles(True)

        self.poll_rate = poll_rate
        self.candle = candles[-1]
        self.tick = int(get_tick(self.candle, GRANULARITY)['tick'])
        self.queue = []

    @staticmethod
    def _req_candles(complete, c=5):
        while True:
            try:
                return instrument_candle_request(api=api,
                                                 instrument="EUR_USD",
                                                 granularity=GRANULARITY,
                                                 count=c,
                                                 force_complete=complete)
            except V20ConnectionError:
                time.sleep(1)

    def poll(self):
        candles = CandleHolder._req_candles(False)

        last_tick = int(get_tick(candles[-1], GRANULARITY)['tick'])
        # logger.info("curr tick: {} poll tick: {}".format(self.tick, last_tick))
        if candles[-1] == self.candle:
            pass

        elif last_tick == self.tick:
            self.candle = candles[-1]
            self.queue.append([self.candle])
            # logger.info('1 item added to queue({} items enqueued)'.format(len(self.queue)))
            # logger.info('enqueued -> {}'.format([c.time for c in candles]))
            logger.debug('enqueued -> {}'.format(self.candle.time))

        elif last_tick > self.tick:
            if abs(last_tick - self.tick) > 1:
                logger.warning("latest poll ahead of current graph by more than 1 tick, might result in incoherence")
            self.candle = candles[-1]
            self.queue.append(candles[-2:])
            self.tick = int(get_tick(self.candle, GRANULARITY)['tick'])
            # logger.info('1 item added to queue({} items enqueued)'.format(len(self.queue)))
            logger.info('enqueued -> {}'.format([c.time for c in candles[-2:]]))

    def start(self):
        def _subproc():
            while True:
                self.poll()
                time.sleep(self.poll_rate)

        threading.Thread(target=_subproc).start()
        logger.info("live polling started...")

    def get_result(self):
        if len(self.queue) > 0:
            r = self.queue.pop(0)
            logger.debug("queue popped -> {} items remaining in queue".format(len(self.queue)))
            return r
        logger.debug('no item in queue')
        return []


# =====================================================================================================================
plot_1 = figure(plot_height=500,
                tools="pan, reset, wheel_zoom",
                x_axis_type="datetime",
                y_axis_location="right")

plot_1.x_range.bounds = (0, 1)
plot_1.x_range.follow = "end"
plot_1.x_range.follow_interval = timedelta(hours=8)
# plot_1.x_range.follow_interval = timedelta(days=72)
# plot_1.x_range.default_span = timedelta(minutes=15)
plot_1.x_range.range_padding = 0.02
plot_1.xaxis.formatter = DatetimeTickFormatter(hours=["%H:%M"],
                                               days=["%d %b"],
                                               months=["%d %b"],
                                               years=["%Y"]
                                               )
plot_1.y_range.max_interval = 0.0035
plot_1.y_range.min_interval = 0.002
plot_1.y_range.default_span = 0.0005
# plot_1.y_range.follow = "end"
# plot_1.y_range.follow_interval = 0.0025

plot_1.varea(x='time', y1='boll_upper', y2='boll_lower', alpha=0.2, fill_color='lemonchiffon', source=source)
plot_1.line(x='time', y='boll_lower', line_dash='dotted', color='black', source=source)
plot_1.line(x='time', y='boll_upper', line_dash='dotted', color='black', source=source)
plot_1.line(x='time', y='boll_centre', alpha=0.5, line_dash='dotted', color='black', source=source)
plot_1.line(x='time', y='average', alpha=0.2, line_width=3, color='navy', source=source)
plot_1.line(x='time', y='ma', alpha=0.8, line_width=2, color='orange', source=source)
plot_1.line(x='time', y='ema', alpha=0.7, line_width=2, color='orangered', source=source)

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
def test_update():
    pass


def log_data():
    def subproc():
        while True:
            with open('data_log', 'w') as f:
                cols = [c for c in source.data]
                for col in cols:
                    f.write('{}, '.format(col))
                f.write('\n')
                for t in range(len(source.data[cols[0]])):
                    for col in cols:
                        f.write('{}, '.format(source.data[col][t]))
                    f.write('\n')

            logger.info('CDS data logged to file')
            time.sleep(150)

    threading.Thread(target=subproc).start()


def update():
    r = ch.get_result()
    if len(r) != 0:

        new_data = dict(
            time=[], average=[], low=[], high=[], open=[], close=[],
            ma=[], ema=[], color=[], macd=[], macd9=[], macdh=[],
            boll_upper=[], boll_lower=[], boll_centre=[]
        )
        for candle_ in r:
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

            close = source.data['close'][:-1] + [c_dict['close']]
            average = source.data['average'][:-1] + [c_dict['average']]
            ma = moving_average.MA(close, 12)
            ema = moving_average.EMA(close, 10)

            macd = moving_average.EMA(close, 12) - moving_average.EMA(close, 26)
            macd_series = source.data['macd'][:-1] + [macd]
            macd9 = moving_average.EMA(macd_series, 9)
            macdh = macd - macd9
            [boll_lower, boll_centre, boll_upper] = bollinger_band.bollinger_band(average, 20, BOLLINGER_STDDEV)

            new_data['ma'] += [ma]
            new_data['ema'] += [ema]
            new_data['macd'] += [macd]
            new_data['macd9'] += [macd9]
            new_data['macdh'] += [macdh]
            new_data['boll_upper'] += [boll_upper]
            new_data['boll_lower'] += [boll_lower]
            new_data['boll_centre'] += [boll_centre]

        if len(r) == 1:
            patch_dict = dict(
                time=[], average=[], low=[], high=[], open=[], close=[],
                ma=[], ema=[], color=[], macd=[], macd9=[], macdh=[],
                boll_upper=[], boll_lower=[], boll_centre=[]
            )
            for k in patch_dict:
                patch_dict[k] = [(COUNT-1, new_data[k][0])]

            # print(patch_dict)
            source.patch(patch_dict)

        if len(r) == 2:
            patch_dict, stream_dict = dict(
                time=[], average=[], low=[], high=[], open=[], close=[],
                ma=[], ema=[], color=[], macd=[], macd9=[], macdh=[],
                boll_upper=[], boll_lower=[], boll_centre=[]
            ),  dict(
                    time=[], average=[], low=[], high=[], open=[], close=[],
                    ma=[], ema=[], color=[], macd=[], macd9=[], macdh=[],
                    boll_upper=[], boll_lower=[], boll_centre=[]
                )
            for k in patch_dict:
                patch_dict[k] = [(COUNT-1, new_data[k][0])]

            # print(patch_dict)
            source.patch(patch_dict)

            for k in stream_dict:
                stream_dict[k] = [new_data[k][1]]

            source.stream(stream_dict, COUNT)

    else:
        pass

#
# def fill_candles(data):
#     new_data = []
#     td = get_timedelta(GRANULARITY)
#     for i in range(len(data)):
#         if i != len(data)-1 and (data[i+1] - data[i]) > td:
#             new_data += [data[i]] + [Candlestick(time=datetime())]
#
#         else:
#             new_data += [data[i]]


# =====================================================================================================================
ch = CandleHolder(0.25)
ch.start()
#
log_data()
#
# curdoc().add_periodic_callback(update, 150)
curdoc().add_root(column(gridplot([[plot_1], [plot_2]], toolbar_location="left", plot_width=1200)))
curdoc().title = "OHLC Live"
