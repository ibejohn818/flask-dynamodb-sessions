# -*- coding: utf-8 -*-

"""
Flask DynamoDB Sessions

This module will use AWS DynamoDB as your session store in Flask.

"""
import sys
import time
from datetime import datetime
from uuid import uuid4
from flask.sessions import SessionInterface
from flask.sessions import SessionMixin
from werkzeug.datastructures import CallbackDict
import json
import boto3

PV3 = sys.version_info[0] == 3

__author__ = """John Hardy"""
__email__ = 'john@johnchardy.com'
__version__ = '0.1.3'


class Session(object):

    def __init__(self, app=None, **kw):
        self.app = app
        self.permanent = kw.get('permanent', True)

        if self.app is not None:
            self.init(self.app)

    def init(self, app):

        conf = app.config.copy()

        conf.setdefault("SESSION_DYNAMODB_ENDPOINT", None)
        conf.setdefault("SESSION_DYNAMODB_REGION", None)
        conf.setdefault("SESSION_DYNAMODB_TABLE", 'flask_sessions')
        conf.setdefault("SESSION_DYNAMODB_TTL_SECONDS", (86400 * 14))

        kw = {
            'table': conf['SESSION_DYNAMODB_TABLE'],
            'endpoint': conf['SESSION_DYNAMODB_ENDPOINT'],
            'region': conf['SESSION_DYNAMODB_REGION'],
            'ttl': conf['SESSION_DYNAMODB_TTL_SECONDS'],
            'permanent': self.permanent,
        }

        interface = DynamodbSessionInterface(**kw)

        app.session_interface = interface

class DynamodbSession(CallbackDict, SessionMixin):

    def __init__(self, initial=None, sid=None, permanent=None):
        def on_update(self):
            self.modified = True
        CallbackDict.__init__(self, initial, on_update)
        self.sid = sid
        if permanent:
            self.permanent = permanent
        self.modified = False


class DynamodbSessionInterface(SessionInterface):
    """
    """
    _boto_client = None

    def __init__(self, **kw):
        self.table = kw.get('table', 'flask_sessions')
        self.permanent = kw.get('permanent', True)
        self.endpoint = kw.get('endpoint', None)
        self.region = kw.get('region', None)
        self.ttl = kw.get('ttl', None)

    def open_session(self, app, req):
        """
        """
        id = req.cookies.get(app.session_cookie_name)

        if id is None:
            id = str(uuid4())
            return DynamodbSession(sid=id, permanent=self.permanent)

        data = self.dynamo_get(id)

        return DynamodbSession(data, sid=id, permanent=self.permanent)

    def save_session(self, app, session, res):
        """
        """
        domain = self.get_cookie_domain(app)
        path = self.get_cookie_path(app)
        if not session:
            if session.modified:
                self.delete_session(session.sid)
                res.delete_cookie(app.session_cookie_name,
                                       domain=domain, path=path)
            return

        # if not self.should_set_cookie(app, session):
        #    return

        httponly = self.get_cookie_httponly(app)
        secure = self.get_cookie_secure(app)
        expires = self.get_expiration_time(app, session)
        session_id = session.sid

        val = json.dumps(dict(session), default=str)

        self.dynamo_save(session_id, val)
        res.set_cookie(app.session_cookie_name, session_id,
                            expires=expires, httponly=httponly,
                            domain=domain, path=path, secure=secure)

    def dynamo_get(self, session_id):
        """
        """
        try:
            res = self.boto_client().get_item(TableName=self.table,
                        Key={'id':{'S': session_id}})
            if res.get('Item').get('data'):
                data = res.get('Item').get('data')
                return json.loads(data.get('S', '{}'))
        except Exception as e:
            print("DYNAMO SESSION GET ITEM ERR: ", str(e))

        return None

    def dynamo_save(self, session_id, json_str):
        try:
            self.boto_client().update_item(TableName=self.table,
                        Key={'id':{'S':session_id}},
                        ExpressionAttributeNames={'#pf_data': 'data',
                                                  '#pf_modified': 'modified',
                                                  '#pf_ttl': 'ttl'},
                        ExpressionAttributeValues={':data': {'S':json_str},
                                                   ':modified': {'S':str(datetime.utcnow())},
                                                   ':ttl': {'N': str(int(datetime.utcnow().timestamp() + self.ttl))},
                                                   },
                        UpdateExpression="SET #pf_data = :data, #pf_modified = :modified, #pf_ttl = :ttl",
                        ReturnValues='NONE')
        except Exception as e:
            print("DYNAMO SESSION SAVE ERR: ", str(e))

    def delete_session(self, session_id):
        try:
            self.boto_client().delete_item(TableName=self.table,
                        Key={'id':{'S':session_id}})
        except Exception as e:
            print("DYNAMO SESSION DELETE ERR: ", str(e))

    def boto_client(self):
        """
        """
        if self._boto_client is None:
            kw = {}

            if self.endpoint is not None:
                kw['endpoint_url'] = self.endpoint
            if self.region is not None:
                kw['region_name'] = self.region

            self._boto_client = boto3.client('dynamodb', **kw)

        return self._boto_client
