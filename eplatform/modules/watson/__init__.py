import os
import json

from watson_developer_cloud import ConversationV1


class watson:
    def __init__(self, username, password, workspace_id):
        if 'VCAP_SERVICES' in os.environ:
            vcap = json.loads(os.getenv('VCAP_SERVICES'))
            print('Found VCAP_SERVICES')
            if 'conversation' in vcap:
                creds = vcap['conversation'][0]['credentials']
                username = creds['username']
                password = creds['password']
                url = creds['url']
        try:
            self.conversation = ConversationV1(
                username=username,
                password=password,
                version='2017-04-21')
        except:
            print ("Error Watson Conversation")
            raise

        # replace with your own workspace_id
        self.workspace_id = workspace_id

    def send_to_watson(self, message_input, response_context=None):
        response = None
        count = 0
        done = False
        while not done and count < 10:
            done = True
            try:
                if response_context is None:
                    response = self.conversation.message(workspace_id=self.workspace_id,
                                                         message_input=message_input)
                else:
                    response = self.conversation.message(workspace_id=self.workspace_id,
                                                         message_input=message_input,
                                                         context=response_context)
            except:
                print("Error, retrying")
                done = False
                raise
            count += 1
        return response

# response = send_to_watson ({'text': input_text}, response_context)
