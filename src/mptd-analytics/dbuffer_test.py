
from mptd.database.DatabaseSocket import DatabaseSocket


dbsock = DatabaseSocket(host='172.17.0.2', password='1234', user='root', port=3306, verbose=True)
dbsock.connect(db='mptd_test')
# cdstick_buffer = CandleDataBuffer(db_socket=dbsock,
#                                   db='mptd_test'
#                                   )
# cdstick_buffer.start()


