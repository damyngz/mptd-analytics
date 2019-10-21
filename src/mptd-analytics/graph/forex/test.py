from mptd.database.DatabaseSocket import DatabaseSocket

d = DatabaseSocket(user='root',password='1234', host='172.17.0.2', port=3306)
d.connect('mptd_test')
