import logging, re
from backend.finance.indicators import candle
from mptd.database.DatabaseSocket import DatabaseSocket

GLOBAL_MIN_TICK = 0
DBSOCK = DatabaseSocket(host='172.17.0.2', password='1234', user='root', port=3306)
DBSOCK.connect(db='mptd_test')
DBSOCK.verbose = False
logger = logging.getLogger(__name__)


# =====================================================================================================================
def set_global_tick():
    global GLOBAL_MIN_TICK
    result = DBSOCK.pass_query("select tick from oanda_instrument_candles where granularity=\'S5\' order by tick asc "
                               "limit 1",
                               return_result=True)[1][0]
    GLOBAL_MIN_TICK = int(result)
    logger.info('GLOBAL_MIN_TICK set to {}'.format(GLOBAL_MIN_TICK))


def advance_poll(t, max_size=100):
    t_ = GLOBAL_MIN_TICK + t
    select_constraint = ['tick', 'open', 'high', 'low', 'close']
    logger.info("select {q} from oanda_instrument_candles where\
(tick>={tick_min} and tick<{tick_max}) order by tick limit {limit};".format(tick_min=t_,
                                                                           tick_max=t_+1000,
                                                                           q=re.sub('[\'\[\]]', '', str(select_constraint)),
                                                                           limit=max_size))

    resp = DBSOCK.pass_query("select {q} from oanda_instrument_candles where\
(tick>={tick_min} and tick<{tick_max}) order by tick limit {limit};".format(tick_min=GLOBAL_MIN_TICK,
                                                                           tick_max=t_,
                                                                           q=re.sub('[\'\[\]]', '', str(select_constraint)),
                                                                           limit=max_size),
                             return_result=True)
    if resp is None:
        return 'FAILED'

    col_names = resp[0]
    resp_body = resp[1:]
    outp = {}
    for col in select_constraint:
        ind = col_names.index(col)
        outp[col] = [x[ind] for x in resp_body]

    outp['average'] = [0 for i in range(len(resp_body))]
    for i in range(len(resp_body)):
        # print(resp_body[i])
        outp['average'][i] = candle.ohlc_average(candle={'o': resp_body[i][select_constraint.index('open')],
                                                         'h': resp_body[i][select_constraint.index('high')],
                                                         'l': resp_body[i][select_constraint.index('low')],
                                                         'c': resp_body[i][select_constraint.index('close')]})
    return outp


set_global_tick()
print(advance_poll(10000))
