import os
import re
import json
import hashlib
import requests

from flask import g
from flask import abort
from flask import request
from flask import jsonify
from flask import Response
from flask import Blueprint

from werkzeug.datastructures import Headers

from eplatform import app
from eplatform import connect_db
from eplatform.modules.watson import watson


main = Blueprint('main', __name__)

# /api/chatbot-name/telegram
# /api/chatbot-name/facebook
# /api/chatbot-name/kik
# /api/chatbot-name/web

# /monitor
# /monitor/chatbot-name


def get_db():
    """Opens a new database connection if there is none yet for the
    current application context.
    """
    if not hasattr(g, 'cloudant_db'):
        g.cloudant_client, g.cloudant_db = connect_db()
    return g.cloudant_db


@app.teardown_appcontext
def close_db(error):
    """Closes the database again at the end of the request."""
    if hasattr(g, 'cloudant_db'):
        g.cloudant_client.disconnect()


def callSendAPI(messageData, chatbotname, endpoint="messages"):
    with open("log/Output.txt", "a") as text_file:
        text_file.write("\n\n")
        text_file.write(str(messageData))
    headers = {'user-agent': 'Eibriel Platform',
               'Content-Type': 'application/json'}
    page_access_token = app.config["CHATBOTS"][chatbotname]["facebook"]["PAGE_ACCESS_TOKEN"]
    page_id = app.config["CHATBOTS"][chatbotname]["facebook"]["PAGE_ID"]
    r = None
    while 1:
        try:
            r = requests.post('https://graph.facebook.com/v2.10/{}/{}?access_token={}'.format(page_id, endpoint, page_access_token), data=json.dumps(messageData), headers=headers)
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


def facebookSendImageMessage(recipientId, payload, chatbotname):
    messageData = {
        'recipient': {
            'id': recipientId
        },
        'message': {
            'attachment': {
                'type': 'image',
                'payload': payload
            }
        }
    }
    r = callSendAPI(messageData, chatbotname)
    return r


def facebookSendAudioMessage(recipientId, payload, chatbotname):
    messageData = {
        'recipient': {
            'id': recipientId
        },
        'message': {
            'attachment': {
                'type': 'audio',
                'payload': payload
            }
        }
    }
    r = callSendAPI(messageData, chatbotname)
    return r


def facebookSendFile(recipientId, fileURL, file_type, chatbotname):
    # {'error': {'error_subcode': 2018008, 'type': 'OAuthException', 'fbtrace_id': 'DCzz4oZiIj6', 'message': '(#100) Failed to fetch the file from the url', 'code': 100}}
    cache_path = file_url_to_chache_path("facebook",
                                         file_type,
                                         fileURL,
                                         recipientId)
    cache_data = get_cache(cache_path)
    r = None
    payload = {}
    if cache_data:
        payload["attachment_id"] = cache_data["file_id"]
    else:
        payload["url"] = fileURL
        payload["is_reusable"] = True
    if file_type == "audio":
        r = facebookSendAudioMessage(recipientId, payload, chatbotname)
    elif file_type == "image":
        r = facebookSendImageMessage(recipientId, payload, chatbotname)
    if r is not None:
        set_cache(cache_path, "facebook", file_type, fileURL, r)


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
        'get_started': {
            'payload': 'Get Started'
        },
        "greeting": [
            {
                "locale": "default",
                "text": "Eibriel presenta..."
            }, {
                "locale": "es_LA",
                "text": "Eibriel presenta..."
            }
        ]
    }
    callSendAPI(configData, chatbotname, endpoint="messenger_profile")


def telegramCallSendAPI(access_point, chatbotname, data=None):
    with open("log/OutputTelegram.txt", "a") as text_file:
        text_file.write("\n\n")
        text_file.write(str(data))
    headers = {'user-agent': "Eibriel platform"}
    token = app.config["CHATBOTS"][chatbotname]["telegram"]["token"]
    try:
        r = requests.get('https://api.telegram.org/bot{0}/{1}'.format(token, access_point), data=data, timeout=40, headers=headers)
    except requests.exceptions.ConnectionError:
        return None
    except requests.exceptions.Timeout:
        return None
    with open("log/OutputTelegram.txt", "a") as text_file:
        text_file.write("\n\n")
        text_file.write(r.text)
    return r


def telegramSendTextMessage(chat_id, answer, chatbotname):
    msg = {
        'chat_id': chat_id,
        'parse_mode': 'Markdown',
        'text': answer,
    }
    telegramCallSendAPI('sendMessage', chatbotname, data=msg)


