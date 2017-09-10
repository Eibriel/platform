from watson_developer_cloud import ConversationV1

class watson:
    def __init__(self, username, password, workspace_id):
        self.conversation = ConversationV1(
            username=username,
            password=password,
            version='2017-04-21')

        # replace with your own workspace_id
        self.workspace_id = workspace_id

    def send_to_watson (self, message_input, response_context=None):
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
                                message_input=message_input, context=response_context)
            except:
                print ("Error, retrying")
                done = False
            count += 1
        return response

#response = send_to_watson ({'text': input_text}, response_context)
