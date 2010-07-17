import os

from setuptools import setup, find_packages

VERSION = '0.2.0'

setup(
    name='django-newcache',
    version=VERSION,
    description='Improved memcached cache backend for Django',
    long_description=file(
        os.path.join(os.path.dirname(__file__), 'README.txt')
    ).read(),
    author='Eric Florenzano',
    author_email='floguy@gmail.com',
    license='BSD',
    url='http://github.com/ericflo/django-newcache',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Programming Language :: Python',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Framework :: Django',
        'Environment :: Web Environment',
    ],
    zip_safe=False,
    packages=find_packages(),
    include_package_data=True,
    install_requires=['setuptools'],
)