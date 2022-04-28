#!/usr/bin/env python3

# An empty telegram bot as a template
#
# long polling with concurrent.futures so it isn't blocking


from json import JSONDecodeError
from time import sleep
import time

import requests

import concurrent.futures

import alarm_memory

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

# if this is __main__ 
if __name__ == "__main__":
    # create telegram bot object
    bot = TelegramBot()

    memory = alarm_memory.AlarmMemory()

    executor = concurrent.futures.ThreadPoolExecutor(max_workers = 10)

    future_update = executor.submit(bot.get_next_update)

    print("Bot started, press Ctrl+C to exit")
    try:    
        # loop continuously until keypress or break
        while True:
            # wait one second
            sleep(1)
            print(". ", end = "", flush=True)

            # current time as epoch time
            current_time = int(round(time.time()))
            # load all the timers from memory
            due_alarms = memory.due_alarms(current_time)
            for timer in due_alarms:
                # send a message to the user
                for user_id in timer['user_ids']:
                    bot.send_message(user_id, "Your alarm is due!")
                # bot.send_message(timer['user_id'], "Your alarm is due")
                # delete the timer from memory
                memory.delete_alarm_by_time(current_time)
               
            # if there is an update
            if future_update.done():
                # get the update
                update = future_update.result()
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
                        text = update['message']['text']
                    except KeyError:
                        text = ""
                    if text == "/set3minutetimer":
                        text = "set 3 minute timer"
                    if text.lower().startswith("set") or text.lower().startswith("start"):
                        # natural language process to get the duration from the text
                        # parse the text, find the number
                        # split the lower case text into words using spaces or dashes
                        
                        words = text.lower().replace("-"," ").split()

                        # find how many words are numbers
                        count_of_numbers = 0
                        number_offset = 0
                        for i in range (len(words)):
                            word = words[i]
                            # if the word is a valid number
                            if word.isdigit():
                                count_of_numbers += 1
                                number_offset = i
                        
                        
                        # if there is only one number, use it as the duration
                        if count_of_numbers == 1:
                            duration = int(words[number_offset])
                        else:
                            duration = 0
                            text = '/help'

                        possible_units = ['second', 'seconds', 'minute', 'minutes', 'hour', 'hours', 'day', 'days']
                        unit_multipiers = [1,1,60,60,3600,3600,86400,86400]
                        # find the unit

                        # convert to seconds
                        for i in range (len(words)):
                            word = words[i]
                            if word in possible_units:
                                duration = duration * unit_multipiers[possible_units.index(word)] 
                                break

                        text = "/timer " + str(duration)
                        
                        
                    if text == '/start':
                        reply = 'Hello {}(@{})! I am a timer bot. Ask me to /timer <seconds> to set a timer'.format(first_name,username)
                    if text == '/help':
                        reply = 'Ask me to /timer <seconds> to set a timer. I also understand things like "start a 5 minute timer" or "set a 5 hour timer" or "set a timer for 5 days for me"'
                    # if text starts with /timer
                    elif text.startswith('/timer'):
                        # get the number of seconds
                        words = text.split(' ')
                        if len(words) > 1:
                            seconds = words[1]
                        
                            # if the number is a number
                            if seconds.isdigit():
                                # calculate the end time and remember it
                                # current time as epoch time
                                current_time = int(round(time.time()))
                                end_time = current_time + int(seconds)
                                memory.add_alarm(chat_id, end_time)
                                # calculate the full date time string for the end time
                                end_time_string = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(end_time))
                                reply = f'Timer set for {seconds} seconds from now at {end_time_string}'
                            else:
                                reply = 'Please enter a number of seconds'
                        else:
                            reply = 'Please enter a number of seconds'
                    else:
                        reply = 'I do not understand you.'
                    bot.send_message(chat_id, reply)
                bot.save_offset()
                future_update = executor.submit(bot.get_next_update)
    # keyboard break exception
    except KeyboardInterrupt:
        print("\nKeyboard break")        


    # save memory
    memory.save_memory()
    executor.shutdown(wait = False)

print('done')




    
