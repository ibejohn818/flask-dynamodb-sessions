import pytest
import re
from pytest_mock import mocker
import flask
import flask.sessions
from flask_dynamodb_sessions import Session


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
