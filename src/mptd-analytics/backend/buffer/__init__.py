import threading
from abc import ABC, abstractmethod

"""
# TODO 
query function must have a way of passing a number limit
set params:
count -> number of rows to query for 
ticks

OR data generator for query function??
"""


class DataBuffer(ABC):
    def __init__(self,
                 db_socket,
                 buffer_size=5000,
                 tolerance=0.3,
                 db=None,
                 ):
        """
        :param query_function: query function
        :param buffer_size:
        :param tolerance:
        """
        self.buffer_size = buffer_size
        self.tolerance = tolerance
        self.dbsock = db_socket

        self.dbsock.connect(db=db)

    @abstractmethod
    def _populate(self):
        pass

    @abstractmethod
    def query(self):
        pass

    @abstractmethod
    def pop_data(self):
        pass