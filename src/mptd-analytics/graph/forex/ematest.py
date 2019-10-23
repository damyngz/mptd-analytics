from backend.finance.indicators.moving_average import MA, EMA_d
from datetime import datetime
import time
data = []
with open('testdata.csv') as f:
    for line in f:
        line_ = line.split(',')

        # dt = line_[0].split()
        # date = dt[0].split('-')
        # time = dt[1].split(':')
        #

        [o, h, l, c] = [float(i) for i in line_[1:5]]
        data.append([o, h, l, c])

for r in range(20):
    c = [i[-1] for i in data[:r+1]]
    # print("{}\n{}\n{}\n{}\n{:5f} {:5f}".format(data[r][0],
    #                                            data[r][1],
    #                                            data[r][2],
    #                                            data[r][3],
    #                                            MA(c, 12),
    #                                            EMA(c, 10)))

    print("{:5f} {:5f}".format(MA(c, 12), EMA_d(c, 10)))

    time.sleep(1)
