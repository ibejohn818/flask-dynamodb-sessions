# Flask DynamoDB Sessions

[![](https://img.shields.io/pypi/v/flask-dynamodb-sessions.svg)](https://pypi.org/project/flask-dynamodb-sessions/) [![Updates](https://pyup.io/repos/github/ibejohn818/flask-dynamodb-sessions/shield.svg)](https://pyup.io/repos/github/ibejohn818/flask-dynamodb-sessions/)

Server-side sessions in Flask using AWS DynamoDB as the backend data store.

DynamoDB is AWS's SaaS NoSQL solution which makes it perfect for use as a session store. 
Being a SaaS service we no longer have to manage servers/storage/etc and take advantage of some notable features such as:

- Auto-scaling
- Automatic Lifecycle ( Garbage collection )
- Encryption at rest
- etc...

Sessions are pickled and base64 encoded to be stored in DynamoDB as strings. As a result you may save
objects to your sessions as long as the object supports the pickle interface.

DynamoDB supports a maximum object size of 400 KB. Minus the UUID4 session id, modified date/time string and ttl timestamp
you have approximately 398 KB available for your session.

## Installation

```shell
# w/ pip
pip install flask-dynamodb-sessions
#  w/ easy_install
easy_install flask-dynamodb-sessions
```

### Usage example
```python
from flask import (Flask, session)
from flask_dynamodb_sessions import Session

app = Flask(__name__)

# Set flask to use the dynamo session interface
Session(app)

@app.route('/', methods=['GET'])
def index_get():
	# use sessions just as you normally would
	session['user'] = {'username': 'jhardy'}
	
	user = session.get('user')
	
	session_id = session.sid
```
*View examples directory for more*

### Configuration Options
Below are additional `SESSION_*` configuration options specific to DynamoDB sessions.

    SESSION_DYNAMODB_TABLE (string): The DynamoDB table to save to. Default: flask_sessions
    SESSION_DYNAMODB_ENDPOINT (string): Override the boto3 endpoint, good for local development and using dynamodb-local. Default: None
    SESSION_DYNAMODB_TTL_SECONDS (int): Number of seconds to add to the TTL column. Default: 86400 * 14 (14 Days)

The existing `SESSION_*` config parameters still apply (IE: cookie settings). SESSION_REFRESH_EACH_REQUEST 
is the only setting that is negated and each request will refesh the cookie (Might be modified in a future release).

### Table Structure
The table structure is fairly simple.
```
{
    id: string HASH,
    modified: string DATETIME UTC
    ttl: number UTC TIME + SESSION_DYANMODB_TTL_SECONDS
    data: string JSON ENCODED SESSION

}
```

Create the table VIA `aws` cli.

```
aws dynamodb create-table --key-schema "AttributeName=id,KeyType=HASH" \
--attribute-definitions "AttributeName=id,AttributeType=S" \
--provisioned-throughput "ReadCapacityUnits=5,WriteCapacityUnits=5" \
--table-name flask_sessions
```

The `ttl` column is present to take advantage of DynamoDB's `Lifecycle` feature where dynamo will delete all rows with a ttl in the past.

Enable time-to-live (garbage collection)

```
aws dynamodb update-time-to-live --time-to-live-specification 'Enabled=true,AttributeName=ttl' --table-name flask_sessions
```



## TODO
- Test coverage
- More laxed cookie refresh
