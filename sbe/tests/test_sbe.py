from heapdict import heapdict
from sbe import SBE, get_nbytes

def test_SBE():
    s = SBE(available_bytes=3 * get_nbytes(1))

    s.put('a', 1, 11)
    s.put('b', 2, 12)
    s.put('c', 3, 13)

    assert s.data == {'a': 1, 'b': 2, 'c': 3}

    s.put('d', 4, 14)

    assert s.data == {'d': 4, 'b': 2, 'c': 3}
    assert 'a' in s.oldscores

    old_bscore = s.heap['b']
    s.put('b', 2, 5)
    assert s.heap['b'] > old_bscore


def test_gets_bump_value():
    s = SBE(available_bytes=3 * get_nbytes(1))
    s.get('x')
    s.get('x')
    s.get('x')

    s.put('x', 1, 1)
    s.put('y', 1, 2)

    assert s.heap.peekitem()[0] == 'y'  # Y is less important than X
