"""
Cache that optimizes for the following

1.  Recently seen items
2.  Frequently occuring items
3.  Costly items (expensive to compute)
4.  Small items (cheap to store)

It assumes cost to store and cost to compute are equally important.

Repeated queries add to the value of each item on each query.

Importance of older items decays exponentially by the number of queries.

"""
from collections import defaultdict
from heapdict import heapdict
import sys

class SBE(object):
    def __init__(self, data=None, available_bytes=1e9):
        if data is None:
            data = dict
        if isinstance(data, type):
            data = data()

        self.data = data
        self.heap = heapdict()
        self.oldscores = defaultdict(lambda: 0)
        self.misses = defaultdict(lambda: 0.0)
        self.tick = 0
        self.nbytes= sum(map(get_nbytes, data.values()))
        self.available_bytes = available_bytes

    def put(self, key, value, cost):
        self.tick += 1
        nbytes = get_nbytes(value)
        scr = score(cost, nbytes, self.tick)

        if key in self.data:
            self.heap[key] += scr
            return

        total_score = scr + self.oldscores[key]

        if (nbytes + self.nbytes > self.available_bytes and  # tight on space
            total_score <= self.heap.peekitem()[1]):         # low performer
            self.oldscores[key] += scr
            return

        self.nbytes += nbytes
        self.heap[key] = total_score
        self.data[key] = value

        if self.nbytes > self.available_bytes:
            self.shrink()

    def get(self, key, default=None):
        # TODO: Need to count misses here and enhance score accordingly
        #       when we do find it.
        value = self.data.get(key, default)

    def shrink(self):
        """
        Spill in-memory storage to disk until usage is less than available
        """
        if self.nbytes <= self.available_bytes:
            return

        while self.nbytes > self.available_bytes:
            key, scr = self.heap.popitem()
            self.retire(key)
            self.oldscores[key] = scr

    def retire(self, key):
        val = self.data.pop(key)
        self.nbytes -= get_nbytes(val)


def score(cost, nbytes, tick, base=1.001):
    return float(cost) / nbytes * (base ** tick)


def get_nbytes(o):
    """ Number of bytes of an object

    >>> get_nbytes(123)  # doctest: +SKIP
    24

    >>> get_nbytes('Hello, world!')  # doctest: +SKIP
    50

    >>> import numpy as np
    >>> get_nbytes(np.ones(1000, dtype='i4'))
    4000
    """
    if hasattr(o, 'nbytes'):
        return o.nbytes
    n = str(type(o))
    if 'pandas' in n and ('DataFrame' in n or 'Series' in n):
        return sum(b.values.nbytes * (10 if b.values.dtype == 'O' else 1)
                   for b in o._data.blocks)  # pragma: no cover
    else:
        return sys.getsizeof(o)
