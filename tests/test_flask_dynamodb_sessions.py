import pytest
from pytest_mock import mocker
import flask
from flask_dynamodb_sessions import Session


def test_session_boto_settings(mocker):

    client_mock = mocker.patch('flask_dynamodb_sessions.boto3.client')

    app = flask.Flask(__name__)

    app.config.update(
        SESSION_DYNAMODB_REGION='bogus-region',
        SESSION_DYNAMODB_ENDPOINT='http://bogus:1234'
    )