def telegramSendAudioMessage(chat_id, audio_url, chatbotname):
    msg = {
        'chat_id': chat_id,
        'audio': audio_url,
    }
    r = telegramCallSendAPI('sendAudio', chatbotname, data=msg)
    return r


def telegramSendDocumentMessage(chat_id, document_url, chatbotname):
    msg = {
        'chat_id': chat_id,
        'document': document_url,
    }
    r = telegramCallSendAPI('sendDocument', chatbotname, data=msg)
    return r


def telegramSendImageMessage(chat_id, image_url, chatbotname):
    msg = {
        'chat_id': chat_id,
        'photo': image_url,
    }
    r = telegramCallSendAPI('sendPhoto', chatbotname, data=msg)
    return r


def telegramSendVideoMessage(chat_id, video_url, chatbotname):
    msg = {
        'chat_id': chat_id,
        'video': video_url,
    }
    r = telegramCallSendAPI('sendVideo', chatbotname, data=msg)
    return r


def telegramSendVoiceMessage(chat_id, voice_url, chatbotname):
    msg = {
        'chat_id': chat_id,
        'voice': voice_url,
    }
    r = telegramCallSendAPI('sendVoice', chatbotname, data=msg)
    return r


def telegramSendFile(chat_id, file_url, file_type, chatbotname):
    cache_path = file_url_to_chache_path("telegram", file_type, file_url)
    cache_data = get_cache(cache_path)
    if cache_data:
        file_url = cache_data["file_id"]
        file_type = cache_data["file_type"]
    r = None
    if file_type == "audio":
        r = telegramSendAudioMessage(chat_id, file_url, chatbotname)
    elif file_type == "image":
        r = telegramSendImageMessage(chat_id, file_url, chatbotname)
    elif file_type == "document":
        r = telegramSendDocumentMessage(chat_id, file_url, chatbotname)
    elif file_type == "video":
        r = telegramSendVideoMessage(chat_id, file_url, chatbotname)
    elif file_type == "voice":
        r = telegramSendVoiceMessage(chat_id, file_url, chatbotname)
    if r is not None and not cache_data:
        set_ok = set_cache(cache_path, "telegram", file_type, file_url, r)
    # if cache_data and not set_ok:
    #    clear_cache(cache_path)
    #    telegramSendAudioMessage(chat_id, audio_url, chatbotname)


def get_watson_response(wat, platform, chatbotname, chat_id, m):
    # Load context
    db = get_db()
    try:
        log = db[str(chat_id)]
        create_log = False
    except KeyError:
        log = {'_id': str(chat_id), "watson_responses": []}
        create_log = True

    response_context = None
    if len(log["watson_responses"]) > 0:
        if log["watson_responses"][-1] is not None:
            response_context = log["watson_responses"][-1]["context"]

    watson_responses = []
    if m is None:
        try:
            watson_response = wat.send_to_watson({})
        except:
            print("Watson Error")
            raise
            abort(500)
        watson_responses.append(watson_response)
    elif len(log) == 0:
        try:
            watson_response = wat.send_to_watson({})
        except:
            print("Watson Error")
            raise
            abort(500)
        watson_responses.append(watson_response)
    else:
        if response_context is None:
            try:
                watson_response = wat.send_to_watson({})
            except:
                print("Watson Error")
                raise
                abort(500)
            watson_responses.append(watson_response)
            response_context = watson_responses[-1]["context"]
        else:
            response_context["platform"] = platform
            response_context["timezone"] = "America/Argentina/Buenos_Aires"
            try:
                watson_response = wat.send_to_watson({'text': m},
                                                     response_context)
                watson_responses.append(watson_response)
            except:
                print("Watson Error")
                raise
                abort(500)

    # print(watson_response)

    log["watson_responses"] = log["watson_responses"] + watson_responses

    if create_log:
        db.create_document(log)
    else:
        log.save()
    return watson_responses


