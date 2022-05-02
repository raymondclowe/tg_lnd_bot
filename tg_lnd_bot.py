#!/usr/bin/env python3
# may need python3.8 for this to work


import concurrent.futures
import datetime
import string
from json import JSONDecodeError
from time import sleep

import config
import memoryModule
import telegrambotapi

# generator that returns spinner characters


def spinner_generator():
    while True:
        for c in ['|', '/', '-', '\\']:
            yield c


def check(thischeck):
    if thischeck is None:
        return thischeck # unchanged

    if check['check_type'] == 'node':
        return "result of checking node" 
    elif check['check_type'] == 'channel':
        return "result of checking channel" # 
        

    pass


# if this is __main__
if __name__ == "__main__":
    # create telegram bot object
    tgBot = telegrambotapi.TelegramBot()

    memory = memoryModule.memoryClass()

    executor = concurrent.futures.ThreadPoolExecutor(max_workers=10)

    update_future = executor.submit(tgBot.get_next_update)

    spinner = spinner_generator()

    print("Bot started, press Ctrl+C to exit")
    try:
        # loop continuously until keypress or break
        while True:
            # wait one second
            sleep(1)
            # print next spinner on the same line overlapping
            print(next(spinner), end='\r')

            # check_channel(next(memory.nextCheck()))

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

                    if words[0] in ['monitor', 'check']:
    
                        # check if the command is valid
                        validcommand = True

                        # if it is not 3 words then not valid
                        if len(words) != 3:
                            validcommand = False

                        # if second word not node or channel then not valid
                        elif words[1] not in ['node', 'channel']:
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

                            # at this point we should have a valid command so we can process it

                            command_type = words[0]
                            check_type = words[1]
                            check_item = words[2]

                            # construct a check object which is a dictionary

                            thischeck = {'check_type': check_type, 
                                         'check_item': check_item,
                                         'chat_id': chat_id,
                                         'next_check_due': datetime.datetime.now() + datetime.timedelta(seconds=config.DEFAULT_CHECK_INTERVAL_SECONDS)}

                            # if this is for command monitor then add it to the memory otherwise check it now
                            if command_type == 'monitor':
                                memory.addCheck(thischeck)
                                reply = f"Adding {thischeck}"
                            else:
                                thischeck, reply = check(thischeck)
                                memory.updateCheck(thischeck)
                            
                             

                    elif text == 'start':
                        reply = f'Hello {first_name}(@{username})! I am a lightning network monitor bot. Say /help for help'
                    elif text == 'help':
                        reply = 'Ask me to /monitor [node|channel] <id>. I will monitor the node or channel with the id you specify and let you know if it is down. ' + \
                                'You can also ask me to /check <node|channel> <id> to see the current status.'
                    else:
                        reply = 'I do not understand you. Try /help for help.'
                    tgBot.send_message(chat_id, reply)
                tgBot.save_offset()
                update_future = executor.submit(tgBot.get_next_update)
    # keyboard break exception
    except KeyboardInterrupt:
        print("\nKeyboard break")

    # save memory
    memory.save_memory()
    executor.shutdown(wait=False)

print('done')
