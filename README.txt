django-newcache
===============

Newcache is an improved memcached cache backend for Django. It provides two
major advantages over Django's built-in cache backend:

 * It supports pylibmc.
 * It allows for a function to be run on each key before it's sent to memcached.

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
create an md5 hash of whatever key you want, and use the hash as your key
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
function to be run on each key, by supplying the CACHE_KEY_FUNC setting. It
must take in any instance of basestring and output a str.