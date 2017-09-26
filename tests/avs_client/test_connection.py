from io import BytesIO
import json
from unittest.mock import patch

import pytest
from requests.exceptions import HTTPError

from avs_client.avs_client import connection
from tests.avs_client.helpers import parse_multipart, TestConnectionMixin
from tests.avs_client import fixtures


class TestConnectionManager(TestConnectionMixin, connection.ConnectionManager):
    @staticmethod
    def generate_dialogue_id():
        # override existing non-deterministic method
        return 'dialogue-id'

    @staticmethod
    def generate_message_id():
        # override existing non-deterministic method
        return 'message-id'


@pytest.fixture
def manager():
    return TestConnectionManager()


@pytest.fixture
def authentication_headers():
    return {'auth': 'value'}


@pytest.fixture
def device_state():
    return {'device': 'state'}


@pytest.fixture
def audio_file():
    return BytesIO(b'things')


def test_create_connection(manager):
    manager.create_connection()

    assert manager.connection.host == 'avs-alexa-eu.amazon.com'
    assert manager.connection.secure is True


def test_establish_downstream_conncetion(manager, authentication_headers):
    manager.create_connection()

    manager.establish_downchannel_stream(
        authentication_headers=authentication_headers
    )

    headers = dict(list(manager.connection.recent_stream.headers.items()))

    assert headers == {
        b':scheme': b'https',
        b':method': b'GET',
        b':path': b'/v20160207/directives',
        b':authority': b'avs-alexa-eu.amazon.com',
        b'auth': b'value',
    }


@pytest.mark.parametrize("status", [200, 204])
def test_synchronise_device_state(
    status, manager, authentication_headers, device_state
):
    manager.create_connection()
    manager.mock_response(status_code=204 or status_code=200)

    manager.synchronise_device_state(
        authentication_headers=authentication_headers,
        device_state=device_state,
    )

    headers = dict(list(manager.connection.recent_stream.headers.items()))

    assert headers == {
        b':method': b'GET',
        b':scheme': b'https',
        b':authority': b'avs-alexa-eu.amazon.com',
        b':path': b'/v20160207/events',
        b'content-type': b'multipart/form-data; boundary=boundary',
        b'auth': b'value',
    }
    parsed = parse_multipart(
        body=manager.connection._sock.queue[1],
        content_type=headers[b'content-type'].decode(),
    )

    assert parsed.parts[0].headers == {
        b'Content-Disposition': (
            b'form-data; name="metadata"; filename="metadata"'
        ),
        b'Content-Type': b'application/json'
    }

    assert json.loads(parsed.parts[0].content.decode()) == {
        'context': device_state,
        'event': {
            'header': {
                'messageId': '',
                'name': 'SynchronizeState',
                'namespace': 'System'
            },
            'payload': {}
        },
    }


def test_send_audio_file(
    manager, audio_file, device_state, authentication_headers
):
    manager.create_connection()
    manager.mock_response(status_code=200)

    with patch.object(manager, 'parse_response'):  # test request only
        manager.send_audio_file(
            device_state=device_state,
            authentication_headers=authentication_headers,
            audio_file=audio_file,
        )

    headers = dict(list(manager.connection.recent_stream.headers.items()))

    assert headers == {
        b':method': b'POST',
        b':scheme': b'https',
        b':authority': b'avs-alexa-eu.amazon.com',
        b':path': b'/v20160207/events',
        b'content-type': b'multipart/form-data; boundary=boundary',
        b'auth': b'value',
    }
    parsed = parse_multipart(
        body=manager.connection._sock.queue[1],
        content_type=headers[b'content-type'].decode(),
    )

    assert parsed.parts[0].headers == {
        b'Content-Type': b'application/json;',
        b'Content-Disposition': (
            b'form-data; name="request"; filename="request"'
        )
    }

    assert json.loads(parsed.parts[0].content.decode()) == {
        'context': device_state,
        'event': {
            'payload': {
                'profile': 'CLOSE_TALK',
                'format': 'AUDIO_L16_RATE_16000_CHANNELS_1'
            },
            'header': {
                'namespace': 'SpeechRecognizer',
                'dialogRequestId': 'dialogue-id',
                'name': 'Recognize',
                'messageId': 'message-id'
            }
        },
    }

    assert parsed.parts[1].headers == {
        b'Content-Type': b'application/octet-stream',
        b'Content-Disposition': b'form-data; name="audio"; filename="audio"'
    }
    assert parsed.parts[1].content == b'things'


def test_parse_response_200(
    manager, audio_file, device_state, authentication_headers
):
    manager.create_connection()

    manager.mock_response(
        data=fixtures.audio_response_multipart,
        headers=[
            (b'access-control-allow-origin', b'*'),
            (b'x-amzn-requestid', b'06aaf3fffec6be28-00003161-00006c28'),
            (
                b'content-type',
                (
                    b'multipart/related;'
                    b'boundary=22b41228-f803-447b-9cde-f99d0a1652b1;'
                    b'start=metadata.1503696654430;type="application/json"'
                )
            )
        ],
        status_code=200
    )

    audio_data = manager.send_audio_file(
        audio_file=audio_file,
        device_state=device_state,
        authentication_headers=authentication_headers,
    )

    assert audio_data == fixtures.audio_response_data


def test_send_audio_204_response(
    manager, audio_file, authentication_headers, device_state
):
    manager.create_connection()
    manager.mock_response(status_code=204)

    response = manager.send_audio_file(
        device_state=device_state,
        authentication_headers=authentication_headers,
        audio_file=audio_file,
    )

    assert response is None


@pytest.mark.parametrize(
    "status",  [code for code in range(200, 600) if code not in [200, 204]]
)
def test_send_audio_non_200_response(
    status, audio_file, manager, device_state, authentication_headers
):
    manager.create_connection()
    manager.mock_response(status_code=status)

    with pytest.raises(HTTPError):
        manager.send_audio_file(
            device_state=device_state,
            authentication_headers=authentication_headers,
            audio_file=audio_file,
        )


def test_ping(manager, authentication_headers):
    manager.create_connection()
    manager.mock_response(status_code=204)

    manager.ping(
        authentication_headers=authentication_headers
    )

    headers = dict(list(manager.connection.recent_stream.headers.items()))

    assert headers == {
        b':scheme': b'https',
        b':method': b'GET',
        b':path': b'/ping',
        b':authority': b'avs-alexa-eu.amazon.com',
        b'auth': b'value',
    }
