import pytest
import re
from mock import call
from pytest_mock import mocker
import flask
import flask.sessions
from flask_dynamodb_sessions import (
    DynamodbSessionInterface,
    Session
)


def test_session_boto_settings(mocker):

    client_mock = mocker.patch('flask_dynamodb_sessions.boto3.client')

    app = flask.Flask(__name__)

    app.config.update(
        SESSION_DYNAMODB_REGION='bogus-region',
        SESSION_DYNAMODB_ENDPOINT='http://bogus:1234'
    )


def create_test_app(**kwargs):
    app = flask.Flask(__name__)
    app.config.update(**kwargs)
    Session(app)

    @app.route('/test_route')
    def test_route():
        flask.session['x'] = 'foo'
        return flask.make_response('', 200)

    return app


def test_save_uses_header(mocker):
    boto_mock = mocker.patch('flask_dynamodb_sessions.boto3.client')
    boto_mock_instance = boto_mock()

    app = create_test_app(
        SESSION_DYNAMODB_USE_HEADER=True
    )
    mocker.spy(boto_mock, 'update_item')

    response = app.test_client().get('/test_route')

    # Find the session ID that was passed to update_item()
    session_id = None
    match = re.search("Key={'id': {'S': '(.+?)'}}", str(boto_mock_instance.update_item.call_args))
    if match:
        session_id = match.group(1)

    assert 'X-SessionId' in response.headers
    assert response.headers['X-SessionId'] == session_id
    assert 'Set-Cookie' not in response.headers


def test_read_uses_header(mocker):
    expected_session_id = 'foobar'
    boto_mock = mocker.patch('flask_dynamodb_sessions.boto3.client')
    boto_mock_instance = boto_mock()
    boto_mock_instance.get_item.return_value = {'Item': {'data': ''}}

    app = create_test_app(
        SESSION_DYNAMODB_USE_HEADER=True
    )
    mocker.spy(boto_mock, 'get_item')

    response = app.test_client().get('/test_route', headers={'X-SessionId': expected_session_id})

    # Find the session ID that was passed to get_item()
    actual_session_id = None
    match = re.search("Key={'id': {'S': '(.+?)'}}", str(boto_mock_instance.get_item.call_args))
    if match:
        actual_session_id = match.group(1)

    assert actual_session_id == expected_session_id


def test_consistent_read_default_false(mocker):
    boto_mock = mocker.patch('flask_dynamodb_sessions.boto3.client')
    boto_mock_instance = boto_mock()
    boto_mock_instance.get_item.return_value = {'Item': {'data': ''}}

    app = create_test_app(
        SESSION_DYNAMODB_USE_HEADER=True
    )
    mocker.spy(boto_mock, 'get_item')

    response = app.test_client().get('/test_route', headers={'X-SessionId': 'foo'})

    # Validate ConsistentRead setting
    assert 'ConsistentRead=False' in str(boto_mock_instance.get_item.call_args)


def test_consistent_read_true(mocker):
    boto_mock = mocker.patch('flask_dynamodb_sessions.boto3.client')
    boto_mock_instance = boto_mock()
    boto_mock_instance.get_item.return_value = {'Item': {'data': ''}}

    app = create_test_app(
        SESSION_DYNAMODB_USE_HEADER=True,
        SESSION_DYNAMODB_CONSISTENT_READ=True
    )
    mocker.spy(boto_mock, 'get_item')

    response = app.test_client().get('/test_route', headers={'X-SessionId': 'foo'})

    # Validate ConsistentRead setting
    assert 'ConsistentRead=True' in str(boto_mock_instance.get_item.call_args)


class TestDynamodbSessionInterface:
    """ Test DynamodbSessionInterface class
    """

    def test_open_session_use_header(self, mocker):
        """ Test open_session method using
            use_header setting. We should
            exercise a dynamo_get and hydrate
            data. A session should be returned
            with hydrated data and header value
            as sid.
        """
        req_mock = mocker.MagicMock(flask.wrappers.Request)
        app_mock = mocker.MagicMock(flask.Flask)
        ddb_sess_patch = mocker.patch('flask_dynamodb_sessions.DynamodbSession')
        ddb_get_patch = mocker.patch('flask_dynamodb_sessions.DynamodbSessionInterface.dynamo_get')
        hydrate_patch = mocker.patch('flask_dynamodb_sessions.DynamodbSessionInterface.hydrate_session')

        req_mock.headers.get.return_value = 'mock-header'
        ddb_get_patch.return_value = {'key': 'mock-sess-data'}
        hydrate_patch.return_value = {'key': 'mock-hydrate-data'}


        dbi = DynamodbSessionInterface(use_header=True)

        _ = dbi.open_session(app_mock, req_mock)

        # dynamo_get should be called with our mock header data
        assert ddb_get_patch.mock_calls == \
            [call('mock-header')]

        # hydrate_session should be called with mock get data
        assert hydrate_patch.mock_calls == \
            [call({'key': 'mock-sess-data'})]

        # our dynamo session patch should be called
        # with our mock hydrate data and mock header
        assert ddb_sess_patch.mock_calls == \
            [call({'key': 'mock-hydrate-data'},
                  permanent=True,
                  sid='mock-header')]

    def test_open_session_use_cookie(self, mocker):
        """ Test open_session method using
            default cookie settings. A session
            should be created with the cookie
            data as sid and we will return no
            session data from dynamo_get.
        """
        req_mock = mocker.MagicMock(flask.wrappers.Request)
        app_mock = mocker.MagicMock(flask.Flask)
        ddb_sess_patch = mocker.patch('flask_dynamodb_sessions.DynamodbSession')
        ddb_get_patch = mocker.patch('flask_dynamodb_sessions.DynamodbSessionInterface.dynamo_get')
        hydrate_patch = mocker.patch('flask_dynamodb_sessions.DynamodbSessionInterface.hydrate_session')

        req_mock.cookies.get.return_value = 'mock-cookie'
        ddb_get_patch.return_value = None

        dbi = DynamodbSessionInterface()

        _ = dbi.open_session(app_mock, req_mock)

        # dynamo_get patch should be called with
        # mock cookie data
        assert ddb_get_patch.mock_calls == \
            [call('mock-cookie')]

        # hydrate should not have been called
        assert hydrate_patch.call_count == 0

        # check dynamo session mock calls
        assert ddb_sess_patch.mock_calls == \
            [call(None, permanent=True, sid='mock-cookie')]


    def test_open_session_new_session(self, mocker):
        """ Test open_session method with
            defaults. Should return a fresh
            session and exec uuid4()
        """
        req_mock = mocker.MagicMock(flask.wrappers.Request)
        app_mock = mocker.MagicMock(flask.Flask)
        ddb_sess_patch = mocker.patch('flask_dynamodb_sessions.DynamodbSession')
        uuid_patch = mocker.patch('flask_dynamodb_sessions.uuid4')

        # new session value that should be used
        uuid_patch.return_value = 'mock-uuid'

        # have cookie return none like a fresh session
        req_mock.cookies.get.return_value = None

        dbi = DynamodbSessionInterface()

        _  = dbi.open_session(app_mock, req_mock)

        # check dynamo session calls
        assert ddb_sess_patch.mock_calls == \
            [call(permanent=True, sid='mock-uuid')]

