Real-time captcha-to-text decodings for asyncio
===============================================
.. image:: https://travis-ci.org/nibrag/aio_anticaptcha.svg?branch=master
   :target: https://travis-ci.org/nibrag/aio_anticaptcha
   :align: right

.. image:: https://coveralls.io/repos/github/nibrag/aio_anticaptcha/badge.svg?branch=master
   :target: https://coveralls.io/github/nibrag/aio_anticaptcha?branch=master
   :align: right

API documentation
-----------------
- https://anti-captcha.com/apidoc
- http://antigate.com/?action=api#algo

Installation
------------
You can install it using Pip:

.. code-block::

    pip install aio_anticaptcha

If you want the latest development version, you can install it from source:

.. code-block::

    git clone git@github.com:nibrag/aio_anticaptcha.git
    cd aio_anticaptcha
    python setup.py install

**Requirements:**

.. code-block::

    python 3.4+
    aiohttp

Usage
-----
With context manager

.. code-block:: python

    import asyncio
    from aio_anticaptcha import AntiCaptcha, ServiceError

    async def run(loop):
        try:
            with AntiCaptcha('API-KEY', loop=loop) as ac:
                # io.IOBase
                resolved, captcha_id = await ac.resolve(open('captcha.jpg'))

                # or bytes, bytearray
                bytes_buff = open('captcha.jpg', 'rb').read()
                resolved, captcha_id = await ac.resolved(bytes_buff)
        except ServiceError as e:
            print(e)

    if __name__ == '__main__':
        loop = asyncio.get_event_loop()
        loop.run_until_complete(run(loop))
        loop.close()

Without context manager

.. code-block:: python

    import asyncio
    from aio_anticaptcha import AntiCaptcha, ServiceError

    async def run(loop):
        ac = AntiCaptcha('API-KEY', loop=loop)
        try:
            # io.IOBase
            resolved, captcha_id = await ac.resolve(open('captcha.jpg'))

            # or bytes, bytearray
            bytes_buff = open('captcha.jpg', 'rb').read()
            resolved, captcha_id = await ac.resolved(bytes_buff)
        except ServiceError as e:
            print(e)
        finally:
            # do'nt forget call close method
            ac.close()

    if __name__ == '__main__':
        loop = asyncio.get_event_loop()
        loop.run_until_complete(run(loop))
        loop.close()

If you wish to complain about a mismatch results, use ``abuse`` method:

.. code-block:: python

    import asyncio
    from aio_anticaptcha import AntiCaptcha

    async def run(loop):
        with AntiCaptcha('API-KEY', loop=loop) as ac:
            resolved, captcha_id = await ac.resolve(open('captcha.jpg'))
            await ac.abuse(captcha_id)

    if __name__ == '__main__':
        loop = asyncio.get_event_loop()
        loop.run_until_complete(run(loop))
        loop.close()

After all manipulations, you can get your account balance:

.. code-block:: python

    import asyncio
    from aio_anticaptcha import AntiCaptcha

    async def run(loop):
        with AntiCaptcha('API-KEY', loop=loop) as ac:
            balance = await ac.get_balance()

    if __name__ == '__main__':
        loop = asyncio.get_event_loop()
        loop.run_until_complete(run(loop))
        loop.close()

Additional options for sending Captcha:
---------------------------------------

Read documentation about all available options:
https://anti-captcha.com/apidoc

.. code-block:: python

    import asyncio
    from aio_anticaptcha import AntiCaptcha

    async def run(loop):
        with AntiCaptcha('API-KEY', loop=loop) as ac:
            resolved, captcha_id = await ac.resolve(open('captcha.jpg'), max_len=5, is_russian=True)

    if __name__ == '__main__':
        loop = asyncio.get_event_loop()
        loop.run_until_complete(run(loop))
        loop.close()

Customizing anticaptcha service
-------------------------------

.. code-block:: python

    import asyncio
    from aio_anticaptcha import AntiCaptcha

    async def run(loop):
        with AntiCaptcha('API-KEY', loop=loop, domain='antigate.com', port=80) as ac:
            balance = await ac.get_balance()

    if __name__ == '__main__':
        loop = asyncio.get_event_loop()
        loop.run_until_complete(run(loop))
        loop.close()

AntiGate.com supported
----------------------

.. code-block:: python

    import asyncio
    from aio_anticaptcha import AntiGate

    async def run(loop):
        with AntiGate('API-KEY', loop=loop) as ag:
            balance = await ag.get_balance()

    if __name__ == '__main__':
        loop = asyncio.get_event_loop()
        loop.run_until_complete(run(loop))
        loop.close()
