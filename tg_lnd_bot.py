#!/usr/bin/env python3
# may need python3.8 for this to work


from json import JSONDecodeError
from time import sleep
import string
import time
import datetime

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
        print(params)
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

                    words = text.split()


                    if text.startswith("monitor") or text.startswith("check"):

                        # check if the command is valid
                        validcommand = True
                        
                        # if it is not 3 words then not valid
                        if len(words) != 3:
                            validcommand = False

                        # if second word not node or channel then not valid
                        elif words[1] not in ['node','channel']:
                            validcommand = False


                        # if second word node then check that third word is 66 characters hex
                        elif words[1] == 'node':
                            if len(words[2]) != 66:
                                if not all(c in string.hexdigits for c in words[2]):
                                    validcommand = False

                        # if the second word is channel then check that third word is a number
                        elif words[1] == 'channel':
                            if not words[2].isdigit():
                                validcommand = False
                        
                        if not validcommand:
                            reply = f"Invalid command: {text}"
                        else:

                            # at this point we should have a valid command

                            
                            check_type = words[1]
                            check_item = words[2]



                            # construct a check object
                            thischeck = memoryModule.checkType(check_type, check_item, chat_id)
                            thischeck.next_check_due = datetime.datetime.now() + datetime.timedelta(seconds=thischeck.check_interval)

                            # add this check to the memory
                            memory.add_check(thischeck)

                            reply = f"Adding {thischeck}"




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




    
