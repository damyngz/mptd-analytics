from backend.finance.indicators.moving_average import *
# from mptd.da
from bokeh.layouts import row, column, gridplot
from bokeh.models import ColumnDataSource, Slider, Select
from bokeh.plotting import curdoc, figure
from bokeh.driving import count


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
DBSOCK =

def set_global_tick():
    global GLOBAL_MIN_TICK
    GLOBAL_MIN_TICK


def advance_poll(t, max_size=100):



@count()
def update(t):
    open, high, low, close, average = advance_poll(t)
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
    ma12 = _moving_avg(close[-12:], 12)[0]
    ma26 = _moving_avg(close[-26:], 26)[0]
    ema12 = _ema(close[-12:], 12)[0]
    ema26 = _ema(close[-26:], 26)[0]

    new_data['ma'] = ma12
    # if   mavg.value == MA12:  new_data['ma'] = [ma12]
    # elif mavg.value == MA26:  new_data['ma'] = [ma26]
    # elif mavg.value == EMA12: new_data['ma'] = [ema12]
    # elif mavg.value == EMA26: new_data['ma'] = [ema26]

    macd = ema12 - ema26
    new_data['macd'] = [macd]

    macd_series = source.data['macd'] + [macd]
    macd9 = _ema(macd_series[-26:], 9)[0]
    new_data['macd9'] = [macd9]
    new_data['macdh'] = [macd - macd9]

    source.stream(new_data, 300)


curdoc().add_root(column(gridplot([[plot_1], [plot_2]], toolbar_location="left", plot_width=1000)))
curdoc().add_periodic_callback(update, 50)
curdoc().title = "OHLC"