@main.route('/api/<chatbotname>/<messenger>', methods=['GET', 'POST'])
def web(chatbotname, messenger):
    platform = messenger
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

        messages = []
        watson_responses = get_watson_response(wat,
                                               platform,
                                               chatbotname,
                                               chat_id,
                                               m)
        for watson_response in watson_responses:
            messages = messages + watson_response["output"]["text"]

        for k in range(0, len(messages)):
            messages[k] = get_external_data(messages[k])

        message = {
            "message": messages
        }

        json_response = json.dumps(message)

        h = Headers()
        h.add("Access-Control-Allow-Origin", "*")

        return Response(json_response, mimetype='application/json', headers=h)
    elif messenger == 'facebook':
        if request.method == 'POST':
            msg = request.json
            with open("log/Output.txt", "a") as text_file:
                text_file.write("\n\n")
                text_file.write(str(msg))
            if msg['object'] == 'page':
                for entries in msg['entry']:
                    for message in entries['messaging']:
                        needs_answer = False
                        if "message" in message:
                            senderId = message['sender']['id']
                            if "text" in message["message"]:
                                m = message["message"]["text"]
                                needs_answer = True
                            elif "sticker_id" in message["message"]:
                                m = "sticker_id {}".format(message["message"]["sticker_id"])
                                needs_answer = True
                        elif "read" in message:
                            senderId = message['sender']['id']
                            m = "[read]"
                            #needs_answer = True
                        elif "postback" in message:
                            if message["postback"].get("payload") == "Get Started":
                                senderId = message['sender']['id']
                                m = None
                                needs_answer = True
                        if needs_answer:
                            if m == '/start':
                                m = None
                            if m == '/configure':
                               facebookConfigureBot(chatbotname)
                            watson_responses = get_watson_response (wat, platform, chatbotname, senderId, m)
                            recipientId = senderId
                            for watson_response in watson_responses:
                                for watson_message in watson_response["output"]["text"]:
                                    img_url = extract_image(watson_message)
                                    voice_url = extract_voice(watson_message)
                                    audio_url = extract_audio(watson_message)
                                    if img_url:
                                        facebookSendFile(recipientId, img_url, 'image', chatbotname)
                                    elif voice_url:
                                        facebookSendFile(recipientId, voice_url, 'voice', chatbotname)
                                    elif audio_url:
                                        facebookSendFile(recipientId, audio_url, 'audio', chatbotname)
                                    else:
                                        watson_message = get_external_data(watson_message)
                                        facebookSendTextMessage(recipientId, markdown_facebook(watson_message), chatbotname)
        return jsonify({})
    elif messenger == 'telegram':
        msg = request.json
        with open("log/OutputTelegram.txt", "a") as text_file:
            text_file.write("\n\n")
            text_file.write(str(msg))
        if "message" not in msg:
            return jsonify({})
        if "text" not in msg["message"] and "voice" not in msg["message"]:
            return jsonify({})

        answer = {
                'method': "sendMessage",
                'chat_id': msg["message"]["chat"]["id"],
                'text': "*Hi there!*",
                'parse_mode': 'Markdown',
                'disable_web_page_preview': True
        }

        if "voice" in msg["message"]:
            file_id = msg["message"]["voice"]["file_id"]
            mime_type = msg["message"]["voice"]["mime_type"]
            duration = msg["message"]["voice"]["duration"]
            if duration > 15:
                answer["text"] = "Audio muy largo. Duración máxima 15 segundos"
                return jsonify(answer)
            fileData = {
                "file_id": file_id
            }
            fileJson = telegramCallSendAPI('getFile',
                                           chatbotname,
                                           data=fileData)
            try:
                fileJson = fileJson.json()
            except:
                return jsonify({})
            with open("log/OutputTelegram.txt", "a") as text_file:
                text_file.write("\n\n")
                text_file.write(str(fileJson))
            if "result" in fileJson and "file_path" in fileJson["result"]:
                file_path = fileJson["result"]["file_path"]
                answer["text"] = file_path
                token = app.config["CHATBOTS"][chatbotname]["telegram"]["token"]
                url = "https://api.telegram.org/file/bot{}/{}".format(token, file_path)
                #r = requests.get(url)
                local_filename = "voice/{}".format(file_id)
                r = requests.get(url, stream=True)
                with open(local_filename, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=1024):
                        if chunk: # filter out keep-alive new chunks
                            f.write(chunk)
                            #f.flush() commented by recommendation from J.F.Sebastian
                username = app.config["CHATBOTS"][chatbotname]["watson-stt"]["username"]
                password = app.config["CHATBOTS"][chatbotname]["watson-stt"]["password"]
                api_url = "https://stream.watsonplatform.net/speech-to-text/api"
                if 'VCAP_SERVICES' in os.environ:
                    vcap = json.loads(os.getenv('VCAP_SERVICES'))
                    print('Found VCAP_SERVICES')
                    if 'speech_to_text' in vcap:
                        creds = vcap['speech_to_text'][0]['credentials']
                        username = creds['username']
                        password = creds['password']
                        api_url = creds['url']
                headers = {
                    'Content-Type': mime_type,
                    #'Transfer-Encoding': 'chunked'
                }
                url = "{}/v1/recognize?model=es-ES_BroadbandModel".format(api_url)
                files = {'upload_file': open(local_filename,'rb')}
                r = requests.post(url, headers=headers, files=files, auth=(username, password))
                try:
                    sttJson = r.json()
                except:
                    return jsonify({})
                with open("log/OutputTelegram.txt", "a") as text_file:
                    text_file.write("\n\n")
                    text_file.write(str(sttJson))
                if "results" not in sttJson:
                    answer["text"] = str(sttJson)
                    return jsonify(answer)
                if len(sttJson["results"]) == 0:
                    answer["text"] = "Error procesando audio"
                    return jsonify(answer)
                transcript = sttJson["results"][0]["alternatives"][0]["transcript"]
                msg["message"]["text"] = transcript
                # return jsonify(answer)
        # return jsonify({})

        if msg["message"]["text"] == '/start':
            msg["message"]["text"] = None
        chat_id = msg["message"]["chat"]["id"]
        watson_responses = get_watson_response(wat,
                                               platform,
                                               chatbotname,
                                               chat_id,
                                               msg["message"]["text"])
        messages = []
        for watson_response in watson_responses:
            messages = messages + watson_response["output"]["text"]
            for message in messages:
                img_url = extract_image(message)
                voice_url = extract_voice(message)
                audio_url = extract_audio(message)
                if img_url:
                    if img_url.endswith("giphy.gif"):
                        telegramSendFile(chat_id, img_url, "video", chatbotname)
                    else:
                        telegramSendFile(chat_id, img_url, "image", chatbotname)
                elif voice_url:
                    telegramSendFile(chat_id, voice_url, "voice", chatbotname)
                elif audio_url:
                    telegramSendFile(chat_id, audio_url, "audio", chatbotname)
                else:
                    message = get_external_data(message)
                    telegramSendTextMessage(chat_id, markdown_telegram(message), chatbotname)
        # answer["text"] = markdown_telegram("\n\n".join(messages))
        # return jsonify(answer)
        return jsonify({})


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
        text = text.replace('[{}]({}){}'.format(alt, url, target),
                            '{} ({})'.format(alt, url))
        get_url = re.search(reg, text)
    return text


