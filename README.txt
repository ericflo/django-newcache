django-newcache
===============

Newcache is an improved memcached cache backend for Django. It provides four
major advantages over Django's built-in cache backend:

 * It supports pylibmc.
 * It allows for a function to be run on each key before it's sent to memcached.
 * It supports setting cache keys with infinite timeouts.
 * It mitigates the thundering herd problem.

It also has some pretty nice defaults. By default, the function that's run on
each key is one that hashes, versions, and flavors the key.  More on that 
later.


How to Install
--------------

The simplest way is to just set it as your cache backend in your settings.py, 
like so::

    CACHE_BACKEND = 'newcache://127.0.0.1:11211/?binary=true'

Note that we've passed an additional argument, binary, to the backend.  This
is because pylibmc supports using binary mode to talk to memcached. This is a
completely optional parameter, and can be omitted safely to use the old text 
mode. It is ignored when using python-memcached.


Default Behavior
----------------

Earlier we said that by default it hashes, versions, and flavors each key. What
does this mean?  Let's go through each item in detail.

Keys in memcached come with many restrictions, both on their length and on 
their contents.  Practically speaking, this means that you can't put spaces
in your keys, and they can't be very long.  One simple solution to this is to
create an sha1 hash of whatever key you want, and use the hash as your key
instead.  That is what we do in newcache.  It not only allows for long keys, 
but it also lets us put spaces or other characters in our key as well.

Sometimes it's necessary to clear the entire cache. We can do this using 
memcached's flushing mechanisms, but sometimes a cache is shared by many things
instead of just one web app.  It's a shame to have everything lose its
fresh cache just because one web app needed to clear its cache. For this, we
introduce a simple technique called versioning. A version number is added to
each cache key, and when this version is incremented, all the old cache keys
will become invalid because they have an incorrect version.

This is exposed as a new setting, CACHE_VERSION, and it defaults to 1.

Finally, we found that as we split our site out into development, staging, and
production, we didn't want them to share the same cache.  But we also didn't
want to spin up a new memcached instance for each one.  So we came up with the
idea of flavoring the cache.  The concept is simple--add a FLAVOR setting and
make it something like 'dev', 'prod', or 'test'.  With newcache, this flavor
string will be added to each key, ensuring that there are no collisions.

Concretely, this is what happens::

    # CACHE_VERSION = 2
    # FLAVOR = 'staging'
    cache.get('games')
    # ... would actually call ...
    cache.get('staging-2-9cfa7aefcc61936b70aaec6729329eda')


Changing the Default
--------------------

All of the above is simply the default, you may provide your own callable
function to be run on each key, by supplying the CACHE_KEY_MODULE setting. It
must provide a get_key function which takes any instance of basestring and 
output a str.


Thundering Herd Mitigation
--------------------------

The thundering herd problem manifests itself when a cache key expires, and many
things rush to get or generate the data stored for that key all at once.  This 
is doing a lot of unnecessary work and can cause service outages if the
database cannot handle the load.  To solve this problem, we really only want 
one thread or process to fetch this data.

Our method of solving this problem is to shove the old (expired) value back 
into the cache for a short time while the first process/thread goes and updates
the key.  This is done in a completely transparent way--no changes should need
to be made in the application code.

With this cache backend, we have provided an extra 'herd' keyword argument to 
the set, add, and set_many methods--which is set to True by default. What this 
does is transform your cache value into a tuple before saving it to the cache. 
Each value is structured like this:

    (A herd marker, your original value, the expiration timestamp)

Then when it actually sets the cache, it sets the real timeout to a little bit
longer than the expiration timestamp. Actually, this "little bit" is 
configurable using the CACHE_HERD_TIMEOUT setting, but it defaults to 60 
seconds.

Now every time we read a value from the cache, we automatically unpack it and 
check whether it's expired.  If it has expired, we put it back in the cache for 
CACHE_HERD_TIMEOUT seconds, but (and this is the key) we act as if it were a 
cache miss (so we return None, or whatever the default was for the call.)

*Note*: If you want to set a value to be used as a counter (with incr and
        decr) then you'll want to bypass the herd mechanism.