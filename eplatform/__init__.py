from flask import Flask

app = Flask(__name__)

app.config.from_object('eplatform.config.Config')

from eplatform.modules.main import main
app.register_blueprint(main)
