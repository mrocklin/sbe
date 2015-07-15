Caching
=======

Automatic caching improves performance in exploratory workflows.  We
opportunistically store intermediate results in a fixed space to speed up
future computations that reuse those results.

Caching has been invaluable in the web community.  How can we extend this to
data-science workflows?

Use case: Dask
--------------

In dask one large result often requires many small results (e.g. computing the
mean of an array involves the sum and len of many sub-arrays.)  Slightly
different computations (e.g. computing the variance of the same array) may
reuse many of the intermediate computations.  When these two arrays are
computed simultaneously we identify the shared sub-expressions to great
benefit.  When these two arrays are computed sequentially (as happens in
exploratory data analysis) then we lose this optimization.

Caching is particularly valuable for datasets that grow slowly, as in time
series that evolve one dataset per day.


Use case: Blaze Server
----------------------

More generally systems that respond to queries like Blaze server may compute
analytic computations driven by some third party.  Much of the caching
necessary for dask's use case is valuable more generally.


What makes a good analytic caching system?
------------------------------------------

Or: Why not use memcached?

Analytic computations vary widely in the time to compute and in the storage
space required to store the result, and in the cost of serialization.  A sane
caching strategy for analytic computations must be aware of these
considerations.

Given a fixed amount of storage space or limited bandwidth to an on-disk store
we must be picky about what we choose to cache and what we release quickly.

In particular we want a caching policy that prefers to keep results with the
following properties:

1.  Costly items (expensive to recompute)
2.  Small items (cheap to store
3.  Frequently requested items
4.  Recently seen items


One solution
------------

Given the following for a computation

*  `cost`: cost to compute
*  `size`: size to store
*  `time`: of computation (either seconds or some incrementing value)

We evaluate the following score

    cost / size * (1 + eps)**time

This has units in seconds per megabyte and has a slow exponential decay in
importance over time (newer items are more important that older ones).  This
emphasizes objectives 1, 2, and 4 above.  By adding this value at each request
of the data we also satisfy objective 3.

The scale of `eps`, a small value, determines the time-scale at which we
degrade old results.


Storage
-------

We can store results in memory, on disk, and with or without compression.  Each
of these choices have trade-offs.  In other systems we have found that good
performance comes from hybridizing these choices, effectively creating a
hierarchy of caches that feed into each other.  For example one might have the
following:

1.  An in-memory cache of small size (2GB)
2.  An in-memory cache of fast-compressed data of small size (2GB)
3.  An on-disk cache of fast-compressed data of large size (30GB)

The highest ranking items (cheap to store, expensive to compute) live in the
uncompressed in-memory cache and have effectively infinite bandwidth to the
user.  As items get pushed from this level they are compressed and stored in a
second in-memory cache that uses fast (1000 MB/s) compression.  As items
retire from this cache they are either forgotten or placed into on-disk storage
(300 MB/s bandwidth).  At any transition between caches we choose to forget
rather than store if the bandwidth cost to recompute the result is not
significantly less than bandwidth of the lower cache.

In practice data needs/compressability/bandwidths vary between applications and
a fixed hierarchy is unlikely to extend to many use cases.  It may be worth
building a composable system to construct various hierarchies as may be
necessary for a particular application.  This was the case with `partd` an
on-disk data store for shuffle operations.  We found that this solution worked
quite well.

An excerpt from the `partd` Readme:

    Composition
    -----------

    In principle we want to compose all of these choices together

    1.  Write policy:  ``Dict``, ``File``, ``Buffer``, ``Client``
    2.  Encoding:  ``Pickle``, ``Numpy``, ``Pandas``, ...
    3.  Compression:  ``Blosc``, ``Snappy``, ...

    Partd objects compose by nesting.  Here we make a partd that writes pickle
    encoded BZ2 compressed bytes directly to disk::

        >>> p = Pickle(BZ2(File('foo')))

    We could construct more complex systems that include compression,
    serialization, buffering, and remote access.::

        >>> server = Server(Buffer(Dict(), File(), available_memory=2e0))

        >>> client = Pickle(Snappy(Client(server.address)))
        >>> client.append({'x': [1, 2, 3]})

TODO
----

Probably all of the above is wrong.  This is design without experimentation.

I played around with this idea on a quick plane ride. Here is a [tiny
repository](http://github.com/mrocklin/sbe) but this should be taken only as
play-time not as a base for a serious project; it has known flaws.

So the thing to do is probably to fool around with these systems, think of a
decent API that captures all that we need to capture, and then slowly build up
something for a practical use case.
