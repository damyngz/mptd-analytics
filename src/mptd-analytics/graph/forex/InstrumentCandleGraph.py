import logging, re, time, threading

from backend.finance.indicators import moving_average, candle
from backend.buffer import DataBuffer
from mptd.database.DatabaseSocket import DatabaseSocket
from bokeh.layouts import column, gridplot
from bokeh.models import ColumnDataSource
from bokeh.plotting import curdoc, figure
from bokeh.driving import count

# =====================================================================================================================
DEBUG = True


# =====================================================================================================================
class CandleDataBuffer(DataBuffer):
    def __init__(self,
                 db_socket,
                 buffer_size=5000,
                 tolerance=0.3,
                 tick_size=1,
                 db=None):
        super().__init__(db_socket, db=db, tolerance=tolerance, buffer_size=buffer_size)
        self.min_tick = 0
        # TODO change to D1 when populated
        self.granularity = 'S5'
        self.buffer = []
        self.cols = [['date_time', 'tick', 'open', 'high', 'low', 'close'], ['average']]

        self.set_tick()
        self._populate()
        self.data_gen = self.pop_data(tick_size)

    def set_tick(self):
        result = self.dbsock.pass_query("select tick from oanda_instrument_candles where granularity=\'S5\' "
                                        "order by tick asc limit 1",
                                        return_result=True)[1][0]

        self.min_tick = int(result)
        logger.info('tick set to {}'.format(self.min_tick))

    def set_granularity(self, g):
        self.granularity = g

    def _populate(self):
        q_sttment = "select {params} from oanda_instrument_candles where" \
                    "(granularity=\'{g}\' and tick>{min_tick})" \
                    "order by tick asc limit {count};".format(params=re.sub('[\'\[\]]', '', str(self.cols[0])),
                                                             g=self.granularity,
                                                             min_tick=self.min_tick,
                                                             # max_tick=self.min_tick + self.buffer_size + 50,
                                                             count=self.buffer_size)
        logger.debug(q_sttment)
        self.query(q_sttment)
        self.min_tick = self.buffer[-1][self.cols[0].index('tick')] + 1

    def query(self, q=None):
        if q is None:
            q = ""
        resp = self.dbsock.pass_query(q)
        col_names = resp[0]
        resp_body = resp[1:]

        outp = {}
        for col in col_names:
            ind = col_names.index(col)
            outp[col] = [x[ind] for x in resp_body]

            outp['average'] = [0 for i in range(len(resp_body))]
            for i in range(len(resp_body)):
                # print(resp_body[i])
                outp['average'][i] = candle.ohlc_average(candle={'o': resp_body[i][col_names.index('open')],
                                                                 'h': resp_body[i][col_names.index('high')],
                                                                 'l': resp_body[i][col_names.index('low')],
                                                                 'c': resp_body[i][col_names.index('close')]})

        self.buffer.append(outp)

    def check(self):
        if len(self.buffer) <= self.tolerance:
            logger.debug("Buffer at size {}(max={}). Re-populating buffer...".format(len(self.buffer),
                                                                                     self.buffer_size))
            self._populate()
        else:
            logger.debug("Buffer at size {}. OK.".format(len(self.buffer)))

    def call_generator(self):
        return next(self.data_gen)

    def pop_data(self, n=1):
        outp = [self.cols]
        while True:
            for i in range(n):
                outp += [self.buffer.pop(0)]
            yield outp
            # TODO open a thread for this process?
            # self.check()

    def stream_buffer(self, poll_rate):
        def subproc():
            while True:
                self.check()
                time.sleep(poll_rate)

        return threading.Thread(target=subproc)

    def start(self, poll_rate=60):
        self.stream_buffer(poll_rate=poll_rate).start()

# =====================================================================================================================
# source = ColumnDataSource(dict(
#         time=[], average=[], low=[], high=[], open=[], close=[],
#         ma=[], macd=[], macd9=[], macdh=[], color=[]
#     ))


