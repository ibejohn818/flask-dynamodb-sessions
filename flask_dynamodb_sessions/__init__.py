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

import pickle
import codecs

__author__ = """John Hardy"""
__email__ = 'john@johnchardy.com'
__version__ = '0.1.8'


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
        conf.setdefault("SESSION_DYNAMODB_USE_HEADER", False)
        conf.setdefault("SESSION_DYNAMODB_HEADER_NAME", 'X-SessionId')
        conf.setdefault("SESSION_DYNAMODB_CONSISTENT_READ", False)

        kw = {
            'table': conf['SESSION_DYNAMODB_TABLE'],
            'endpoint': conf['SESSION_DYNAMODB_ENDPOINT'],
            'region': conf['SESSION_DYNAMODB_REGION'],
            'ttl': conf['SESSION_DYNAMODB_TTL_SECONDS'],
            'permanent': self.permanent,
            'use_header': conf['SESSION_DYNAMODB_USE_HEADER'],
            'header_name': conf['SESSION_DYNAMODB_HEADER_NAME'],
            'consistent_read': conf['SESSION_DYNAMODB_CONSISTENT_READ']
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
        self.use_header = kw.get('use_header', False)
        self.header_name = kw.get('header_name', None)
        self.consistent_read =  bool(kw.get('consistent_read', False))

    def open_session(self, app, req):
        """
        """
        if self.use_header:
            id = req.headers.get(self.header_name)
        else:
            id = req.cookies.get(app.session_cookie_name)
        
        if id is None:
            id = str(uuid4())
            return DynamodbSession(sid=id, permanent=self.permanent)

        data = self.dynamo_get(id)

        if data is not None:
            data = self.hydrate_session(data)

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

        self.dynamo_save(session_id, dict(session))

        if self.use_header:
            res.headers[self.header_name] = session_id
        else:
            res.set_cookie(app.session_cookie_name, session_id,
                                expires=expires, httponly=httponly,
                                domain=domain, path=path, secure=secure)



    def pickle_session(self, session):
        """Pickle the session object and base64 encode it
            for storage as a dynamo string
        """
        pickled = pickle.dumps(session)

        canned = codecs.encode(pickled, 'base64').decode()

        return canned

    def hydrate_session(self, session_data):
        """Base64 decode string back to bytes and unpickle
        """
        uncanned = codecs.decode(session_data.encode(), 'base64')

        pickled = pickle.loads(uncanned)

        return pickled

    def dynamo_get(self, session_id):
        """
        """
        try:
            res = self.boto_client().get_item(TableName=self.table,
                        Key={'id':{'S': session_id}},
                        ConsistentRead=self.consistent_read)
            if res.get('Item').get('data'):
                data = res.get('Item').get('data')
                return data.get('S', '{}')
        except Exception as e:
            print("DYNAMO SESSION GET ITEM ERR: ", str(e))

        return None

    def dynamo_save(self, session_id, session):
        try:
            # print(session)
            fields = {
                'data': {'S': self.pickle_session(session)},
                'modified': {'S': str(datetime.utcnow())},
                'ttl': {'N': str(int(datetime.utcnow().timestamp() + self.ttl))}
            }

            attr_names = {}
            attr_vals = {}
            ud_exp = []
            for k, v in fields.items():
                attr = "#attr_{}".format(k)
                token = ":{}".format(k)
                ud_exp.append("{} = {}".format(attr, token))
                attr_vals[token] = v
                attr_names[attr] = k

            self.boto_client().update_item(TableName=self.table,
                        Key={'id':{'S':session_id}},
                        ExpressionAttributeNames=attr_names,
                        ExpressionAttributeValues=attr_vals,
                        UpdateExpression="SET {}".format(", ".join(ud_exp)),
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