def extract_image(message):
    if message.startswith("!["):
        get_url = re.search(r"\!\[.*\]\((?P<url>.+?)\)", message)
        if get_url:
            return get_url.group('url')
    return False


def extract_voice(message):
    if message.startswith("¡["):
        get_url = re.search(r"\¡\[.*\]\((?P<url>.+?)\)", message)
        if get_url:
            return get_url.group('url')
    return False


def extract_audio(message):
    if message.startswith("+["):
        get_url = re.search(r"\+\[.*\]\((?P<url>.+?)\)", message)
        if get_url:
            return get_url.group('url')
    return False


def get_external_data(watson_message):
    if watson_message.startswith("[subway_status]"):
        last_letter = watson_message[-1]
        subway_status = get_subway_status()
        watson_message = None
        for line in subway_status:
            if watson_message is not None:
                watson_message = "{}\n".format(watson_message)
            else:
                watson_message = ""
            if last_letter == ']' or line[0] == last_letter:
                if last_letter == ']':
                    watson_message = "{}<strong>{}</strong>: {}".format(watson_message, line[0], line[1])
                else:
                    if line[1] == 'Normal':
                        watson_message = "La línea <strong>{}</strong> parece funcionar correctamente, el estado de la situación es {}".format(line[0], line[1])
                    else:
                        watson_message = "La línea <strong>{}</strong> tiene problemas lamentablemente. {}".format(line[0], line[1])
    if watson_message.startswith("[weather]"):
        watson_message = get_weather(watson_message[9:])
    return watson_message

