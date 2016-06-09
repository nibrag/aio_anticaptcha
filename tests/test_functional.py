from base64 import b64encode

import aiohttp
import asyncio
import io
import unittest
from unittest import mock
from aio_anticaptcha import (
    AntiCaptcha, ServiceError, ZeroBalanceError,
    UserKeyError, AntiGate
)
from .helpers import (
    fake_coroutine, fake_client_session
)

api_key = 'd41d8cd98f00b204e9800998ecf8427e'


class AntiCaptchaTestCase(unittest.TestCase):
    def setUp(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(None)

    def tearDown(self):
        self.loop.close()

    def test_ctor(self):
        with self.assertRaises(ValueError) as cm:
            AntiCaptcha('invalid key')
        self.assertIn('api_key must be string 32 bytes', str(cm.exception))

        with self.assertRaises(ValueError) as cm:
            AntiCaptcha(api_key, check_interval=0)
        self.assertIn('check_interval must be integer', str(cm.exception))

        with self.assertRaises(ValueError) as cm:
            AntiCaptcha(api_key, check_interval=-1)
        self.assertIn('check_interval must be integer', str(cm.exception))

        with self.assertRaises(ValueError) as cm:
            AntiCaptcha(api_key, send_interval=0)
        self.assertIn('send_interval must be integer', str(cm.exception))

        with self.assertRaises(ValueError) as cm:
            AntiCaptcha(api_key, send_interval=-1)
        self.assertIn('send_interval must be integer', str(cm.exception))

    def test_create_session(self):
        ag = AntiCaptcha(api_key, loop=self.loop)
        ses = ag._create_session()
        self.assertIsInstance(ses, aiohttp.ClientSession)
        self.assertIs(ses._loop, ag._loop)
        ses.close()
        ag.close()

    def test_close(self):
        ag = AntiCaptcha(api_key, loop=self.loop)
        self.assertFalse(ag._session.closed)
        ag.close()
        self.assertTrue(ag._session.closed)

    def test_enter_ctx(self):
        ag = AntiCaptcha(api_key, loop=self.loop)
        ses = ag._session
        ag.__enter__()
        self.assertIs(ses, ag._session)
        ag.close()

    def test_exit_ctx(self):
        with AntiCaptcha(api_key, loop=self.loop) as ag:
            self.assertIsInstance(ag._session, aiohttp.ClientSession)
        self.assertTrue(ag._session.closed)

    def test_handle_error(self):
        ag = AntiCaptcha(api_key, loop=self.loop)
        with self.assertRaises(UserKeyError) as cm:
            ag._handle_error('ERROR_WRONG_USER_KEY')
        self.assertIn('Account authorization key is invalid',
                      str(cm.exception))

        with self.assertRaises(UserKeyError) as cm:
            ag._handle_error('ERROR_KEY_DOES_NOT_EXIST')
        self.assertIn('Account authorization key', str(cm.exception))

        with self.assertRaises(ZeroBalanceError) as cm:
            ag._handle_error('ERROR_ZERO_BALANCE')
        self.assertIn('Account has zero or negative balance',
                      str(cm.exception))

        with self.assertRaises(ServiceError) as cm:
            ag._handle_error('ERROR_ZERO_CAPTCHA_FILESIZE')
        self.assertIn('The size of the captcha you are',
                      str(cm.exception))

        with self.assertRaises(ServiceError) as cm:
            ag._handle_error('ERROR_IMAGE_TYPE_NOT_SUPPORTED')
        self.assertIn('Could not determine captcha file type',
                      str(cm.exception))

        with self.assertRaises(ServiceError) as cm:
            ag._handle_error('ERROR_IP_NOT_ALLOWED')
        self.assertIn('Request with current account key',
                      str(cm.exception))

        with self.assertRaises(ServiceError) as cm:
            ag._handle_error('ERROR_NO_SUCH_CAPCHA_ID')
        self.assertIn('Captcha with such ID was', str(cm.exception))

        with self.assertRaises(ServiceError) as cm:
            ag._handle_error('ERROR_NO_REQUEST_ACTION_RECEIVED')
        self.assertIn('No request action received', str(cm.exception))
        ag.close()

    def test_abuse_http_err(self):
        ag = AntiCaptcha(api_key, loop=self.loop)
        ag.close()
        ag._session = fake_client_session(400, 'OK')

        with self.assertRaises(ServiceError) as cm:
            self.loop.run_until_complete(ag.abuse(123))
        self.assertIn('HTTP error', str(cm.exception))

    def test_abuse_handle_error(self):
        ag = AntiCaptcha(api_key, loop=self.loop)
        ag.close()
        ag._session = fake_client_session(
            200, 'ERROR_NO_REQUEST_ACTION_RECEIVED')

        with self.assertRaises(ServiceError) as cm:
            self.loop.run_until_complete(ag.abuse(123))
        self.assertIn('No request action received', str(cm.exception))

    def test_abuse_client_error(self):
        ag = AntiCaptcha(api_key, loop=self.loop)
        ag.close()
        ag._session, resp = fake_client_session(
            200, aiohttp.ClientError(), ret_resp=True)

        with self.assertRaises(ServiceError) as cm:
            self.loop.run_until_complete(ag.abuse(123))
        self.assertIn('Network error', str(cm.exception))
        self.assertTrue(resp.release.called)
        self.assertTrue(resp.close.called)

    def test_get_balance_http_err(self):
        ag = AntiCaptcha(api_key, loop=self.loop)
        ag.close()
        ag._session = fake_client_session(400, 'OK')

        with self.assertRaises(ServiceError) as cm:
            self.loop.run_until_complete(ag.get_balance())
        self.assertIn('HTTP error', str(cm.exception))

    def test_get_balance_handle_error(self):
        ag = AntiCaptcha(api_key, loop=self.loop)
        ag.close()
        ag._session = fake_client_session(
            200, 'ERROR_NO_REQUEST_ACTION_RECEIVED')

        with self.assertRaises(ServiceError) as cm:
            self.loop.run_until_complete(ag.get_balance())
        self.assertIn('No request action received', str(cm.exception))

    def test_get_balance_client_error(self):
        ag = AntiCaptcha(api_key, loop=self.loop)
        ag.close()
        ag._session, resp = fake_client_session(
            200, aiohttp.ClientError(), ret_resp=True)

        with self.assertRaises(ServiceError) as cm:
            self.loop.run_until_complete(ag.get_balance())
        self.assertIn('Network error', str(cm.exception))
        self.assertTrue(resp.release.called)
        self.assertTrue(resp.close.called)

    def test_get_balance_inv_reply(self):
        ag = AntiCaptcha(api_key, loop=self.loop)
        ag.close()
        ag._session = fake_client_session(200, 'abc')

        with self.assertRaises(ServiceError) as cm:
            self.loop.run_until_complete(ag.get_balance())
        self.assertIn('Invalid server reply', str(cm.exception))

    def test_get_balance_ok(self):
        ag = AntiCaptcha(api_key, loop=self.loop)
        ag.close()
        ag._session = fake_client_session(200, '0.5')

        balance = self.loop.run_until_complete(ag.get_balance())
        self.assertEqual(balance, 0.5)

    def test_get_captcha_http_err(self):
        ag = AntiCaptcha(api_key, loop=self.loop)
        ag.close()
        ag._session = fake_client_session(400, 'OK')

        with self.assertRaises(ServiceError) as cm:
            self.loop.run_until_complete(ag._get_captcha('id'))
        self.assertIn('HTTP error', str(cm.exception))

    def test_get_captcha_handle_error(self):
        ag = AntiCaptcha(api_key, loop=self.loop)
        ag.close()
        ag._session = fake_client_session(
            200, 'ERROR_NO_REQUEST_ACTION_RECEIVED')

        with self.assertRaises(ServiceError) as cm:
            self.loop.run_until_complete(ag._get_captcha('id'))
        self.assertIn('No request action received', str(cm.exception))

    def test_get_captcha_client_error(self):
        ag = AntiCaptcha(api_key, loop=self.loop)
        ag.close()
        ag._session, resp = fake_client_session(
            200, aiohttp.ClientError(), ret_resp=True)

        with self.assertRaises(ServiceError) as cm:
            self.loop.run_until_complete(ag._get_captcha('id'))
        self.assertIn('Network error', str(cm.exception))
        self.assertTrue(resp.release.called)
        self.assertTrue(resp.close.called)

    def test_get_captcha_inv_reply(self):
        ag = AntiCaptcha(api_key, loop=self.loop)
        ag.close()
        ag._session = fake_client_session(200, 'abc')

        with self.assertRaises(ServiceError) as cm:
            self.loop.run_until_complete(ag._get_captcha('id'))
        self.assertIn('Invalid server reply', str(cm.exception))

    def test_get_captcha_ok(self):
        ag = AntiCaptcha(api_key, loop=self.loop)
        ag.close()
        ag._session = fake_client_session(200, 'OK|123')

        cid = self.loop.run_until_complete(ag._get_captcha('id'))
        self.assertEqual(cid, '123')

    @mock.patch('aio_anticaptcha.asyncio.sleep')
    def test_get_captcha_not_ready(self, sleep_mock):
        sleep_mock.side_effect = fake_coroutine(1)

        ag = AntiCaptcha(api_key, loop=self.loop)
        ag.close()
        ag._session = fake_client_session(
            200, ['CAPCHA_NOT_READY', 'OK|123'], iter_v=True)

        cid = self.loop.run_until_complete(ag._get_captcha('id'))
        self.assertEqual(cid, '123')
        self.assertEqual(ag._session.get.call_count, 2)
        sleep_mock.assert_called_with(ag._check_interval, loop=ag._loop)

    @mock.patch('aio_anticaptcha.aiohttp.helpers.FormData.add_fields')
    def test_send_captcha_base64(self, add_fields):
        ag = AntiCaptcha(api_key, loop=self.loop)
        ag.close()
        ag._session = fake_client_session(200, 'OK|123')

        self.loop.run_until_complete(ag._send_captcha(b'base64'))
        add_fields.assert_called_with(
            ('method', 'base64'), ('body', b64encode(b'base64').decode()))

    @mock.patch('aio_anticaptcha.aiohttp.helpers.FormData.add_field')
    def test_send_captcha_io_base(self, add_field):
        ag = AntiCaptcha(api_key, loop=self.loop)
        ag.close()
        ag._session = fake_client_session(200, 'OK|123')

        f = io.StringIO()
        self.loop.run_until_complete(ag._send_captcha(f))
        self.assertEqual(add_field.call_count, 3)
        add_field.assert_any_call('method', 'post')
        add_field.assert_any_call('key', api_key)
        add_field.assert_any_call('file', f, filename='cap',
                                  content_type='multipart/form-data')

    def test_send_captcha_wrong_format(self):
        ag = AntiCaptcha(api_key, loop=self.loop)
        ag.close()

        with self.assertRaises(ServiceError) as cm:
            self.loop.run_until_complete(ag._send_captcha('str'))
        self.assertIn('Unsupported captcha type', str(cm.exception))

    @mock.patch('aio_anticaptcha.aiohttp.helpers.FormData.add_fields')
    def test_send_captcha_ext_opts(self, add_fields):
        ag = AntiCaptcha(api_key, loop=self.loop)
        ag.close()
        ag._session = fake_client_session(200, 'OK|123')

        self.loop.run_until_complete(ag._send_captcha(b'base64', b=2))
        self.assertEqual(add_fields.call_count, 3)

        add_fields.assert_any_call(
            ('method', 'base64'), ('body', b64encode(b'base64').decode()))
        add_fields.assert_any_call([('b', 2)])

    def test_send_captcha_http_err(self):
        ag = AntiCaptcha(api_key, loop=self.loop)
        ag.close()
        ag._session = fake_client_session(400, 'OK|123')

        with self.assertRaises(ServiceError) as cm:
            self.loop.run_until_complete(ag._send_captcha(b'base64'))
        self.assertIn('HTTP error', str(cm.exception))

    def test_send_captcha_handle_err(self):
        ag = AntiCaptcha(api_key, loop=self.loop)
        ag.close()
        ag._session = fake_client_session(
            200, 'ERROR_NO_REQUEST_ACTION_RECEIVED')

        with self.assertRaises(ServiceError) as cm:
            self.loop.run_until_complete(ag._send_captcha(b'id'))
        self.assertIn('No request action received', str(cm.exception))

    def test_send_captcha_client_error(self):
        ag = AntiCaptcha(api_key, loop=self.loop)
        ag.close()
        ag._session, resp = fake_client_session(
            200, aiohttp.ClientError(), ret_resp=True)

        with self.assertRaises(ServiceError) as cm:
            self.loop.run_until_complete(ag._send_captcha(b'id'))
        self.assertIn('Network error', str(cm.exception))
        self.assertTrue(resp.release.called)
        self.assertTrue(resp.close.called)

    def test_send_captcha_inv_reply(self):
        ag = AntiCaptcha(api_key, loop=self.loop)
        ag.close()
        ag._session = fake_client_session(200, 'abc')

        with self.assertRaises(ServiceError) as cm:
            self.loop.run_until_complete(ag._send_captcha(b'id'))
        self.assertIn('Invalid server reply', str(cm.exception))

    def test_send_captcha_ok(self):
        ag = AntiCaptcha(api_key, loop=self.loop)
        ag.close()
        ag._session = fake_client_session(200, 'OK|123')

        cid = self.loop.run_until_complete(ag._send_captcha(b'id'))
        self.assertEqual(cid, '123')

    @mock.patch('aio_anticaptcha.asyncio.sleep')
    def test_send_captcha_not_ready(self, sleep_mock):
        sleep_mock.side_effect = fake_coroutine(1)

        ag = AntiCaptcha(api_key, loop=self.loop)
        ag.close()
        ag._session = fake_client_session(
            200, ['ERROR_NO_SLOT_AVAILABLE', 'OK|123'], iter_v=True)

        cid = self.loop.run_until_complete(ag._send_captcha(b'id'))
        self.assertEqual(cid, '123')
        self.assertEqual(ag._session.post.call_count, 2)
        sleep_mock.assert_called_with(ag._send_interval, loop=ag._loop)

    def test_resolve(self):
        ag = AntiCaptcha(api_key, loop=self.loop)
        ag.close()
        ag._session = fake_client_session(200, ['OK|123', 'OK|234'],
                                          iter_v=True)

        cid = self.loop.run_until_complete(ag.resolve(b'id'))
        self.assertEqual(cid, ('123', '234'))

    def test_antigate(self):
        ag = AntiGate(api_key, loop=self.loop)
        ag.close()

        self.assertIn('antigate.com', ag._request_url)
