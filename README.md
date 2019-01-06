# Flask DynamoDB Sessions

[![](https://img.shields.io/pypi/v/flask-dynamodb-sessions.svg)](https://pypi.org/project/flask-dynamodb-sessions/) [![Updates](https://pyup.io/repos/github/ibejohn818/flask-dynamodb-sessions/shield.svg)](https://pyup.io/repos/github/ibejohn818/flask-dynamodb-sessions/)

Server-side sessions in Flask using AWS DynamoDB as the backend data store.

DynamoDB is AWS's SaaS NoSQL solution which makes it perfect for use as a session store. 
Being a SaaS service we no longer have to manage servers/storage/etc and take advantage of some notable features such as:

- Auto-scaling
- Automatic Lifecycle ( Garbage collection )
- Encryption at rest
- etc...

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

The session dictionary is serialized using `json.dumps({SESSION}, default=str)`. More advanced serialization is in-progress.

### Configuration Options
Below are additional `SESSION_*` configuration options specific to DynamoDB sessions.

    SESSION_DYNAMODB_TABLE (string): The DynamoDB table to save to. Default: flask_sessions
    SESSION_DYNAMODB_ENDPOINT (string): Override the boto3 endpoint, good for local development and using dynamodb-local. Default: None
    SESSION_DYNAMODB_TTL_SECONDS (int): Number of seconds to add to the TTL column. Default: 86400 * 14 (14 Days)

The existing `SESSION_*` config parameters still apply (IE: cookie settings). SESSION_REFRESH_EACH_REQUEST is the only setting that is negated and each request will refesh the cookie (Might be modified in a future release).

### Table Structure
The table structure is faily simple.
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
aws dynamodb create-table --key-schema "AttributeName=id,KeyType=HASH" --attribute-definitions "AttributeName=id,AttributeType=S" --provisioned-throughput "ReadCapacityUnits=5,WriteCapacityUnits=5" --table-name flask_sessions
```

You can find table creation scripts in the `utils/dynamo` directory.

The `ttl` column is present to take advantage of DynamoDB's `Lifecycle` feature where dynamo will delete all rows with a ttl in the past.


## TODO
- Advanced serialization of session (IE: Pickling )
- Test coverage
- More laxed cookie refresh
