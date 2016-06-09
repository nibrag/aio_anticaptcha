import aiohttp
import asyncio
import io
from base64 import b64encode

__version__ = '0.1.0'
__all__ = ('AntiCaptcha', 'AntiGate', 'ServiceError',
           'UserKeyError', 'ZeroBalanceError')


class ServiceError(Exception):
    pass


class UserKeyError(ServiceError):
    pass


class ZeroBalanceError(ServiceError):
    pass


class AntiCaptcha:
    def __init__(self, api_key, *, domain='anti-captcha.com', port=80,
                 check_interval=10, send_interval=0.1, loop=None):
        if not isinstance(api_key, str) or len(api_key) != 32:
            raise ValueError('api_key must be string 32 bytes')
        if check_interval <= 0:
            raise ValueError('check_interval must be integer '
                             'and greater than zero')
        if send_interval <= 0:
            raise ValueError('send_interval must be integer '
                             'and greater than zero')

        self._api_key = api_key
        self._check_interval = check_interval
        self._send_interval = send_interval

        self._request_url = 'http://{}:{}/in.php'.format(domain, port)
        self._response_url = 'http://{}:{}/res.php'.format(domain, port)
        self._loop = loop or asyncio.get_event_loop()
        self._session = self._create_session()

    @asyncio.coroutine
    def resolve(self, captcha, **ext_opts):
        captcha_id = yield from self._send_captcha(captcha, **ext_opts)
        resolved = yield from self._get_captcha(captcha_id)
        return captcha_id, resolved

    @asyncio.coroutine
    def _send_captcha(self, captcha, **ext_opts):
        data = aiohttp.helpers.FormData((('key', self._api_key),))

        if isinstance(captcha, (bytes, bytearray)):
            captcha = b64encode(captcha)
            data.add_fields(('method', 'base64'), ('body', captcha.decode()))
        elif isinstance(captcha, io.IOBase):
            data.add_field('method', 'post')
            data.add_field('file', captcha, filename='cap',
                           content_type='multipart/form-data')
        else:
            raise ServiceError('Unsupported captcha type')

        if ext_opts:
            data.add_fields(list(ext_opts.items()))

        while True:
            resp = yield from self._session.post(
                self._request_url, data=data)
            try:
                if resp.status >= 400:
                    raise ServiceError('HTTP error [status: %d]' %
                                       resp.status)
                msg = yield from resp.text()

                if msg == 'ERROR_NO_SLOT_AVAILABLE':
                    yield from asyncio.sleep(self._send_interval,
                                             loop=self._loop)
                else:
                    self._handle_error(msg)

                    chunks = msg.split('|', 1)
                    if len(chunks) == 2 and chunks[0].upper() == 'OK':
                        return chunks[1]
                    else:
                        raise ServiceError('Invalid server reply')
            except aiohttp.ClientError as e:
                resp.close()
                raise ServiceError('Network error: %s' % str(e))
            finally:
                yield from resp.release()

    @asyncio.coroutine
    def _get_captcha(self, captcha_id):
        data = {'key': self._api_key, 'action': 'get', 'id': captcha_id}

        while True:
            resp = yield from self._session.get(self._response_url,
                                                params=data)
            try:
                if resp.status >= 400:
                    raise ServiceError('HTTP error [status: %d]' %
                                       resp.status)
                msg = yield from resp.text()

                if msg == 'CAPCHA_NOT_READY':
                    yield from asyncio.sleep(self._check_interval,
                                             loop=self._loop)
                else:
                    self._handle_error(msg)

                    chunks = msg.split('|', 1)
                    if len(chunks) == 2 and chunks[0].upper() == 'OK':
                        return chunks[1]
                    else:
                        raise ServiceError('Invalid server reply')
            except aiohttp.ClientError as e:
                resp.close()
                raise ServiceError('Network error: %s' % str(e))
            finally:
                yield from resp.release()

    @asyncio.coroutine
    def get_balance(self):
        data = {'key': self._api_key, 'action': 'getbalance'}
        resp = yield from self._session.get(self._response_url, params=data)

        try:
            if resp.status >= 400:
                raise ServiceError('HTTP error [status: %d]' % resp.status)
            msg = (yield from resp.text())
            self._handle_error(msg)
            try:
                return float(msg)
            except ValueError:
                raise ServiceError('Invalid server reply')
        except aiohttp.ClientError as e:
            resp.close()
            raise ServiceError('Network error: %s' % str(e))
        finally:
            yield from resp.release()

    @asyncio.coroutine
    def abuse(self, captcha_id):
        data = {'key': self._api_key, 'action': 'reportbad', 'id': captcha_id}
        resp = yield from self._session.get(self._response_url, params=data)

        try:
            if resp.status >= 400:
                raise ServiceError('HTTP error [status: %d]' % resp.status)
            msg = (yield from resp.text())
            self._handle_error(msg)
        except aiohttp.ClientError as e:
            resp.close()
            raise ServiceError('Network error: %s' % str(e))
        finally:
            yield from resp.release()

    def close(self):
        self._session.close()

    def _create_session(self):
        return aiohttp.ClientSession(loop=self._loop)

    def _handle_error(self, msg):
        msg = msg.upper()
        if msg.startswith('ERROR_'):
            errs = {
                'ERROR_WRONG_USER_KEY':
                    UserKeyError('Account authorization key is invalid'),
                'ERROR_KEY_DOES_NOT_EXIST':
                    UserKeyError('Account authorization key '
                                 'not found in the system'),
                'ERROR_ZERO_BALANCE':
                    ZeroBalanceError('Account has zero or negative balance'),
                'ERROR_ZERO_CAPTCHA_FILESIZE':
                    ServiceError('The size of the captcha you are '
                                 'uploading is less than 100 bytes.'),
                'ERROR_IMAGE_TYPE_NOT_SUPPORTED':
                    ServiceError('Could not determine captcha file type'),
                'ERROR_IP_NOT_ALLOWED':
                    ServiceError('Request with current account key '
                                 'is not allowed from your IP'),
                'ERROR_NO_SUCH_CAPCHA_ID':
                    ServiceError('Captcha with such ID was '
                                 'not found in the system'),
                'ERROR_NO_REQUEST_ACTION_RECEIVED':
                    ServiceError('No request action received')
            }
            if msg in errs:
                raise errs[msg]

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class AntiGate(AntiCaptcha):
    def __init__(self, api_key, *, domain='antigate.com', port=80,
                 check_interval=10, send_interval=0.1, loop=None):
        super().__init__(api_key, domain=domain, port=port,
                         check_interval=check_interval, loop=loop,
                         send_interval=send_interval)
