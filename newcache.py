"Modified memcached cache backend"

import hashlib
import time

from threading import local

from django.core.cache.backends.base import BaseCache, InvalidCacheBackendError
from django.utils import importlib
from django.utils.encoding import smart_str
from django.conf import settings

try:
    import pylibmc as memcache
    NotFoundError = memcache.NotFound
    using_pylibmc = True
except ImportError:
    using_pylibmc = False
    try:
        import memcache
        NotFoundError = ValueError
    except ImportError:
        raise InvalidCacheBackendError('Memcached cache backend requires ' + 
            'either the "pylibmc" or "memcache" library')

# Flavor is used amongst multiple apps to differentiate the "flavor" of the
# environment. Examples of flavors are 'prod', 'staging', 'dev', and 'test'.
FLAVOR = getattr(settings, 'FLAVOR', '')

CACHE_VERSION = str(getattr(settings, 'CACHE_VERSION', 1))
CACHE_BEHAVIORS = getattr(settings, 'CACHE_BEHAVIORS', {'hash': 'crc'})
CACHE_KEY_MODULE = getattr(settings, 'CACHE_KEY_FUNC', 'newcache')

def key_func(key):
    """
    Returns a hashed, versioned, flavored version of the string that was input.
    """
    hashed = hashlib.md5(smart_str(key)).hexdigest()
    return ''.join((settings.FLAVOR, '-', CACHE_VERSION, '-', hashed))

key_func = importlib.import_module(CACHE_KEY_MODULE).key_func

class CacheClass(BaseCache):

    def __init__(self, server, params):
        super(CacheClass, self).__init__(params)
        self._servers = server.split(';')
        self._use_binary = bool(params.get('binary'))
        self._local = local()
    
    @property
    def _cache(self):
        """
        Implements transparent thread-safe access to a memcached client.
        """
        client = getattr(self._local, 'client', None)
        if client:
            return client
        
        # Use binary mode if it's both supported and requested
        if using_pylibmc and self._use_binary:
            client = memcache.Client(self._servers, binary=True)
        else:
            client = memcache.Client(self._servers)
        
        # If we're using pylibmc, set the behaviors according to settings
        if using_pylibmc:
            client.behaviors = CACHE_BEHAVIORS
        
        self._local.client = client
        return client

    def _get_memcache_timeout(self, timeout):
        """
        Memcached deals with long (> 30 days) timeouts in a special
        way. Call this function to obtain a safe value for your timeout.
        """
        timeout = timeout or self.default_timeout
        if timeout > 2592000: # 60*60*24*30, 30 days
            # See http://code.google.com/p/memcached/wiki/FAQ
            # "You can set expire times up to 30 days in the future. After that
            # memcached interprets it as a date, and will expire the item after
            # said date. This is a simple (but obscure) mechanic."
            #
            # This means that we have to switch to absolute timestamps.
            timeout += int(time.time())
        return timeout

    def add(self, key, value, timeout=None):
        return self._cache.add(key_func(key), value,
            self._get_memcache_timeout(timeout))

    def get(self, key, default=None):
        val = self._cache.get(key_func(key))
        if val is None:
            return default
        return val

    def set(self, key, value, timeout=None):
        self._cache.set(key_func(key), value,
            self._get_memcache_timeout(timeout))

    def delete(self, key):
        self._cache.delete(key_func(key))

    def get_many(self, keys):
        rvals = map(key_func, keys)
        resp = self._cache.get_multi(rvals)
        reverse = dict(zip(rvals, keys))
        return dict(((reverse[k], v) for k, v in resp.iteritems()))

    def close(self, **kwargs):
        self._cache.disconnect_all()

    def incr(self, key, delta=1):
        try:
            return self._cache.incr(key_func(key), delta)
        except NotFoundError:
            raise ValueError("Key '%s' not found" % (key,))

    def decr(self, key, delta=1):
        try:
            return self._cache.decr(key_func(key), delta)
        except NotFoundError:
            raise ValueError("Key '%s' not found" % (key,))
    
    def set_many(self, data, timeout=0):
        safe_data = dict(((key_func(k), v) for k, v in data.iteritems()))
        self._cache.set_multi(safe_data, self._get_memcache_timeout(timeout))
    
    def delete_many(self, keys):
        self._cache.delete_multi(map(key_func, keys))
    
    def clear(self):
        self._cache.flush_all()