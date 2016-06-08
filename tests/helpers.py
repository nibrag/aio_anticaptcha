import asyncio
from unittest import mock


def fake_coroutine(return_value, iter_v=False):
    def coro(*args, **kwargs):
        if iter_v:
            value = next(return_value)
        else:
            value = return_value

        if isinstance(value, Exception):
            raise value
        return value

    return mock.Mock(side_effect=asyncio.coroutine(coro))


def fake_resp(status, text):
    resp = mock.Mock()
    resp.status = status
    resp.text = fake_coroutine(text)
    resp.release = fake_coroutine(True)
    return resp


def fake_client_session(status, text, ret_resp=False, iter_v=False):
    session = mock.Mock()

    if iter_v:
        resp = map(lambda t: fake_resp(status, t), text)
    else:
        resp = fake_resp(status, text)

    session.get = fake_coroutine(resp, iter_v=iter_v)
    session.post = fake_coroutine(resp, iter_v=iter_v)

    if ret_resp:
        return session, resp
    return session
