import os
import json

from flask import Flask

from cloudant import Cloudant

app = Flask(__name__)

app.config.from_object('eplatform.config.Config')


def connect_db():
    if 'VCAP_SERVICES' in os.environ:
        vcap = json.loads(os.getenv('VCAP_SERVICES'))
        print('Found VCAP_SERVICES')
    elif "LOCAL_ENV" in app.config:
        vcap = app.config["LOCAL_ENV"]
        print('Found local VCAP_SERVICES')
    if 'cloudantNoSQLDB' in vcap:
        creds = vcap['cloudantNoSQLDB'][0]['credentials']
        user = creds['username']
        password = creds['password']
        url = 'https://' + creds['host']
    db_name = "test"
    try:
        client = Cloudant(user, password, url=url, connect=True)
    except:
        print("Cloudant Error")
    try:
        db = client.create_database(db_name, throw_on_exists=False)
    except:
        print("Cloudant Error")
    return client, db

# DO NOT MOVE!
from eplatform.modules.main import main

app.register_blueprint(main)
