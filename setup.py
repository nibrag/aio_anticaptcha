#!/usr/bin/env python
import codecs
import os
import re
import sys

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup


with codecs.open(os.path.join(os.path.abspath(os.path.dirname(
        __file__)), 'aio_anticaptcha', '__init__.py'), 'r', 'latin1') as fp:
    try:
        version = re.findall(r"^__version__ = '([^']+)'\r?$",
                             fp.read(), re.M)[0]
    except IndexError:
        raise RuntimeError('Unable to determine version.')


if sys.version_info < (3, 4, 0):
    raise RuntimeError("aio_anticaptcha requires Python 3.4+")


setup(
        name='aio_anticaptcha',
        author='Nail Ibragimov',
        author_email='ibragwork@gmail.com',
        version=version,
        keywords='antigate captcha anticaptcha',
        license='Apache 2',
        url='https://github.com/nibrag/aio_anticaptcha',
        install_requires=['aiohttp'],

        description='Real-time captcha-to-text decodings',
        long_description=open("README.rst").read(),
        packages=['aio_anticaptcha']
)
