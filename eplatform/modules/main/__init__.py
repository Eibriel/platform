import os
import re
import requests

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


def callSendAPI(messageData, chatbotname):
    headers = {'user-agent': 'rDany', 'Content-Type': 'application/json'}
    page_access_token = app.config["CHATBOTS"][chatbotname]["facebook"]["PAGE_ACCESS_TOKEN"]
    r = None
    while 1:
        try:
            r = requests.post('https://graph.facebook.com/v2.6/me/messages?access_token={}'.format(page_access_token), data=json.dumps(messageData), headers=headers)
            break
        except requests.exceptions.ConnectionError:
            raise
            if retry:
                print ("Facebook: ConnectionError")
            else:
                break
        except requests.exceptions.Timeout:
            raise
            if retry:
                print ("Facebook: Timeout")
            else:
                break
        time.sleep(5)
    return r


def facebookSendTextMessage(recipientId, messageText, chatbotname):
    messageData = {
        'recipient': {
          'id': recipientId
        },
        'message': {
          'text': messageText
        }
      }
    callSendAPI(messageData, chatbotname)


def facebookSendImageMessage(recipientId, imageURL, chatbotname):
    messageData = {
        'recipient': {
            'id': recipientId
        },
        'message': {
            'attachment':{
                'type':'image',
                'payload':{
                    'url': imageURL
                }
            }
        }
    }
    callSendAPI(messageData, chatbotname)


def facebookReceivedMessage(message):
    senderID = message['sender']['id']
    recipientID = message['recipient']['id']
    timeOfMessage = message['timestamp']
    message_ = message['message']
    messageID = message_['mid']
    messageText = message_.get('text')
    messageAttachments = message_.get('attachments')
    facebookSendTextMessage(recipientID, )


def facebookConfigureBot(chatbotname):
    configData = {
        'get_started': 'payload'
    }
    callSendAPI(configData, chatbotname)


def get_watson_response(wat, chatbotname, chat_id, m):
    with open("log/Output.txt", "w") as text_file:
        text_file.write(str(m))
    # Load context
    chatbot_log_path = os.path.join("log", chatbotname)
    if not os.path.isdir(chatbot_log_path):
        os.mkdir(chatbot_log_path)
    json_filename = os.path.join(chatbot_log_path, "{}.json".format(chat_id))

    log = []
    if os.path.exists(json_filename):
        with open(json_filename) as data_file:
            try:
                log = json.load(data_file)
            except:
                pass

    response_context = None
    if len(log) > 0:
        response_context = log[-1]["context"]

    if m is None:
        watson_response = wat.send_to_watson ({})
    else:
        if response_context == None:
            watson_response = wat.send_to_watson ({})
            response_context = watson_response["context"]
        watson_response = wat.send_to_watson ({'text': m}, response_context)

    #print (watson_response)

    log.append(watson_response)
    with open(json_filename, 'w') as data_file:
        json.dump(log, data_file, sort_keys=True, indent=4, separators=(',', ': '))
    return watson_response


@main.route('/api/<chatbotname>/<messenger>', methods=['GET', 'POST'])
def web(chatbotname, messenger):
    # Messenger web - facebook - telegram - kik
    if request.method == 'GET' and messenger != 'facebook':
        abort(404)

    config = app.config["CHATBOTS"]
    if chatbotname not in config:
        abort(404)

    # Facebook Challenge
    if request.method == 'GET' and messenger == 'facebook':
        hub_mode = request.args.get('hub.mode', '')
        hub_verify_token = request.args.get('hub.verify_token', '')
        hub_challenge = request.args.get('hub.challenge', '')
        if hub_mode == 'subscribe' and hub_verify_token == config[chatbotname]["facebook"]["HUB_VERIFY_TOKEN"]:
            return hub_challenge
        else:
            abort(403)
    #

    wat = watson(config[chatbotname]["watson"]["username"],
                config[chatbotname]["watson"]["password"],
                config[chatbotname]["watson"]["workspace_id"])

    if messenger == 'web':
        if request.form.get("question") == '':
            m = None
        else:
            m = request.form.get("question")

        chat_id = request.form.get("chat_id")

        watson_response = get_watson_response (wat, chatbotname, chat_id, m)

        message = {
            "message": watson_response["output"]["text"]
        }

        json_response = json.dumps(message)

        h = Headers()
        h.add("Access-Control-Allow-Origin", "*")

        return Response(json_response, mimetype='application/json', headers=h)
    elif messenger == 'facebook':
        if request.method == 'POST':
            msg = request.json
            if msg['object'] == 'page':
                for entries in msg['entry']:
                    for message in entries['messaging']:
                        needs_answer = False
                        if "message" in message:
                            senderId = message['sender']['id']
                            m = message["message"]["text"]
                            needs_answer = True
                        elif "postback" in message:
                            senderId = message['sender']['id']
                            m = None
                            needs_answer = True
                        if needs_answer:
                            if m == '/start':
                                m = None
                            if m == '/configure':
                               facebookConfigureBot(chatbotname) 
                            watson_response = get_watson_response (wat, chatbotname, senderId, m)
                            recipientId = senderId
                            for watson_message in watson_response["output"]["text"]:
                                if watson_message.startswith("!["):
                                    get_url = re.search(r"\!\[.*\]\((?P<url>.+?)\)", watson_message)
                                    if get_url:
                                        facebookSendImageMessage(recipientId, get_url.group('url'), chatbotname)
                                else:
                                    facebookSendTextMessage(recipientId, markdown_facebook(watson_message), chatbotname)
        return jsonify({})
    elif messenger == 'telegram':
        msg = request.json
        if "message" not in msg:
            return jsonify({})
        answer = {
                'method': "sendMessage",
                'chat_id': msg["message"]["chat"]["id"],
                'text': "*Hi there!*",
                'parse_mode': 'Markdown',
                'disable_web_page_preview': True
        }
        if msg["message"]["text"] == '/start':
            msg["message"]["text"] = None
        watson_response = get_watson_response (wat, chatbotname, msg["message"]["chat"]["id"], msg["message"]["text"])

        answer["text"] = markdown_telegram("\n\n".join(watson_response["output"]["text"]))
        return jsonify(answer)

def markdown_telegram(text):
    text = text.replace('<em>', '_')
    text = text.replace('</em>', '_')
    text = text.replace('<strong>', '*')
    text = text.replace('</strong>', '*')
    return text

def markdown_facebook(text):
    text = text.replace('<em>', '')
    text = text.replace('</em>', '')
    text = text.replace('<strong>', '')
    text = text.replace('</strong>', '')

    reg = r"\[(?P<alt>.*?)\]\((?P<url>.+?)\)(?P<target>\^*)"
    get_url = re.search(reg, text)
    while get_url:
        alt = get_url.group('alt')
        url = get_url.group('url')
        target = get_url.group('target')
        text = text.replace('[{}]({}){}'.format(alt, url, target), '{} ({})'.format(alt, url))
        get_url = re.search(reg, text)

    return text
