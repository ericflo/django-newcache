import functools
import time

from django.conf import settings

settings.configure(DEBUG=False, TEMPLATE_DEBUG=False, FLAVOR='test',
    CACHE_HERD_TIMEOUT=1)

from newcache import CacheClass

def get_client(server='127.0.0.1:11211', **kwargs):
    return CacheClass(server, kwargs)

def cachetest(f):
    @functools.wraps(f)
    def inner(*args, **kwargs):
        c = get_client()
        c._cache.flush_all()
        resp = f(c, *args, **kwargs)
        c._cache.flush_all()
        return resp
    return inner
        
@cachetest
def test_basic(c):
    """
    Basic set, get, and delete.
    """
    assert c.get('test') is None
    c.set('test', True, 10)
    assert c.get('test') == True
    c.delete('test')
    assert c.get('test') is None

@cachetest
def test_add(c):
    """
    Ensures that the add command works properly.
    """
    assert c.get('test') is None
    c.add('test', 1, 10)
    assert c.get('test') == 1
    c.add('test', 2, 10)
    assert c.get('test') == 1

@cachetest
def test_incr_decr(c):
    """
    Increment and decrement functions.
    """
    assert c.get('test') is None
    c.set('test', 5, 10, herd=False)
    assert c.get('test') == 5
    c.incr('test', 1)
    assert c.get('test') == 6
    c.decr('test', 3)
    assert c.get('test') == 3

@cachetest
def test_get_set_many(c):
    """
    Tests the batch set, get, and delete functions.
    """
    assert c.get_many(['a', 'b', 'c']) == {}
    c.set_many({'a': 1, 'b': 2, 'c': 3}, 10)
    assert c.get_many(['a', 'b', 'c']) == {'a': 1, 'b': 2, 'c': 3}
    c.delete_many(['a', 'b'])
    assert c.get_many(['a', 'b', 'c']) == {'c': 3}

@cachetest
def test_herd(c):
    """
    Ensures that the herd effects works properly.
    """
    assert c.get('test') is None
    c.set('test', 1, 1)
    time.sleep(1.1)
    assert c.get('test') == 1
    time.sleep(1)
    assert c.get('test') is None

@cachetest
def test_none_timeout(c):
    """
    Tests that setting the cache with None as the timeout works properly.
    """
    c.set('test1', 1, timeout=None)
    assert c.get('test1') == 1
    c.add('test2', 2, timeout=None)
    assert c.get('test2') == 2
    c.set('test3', 3, timeout=None, herd=False)
    assert c.get('test3') == 3
    c.add('test4', 4, timeout=None, herd=False)
    assert c.get('test4') == 4