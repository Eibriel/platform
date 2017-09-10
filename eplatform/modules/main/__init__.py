import os

from flask import abort
from flask import request
from flask import jsonify
from flask import Response
from flask import Blueprint

from werkzeug.datastructures import Headers

from eplatform import app
from eplatform.modules.watson import watson

import json

main = Blueprint('main', __name__)

#/api/chatbot-name/telegram
#/api/chatbot-name/facebook
#/api/chatbot-name/kik
#/api/chatbot-name/web

#/monitor
#/monitor/chatbot-name

@main.route('/api/<chatbotname>/web', methods=['POST'])
def web(chatbotname):
    config = app.config["CHATBOTS"]
    if chatbotname not in config:
        abort(404)
    if request.form.get("question") == '':
        m = None
    else:
        m = request.form.get("question")

    wat = watson(config[chatbotname]["watson"]["username"],
                config[chatbotname]["watson"]["password"],
                config[chatbotname]["watson"]["workspace_id"])

    # Load context
    chat_id = request.form.get("chat_id")
    chatbot_log_path = os.path.join("log", chatbotname)
    if not os.path.isdir(chatbot_log_path):
        os.mkdir(chatbot_log_path)
    json_filename = os.path.join(chatbot_log_path, "{}.json".format(chat_id))

    if os.path.exists(json_filename):
        with open(json_filename) as data_file:
            try:
                log = json.load(data_file)
            except:
                pass
    else:
        log = []

    if len(log) > 0:
        response_context = log[-1]["context"]

    if m is None:
        watson_response = wat.send_to_watson ({})
    else:
        watson_response = wat.send_to_watson ({'text': m}, response_context)

    print (watson_response)

    log.append(watson_response)
    with open(json_filename, 'w') as data_file:
        json.dump(log, data_file, sort_keys=True, indent=4, separators=(',', ': '))

    message = {
        "message": watson_response["output"]["text"]
    }

    json_response = json.dumps(message)

    h = Headers()
    h.add("Access-Control-Allow-Origin", "*")

    #return jsonify(message, headers=h)
    #return Response("jsonCallback({});".format(json_response), mimetype='application/javascript', headers=h)
    return Response(json_response, mimetype='application/json', headers=h)