def get_weather(info="general"):
    headers = {'user-agent': "Eibriel platform"}
    #token = app.config["CHATBOTS"][chatbotname]["telegram"]["token"]
    if info in ["general", "rain_now", "temp", "hum"]:
        url = 'http://api.openweathermap.org/data/2.5/weather?id=3435259&units=metric&appid=36df7696a407fa7ff3b95e94be4bbe3f'
    elif info in ["rain_future", "future"]:
        url = 'http://api.openweathermap.org/data/2.5/forecast?id=3435259&units=metric&appid=36df7696a407fa7ff3b95e94be4bbe3f'
    try:
        r = requests.get(url, timeout=40, headers=headers)
    except requests.exceptions.ConnectionError:
        return "Error"
    except requests.exceptions.Timeout:
        return "Error"
    try:
        r_json = r.json()
    except:
        return "Error"
    if info=="rain_now":
        return "Ahora mismo ..."
    elif info=="rain_future":
        return "Quizás llueva o quizás no ..."
    elif info=="future":
        return "El clima será ..."
    elif info=="temp":
        return "En Plaza de Mayo hace {}º".format(r_json["main"]["temp"])
    elif info=="hum":
        return "En Plaza de Mayo hay una humedad del {}% ".format(r_json["main"]["humidity"])
    else:
        return "En Plaza de Mayo hace {}º, con una humedad del {}% ".format(r_json["main"]["temp"], r_json["main"]["humidity"])


def get_subway_status():
    headers = {'user-agent': "Eibriel platform"}
    #token = app.config["CHATBOTS"][chatbotname]["telegram"]["token"]
    try:
        r = requests.get('http://www.metrovias.com.ar/', timeout=40, headers=headers)
    except requests.exceptions.ConnectionError:
        return None
    except requests.exceptions.Timeout:
        return None
    #return r
    #lines = ["A", "B", "C", "D", "E", "H", "P", "U"]
    statuses = [
        ["A", None],
        ["B", None],
        ["C", None],
        ["D", None],
        ["E", None],
        ["H", None],
        ["P", None],
        ["U", None]
    ]
    for line in statuses:
        get_status = re.search(r"status-line-{}\">(?P<status>.+)<\/span>".format(line[0]), r.text)
        if get_status:
            line[1] = get_status.group("status")
    return statuses


def file_url_to_chache_path(platform, file_type, file_url, chat_id = ""):
    hash = hashlib.md5("{} {} {}{}".format(platform, file_type, file_url, chat_id).encode("UTF-8")).hexdigest()
    return os.path.join("cache", hash)


def clear_cache(cache_path):
    if os.path.exists(cache_path):
        os.remove(cache_path)


def get_cache(cache_path):
    cache_data = None
    if os.path.exists(cache_path):
        with open(cache_path) as data_file:
            try:
                cache_data = json.load(data_file)
            except:
                pass
    return cache_data


def set_cache(cache_path, platform, file_type, file_url, r):
    try:
        r_json = r.json()
    except:
        return False
    if platform == "telegram":
        with open("log/OutputTelegram.txt", "a") as text_file:
            text_file.write("\n\n")
            text_file.write(str(r_json))
        if not r_json["ok"]:
            # {'error_code': 400, 'description': 'Bad Request: wrong persistent file_id specified: Wrong padding in the string', 'ok': False}
            # {"ok":false,"error_code":400,"description":"Bad Request: wrong file identifier/HTTP URL specified"}
            return False
        if "photo" in r_json["result"]:
            file_id = r_json["result"]["photo"][0]["file_id"]
            final_file_type = "image"
        if "audio" in r_json["result"]:
            file_id = r_json["result"]["audio"]["file_id"]
            final_file_type = "audio"
        if "voice" in r_json["result"]:
            file_id = r_json["result"]["voice"]["file_id"]
            final_file_type = "voice"
        if "video" in r_json["result"]:
            file_id = r_json["result"]["video"]["file_id"]
            final_file_type = "video"
        if "document" in r_json["result"]:
            file_id = r_json["result"]["document"]["file_id"]
            final_file_type = "document"
        # if file_type != final_file_type:
        #    return False
    if platform == "facebook":
        with open("log/Output.txt", "a") as text_file:
            text_file.write("\n\n")
            text_file.write(str(r_json))
        if "attachment_id" not in r_json:
            return False
        if file_type == "audio":
            file_id = r_json["attachment_id"]
        if file_type == "image":
            file_id = r_json["attachment_id"]
        final_file_type = file_type

    cache_data = {
        "file_url": file_url,
        "file_id": file_id,
        "file_type": final_file_type
    }
    with open(cache_path, 'w') as data_file:
        json.dump(cache_data,
                  data_file,
                  sort_keys=True,
                  indent=4,
                  separators=(',', ': '))
    return True