logger = logging.getLogger(__name__)
source = ColumnDataSource(dict(
    time=[], average=[], low=[], high=[], open=[], close=[],
    ma=[], color=[]
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

# plot_2 = figure(plot_height=250, x_range=plot_1.x_range, tools="xpan,reset", y_axis_location="right")
# plot_2.line(x='time', y='macd', color='red', source=source)
# plot_2.line(x='time', y='macd9', color='blue', source=source)
# plot_2.segment(x0='time', y0=0, x1='time', y1='macdh', line_width=6, color='black', alpha=0.5, source=source)

# GLOBAL_MIN_TICK = 0
cdstick_buffer = CandleDataBuffer(db_socket=DatabaseSocket(host='172.17.0.2',
                                                           password='1234',
                                                           user='root',
                                                           port=3306, verbose=True),
                                  db='mptd_test'
                                  )
cdstick_buffer.start()


# =====================================================================================================================
# def set_global_tick():
#     global GLOBAL_MIN_TICK
#     result = DBSOCK.pass_query("select tick from oanda_instrument_candles where granularity=\'S5\' order by tick asc "
#                            "limit 1",
#                            return_result=True)[1][0]
#     GLOBAL_MIN_TICK = int(result)
#     logger.info('GLOBAL_MIN_TICK set to {}'.format(GLOBAL_MIN_TICK))


# def advance_poll(t, max_size=100):
#     t_ = GLOBAL_MIN_TICK + t
#     select_constraint = ['tick', 'open', 'high', 'low', 'close']
#     logger.info("select {q} from oanda_instrument_candles where\
#     (tick>={tick_min} and tick<{tick_max}) order by tick limit {limit};".format(tick_min=t_,
#                                                                        tick_max=t_+1000,
#                                                                        q=re.sub('[\'\[\]]', '', str(select_constraint)),
#                                                                        limit=max_size))
#
#     resp = DBSOCK.pass_query("select {q} from oanda_instrument_candles where\
#     (tick>={tick_min} and tick<{tick_max}) order by tick limit {limit};".format(tick_min=GLOBAL_MIN_TICK,
#                                                                        tick_max=t_,
#                                                                        q=re.sub('[\'\[\]]', '', str(select_constraint)),
#                                                                        limit=max_size),
#                          return_result=True)
#     if resp is None:
#         return 'FAILED'
#
#     col_names = resp[0]
#     resp_body = resp[1:]
#     outp = {}
#     for col in select_constraint:
#         ind = col_names.index(col)
#         outp[col] = [x[ind] for x in resp_body]
#
#     outp['average'] = [0 for i in range(len(resp_body))]
#     for i in range(len(resp_body)):
#         # print(resp_body[i])
#         outp['average'][i] = candle.ohlc_average(candle={'o': resp_body[i][select_constraint.index('open')],
#                                                          'h': resp_body[i][select_constraint.index('high')],
#                                                          'l': resp_body[i][select_constraint.index('low')],
#                                                          'c': resp_body[i][select_constraint.index('close')]})
#     return outp


@count()
def update(t):
    data = cdstick_buffer.call_generator()
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

    logging.info(source.data['close'])
    close = source.data['close'] + [close]
    ma12 = moving_average.MA(close, 12)[0]
    # ma26 = moving_average.MA(close, 26)[0]
    # ema12 = moving_average.EMA(close, 12)[0]
    # ema26 = moving_average.EMA(close, 26)[0]

    new_data['ma'] = ma12
    # if   mavg.value == MA12:  new_data['ma'] = [ma12]
    # elif mavg.value == MA26:  new_data['ma'] = [ma26]
    # elif mavg.value == EMA12: new_data['ma'] = [ema12]
    # elif mavg.value == EMA26: new_data['ma'] = [ema26]

    # macd = ema12 - ema26
    # new_data['macd'] = [macd]
    #
    # macd_series = source.data['macd'] + [macd]
    # macd9 = moving_average.EMA(macd_series[-26:], 9)[0]
    # new_data['macd9'] = [macd9]
    # new_data['macdh'] = [macd - macd9]

    source.stream(new_data, 300)


# =====================================================================================================================

#
curdoc().add_root(column(gridplot([[plot_1]], toolbar_location="left", plot_width=1000)))
# curdoc().add_root(column(gridplot([[plot_1], [plot_2]], toolbar_location="left", plot_width=1000)))
curdoc().add_periodic_callback(update, 200)
curdoc().title = "OHLC"
