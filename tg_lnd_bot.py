#!/usr/bin/env python3
# may need python3.8 for this to work


from json import JSONDecodeError
from time import sleep
import time

import requests

import concurrent.futures

import memoryModule

import secrets


# telegram bot api class
class TelegramBot:
    def __init__ (self):
        self.token = secrets.TELEGRAM_BOT_TOKEN
        self.api_url = 'https://api.telegram.org/bot{}/'.format(self.token)
        self.session = requests.Session()
        self.offset = 0
        self.previous_offset = -1
        self.offset_filename = "telegram_update_offset.txt"
        # self.get_next_update()

    def get_next_update(self):
        if self.offset == 0:
            try:
                with open(self.offset_filename, 'r') as f:
                    self.offset = int(f.read()) - 1
            except FileNotFoundError:
                with open(self.offset_filename, 'w') as f:
                    f.write(str(self.offset))
        # timeout defaults to 30 and has max 50
        params = {'offset': self.offset + 1, 'limit': 1, 'timeout': 50}
        try:
            response = self.session.get(self.api_url + 'getUpdates', params = params)
        except:
            return None
        if response.status_code != 200:
            return None
        try:
            response_json = response.json()
        except JSONDecodeError:
            return None
        if 'result' not in response_json:
            return None
        if len(response_json['result']) == 0:
            return []
        if response_json['result'][0]['update_id'] != self.offset:
            self.offset = response_json['result'][0]['update_id']
            return response_json['result'][0]
        return None

    def save_offset(self):
        if self.offset != self.previous_offset:
            with open(self.offset_filename, 'w') as f:
                f.write(str(self.offset))
            self.previous_offset = self.offset

    def send_message(self, chat_id, text):
        params = {'chat_id': chat_id, 'text': text}
        response = self.session.post(self.api_url + 'sendMessage', params = params)
        return response.status_code == 200

# generator that returns spinner characters
def spinner_generator():
    while True:
        for c in ['|', '/', '-', '\\']:
            yield c

def check_channel(check):
    if check is None:
        return

    if check['check_type'] == 'node':
        pass
    elif check['check_type'] == 'channel':
        pass

    pass

# if this is __main__ 
if __name__ == "__main__":
    # create telegram bot object
    tgBot = TelegramBot()

    memory = memoryModule.memoryClass()

    executor = concurrent.futures.ThreadPoolExecutor(max_workers = 10)

    update_future = executor.submit(tgBot.get_next_update)

    spinner = spinner_generator()

    print("Bot started, press Ctrl+C to exit")
    try:    
        # loop continuously until keypress or break
        while True:
            # wait one second
            sleep(1)
            # print next spinner on the same line overlapping
            print(next(spinner), end = '\r')
            
            check_channel(next(memory.nextCheck()))
               
            # if there is an update
            if update_future.done():
                # get the update
                update = update_future.result()
                # if the update is a message
                if 'message' in update:
                    # get the message
                    chat_id = update['message']['chat']['id']
                    first_name = update['message']['from']['first_name']
                    try:
                        username = update['message']['from']['username']
                    except KeyError:
                        username = first_name
                    try:
                        text = update['message']['text'].lower()
                    except KeyError:
                        text = ""

                    # if the first character is not a '/' then ignore this
                    if text[0] != '/':
                        continue

                    # strip off the initial character
                    text = text[1:]


                    if text.startswith("monitor") or text.startswith("check"):
                        monitorcheck = words[1]

                        words = text.split()

                        if len(words) == 1:
                            tgBot.send_message(chat_id, f"Please specify a thing to {monitorcheck}")
                            continue

                        # second word must be "node" or "channel"
                        if (words[1] not in ["node", "channel"]) or (len(words) != 3):
                            tgBot.send_message(chat_id, f"Please specify a thing to {monitorcheck}, either node or channel followed by their id")
                            continue

                        # check that the third word is a reasonable id

                        # construct a check object
                        thischeck = memoryModule.checkType()



                    elif text == 'start':
                        reply = 'Hello {}(@{})! I am a lightning network monitor bot. Say /help for help'.format(first_name,username)
                    elif text == 'help':
                        reply = '''Ask me to /monitor [node|channel] <id>. I will monitor the node or channel with the id you specify and let you know if it is down.
                                    You can also ask me to /check <node|channel> <id> to see the current status.'''
                    else:
                        reply = 'I do not understand you.'
                    tgBot.send_message(chat_id, reply)
                tgBot.save_offset()
                update_future = executor.submit(tgBot.get_next_update)
    # keyboard break exception
    except KeyboardInterrupt:
        print("\nKeyboard break")        


    # save memory
    memory.save_memory()
    executor.shutdown(wait = False)

print('done')




    
