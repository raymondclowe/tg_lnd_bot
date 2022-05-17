#!/usr/bin/env python3
# may need python3.8 for this to work
from utils import log

import sys
import concurrent.futures
import datetime
import string
import json
from time import sleep

import config
import memoryModule
import telegrambotapi

from lnclicommand import lncli_command

# generator that returns spinner characters


def spinner_generator():
    while True:
        for c in ['|', '/', '-', '\\']:
            yield c


def doTheInteractiveCheck(thischeck, tgbot, chat_id):
    if thischeck is None:
        return 'Nothing to check'  # unchanged

    # tgbot.send_message(chat_id, 'checking ...')

    # create a history dictonary
    history = {}
    history['datetime'] = datetime.datetime.now().isoformat()
    history['result'] = ''

    # if thischeck['history'] doesn't exist then create it with empty list
    if 'history' not in thischeck:
        thischeck['history'] = []

    if thischeck['check_type'] == 'node':
        # get a list of lnd peers
        # if not on the list then do a lncli connectpeer and keep waiting until the connection happens and a ping time is available, or it timesout after 1 minute
        # tgbot.send_message(chat_id, f'Getting list of peers' )
        peers_json = lncli_command('listpeers')
        # print(peers)

        if peers_json is None:
            return 'Error getting list of peers'

        # loop through peers_json
        for peer in peers_json['peers']:
            # tgbot.send_message(chat_id, f'checking peer:  {peer["pub_key"]}' )
            if peer['pub_key'] == thischeck['check_item']:
                tgbot.send_message(
                    chat_id, f'node {peer["pub_key"]} is online as a peer')
                # found the peer in the list
                # check if the ping time is available
                history['result'] = "online as peer"
                if 'ping_time' in peer:
                    # ping time is available
                    tgbot.send_message(
                        chat_id, f'Ping time is {peer["ping_time"]}')
                    history['pingtime'] = peer["ping_time"]
                if 'flap_count' in peer:
                    #
                    tgbot.send_message(
                        chat_id, f'Flap count is {peer["flap_count"]}')
                    history['flapcount'] = peer["flap_count"]
                if 'last_flap_ns' in peer:
                    last_flap_ns = peer['last_flap_ns']
                    # convert last_flap_ns in epoch ns to a datetime object
                    last_flap_dt = datetime.datetime.fromtimestamp(
                        int(last_flap_ns) / 1e9)
                    history['flap_time'] = last_flap_dt.isoformat()
                    tgbot.send_message(
                        chat_id, f'Last flap time is {last_flap_dt}')
                thischeck['history'].append(history)
                return "Check completed"

        # if we get here then the peer is not on the list
        # do a connectpeer
        tgbot.send_message(
            chat_id, f'{thischeck["check_item"]} is not on the local peer list')
        history['result'] = "not on list"
        nodeinfo = lncli_command(f'getnodeinfo {thischeck["check_item"]}')
        if nodeinfo is None:
            # tgbot.send_message(chat_id, )
            history['result'] = "not on graph"
            thischeck['history'].append(history)
            return f'peer {thischeck["check_item"]} is not on the graph'
        # print(nodeinfo)
        # print(nodeinfo['pub_key'])
        # print(thischeck['check_item'])
        if nodeinfo['node']['pub_key'] == thischeck['check_item']:
            tgbot.send_message(
                chat_id, f'{thischeck["check_item"]} is on the graph, trying to connect to it')

        # see if the addresses exists
        if nodeinfo["node"]["addresses"] is None:
            # tgbot.send_message(chat_id, f'peer {thischeck["check_item"]} has no addresses' )
            history['result'] = "no addresses"
            thischeck['history'].append(history)
            return f'{thischeck["check_item"]} has no addresses'
        history['addresses_available'] = nodeinfo["node"]["addresses"]
        for address in nodeinfo["node"]["addresses"]:

            connect_result_json = lncli_command(
                f'connect {thischeck["check_item"]}@{address["addr"]}')
            if connect_result_json is not None:
                history['result'] = "connected"
                history['address_connected'] = address["addr"]
                tgbot.send_message(
                    chat_id, f'{thischeck["check_item"]} connected as  {thischeck["check_item"]}@{address["addr"]}')
                return

        history['result'] = "could not connect"
        thischeck['history'].append(history)
        return f'peer {thischeck["check_item"]} could not connect as  {thischeck["check_item"]}@{nodeinfo["node"]["addresses"]}'

        # wait for up to 60 seconds
        tgbot.send_message(
            chat_id, f'waiting up to 60 seconds for {thischeck["check_item"]} to get valid ping time')
        start_time = datetime.datetime.now()

        # while until 60 seconds have passed
        while True:
            # if the time is now start_time plus 60 then break
            if datetime.datetime.now() >= start_time + datetime.timedelta(seconds=60):
                history['result'] = "connected but timeout trying to get ping time"
                thischeck['history'].append(history)
                return "Connected but didn't get valid ping within 60 seconds, try checking later"

            # get the listpeer again
            peers_json = lncli_command('listpeers')
            # loop through peers_json
            for peer in peers_json['peers']:
                # tgbot.send_message(chat_id, f'checking peer:  {peer["pub_key"]}' )
                if peer['pub_key'] == thischeck['check_item']:
                    # found the peer in the list
                    # check if the ping time is available
                    history['result'] = "online as peer after connecting"
                    if 'ping_time' in peer:
                        # ping time is available
                        # if the ping time is zero wait 1 seconds and continue loop
                        if peer['ping_time'] == '0':
                            sleep(1)
                            break
                        # if the ping time is not zero then return the ping time
                        history['pingtime'] = peer["ping_time"]
                        thischeck['history'].append(history)
                        return f'Ping time is {peer["ping_time"]}'
            sleep(1)

    if thischeck['check_type'] == 'channel':
        channel_info = lncli_command(f'getchaninfo {thischeck["check_item"]}')
        if channel_info is None:
            history['result'] = "not on graph"
            thischeck['history'].append(history)
            return f'channel {thischeck["check_item"]} is not on the graph'
        # print(channel_info)
        # convert the last_update time to a datetime object and then to a normal string date
        last_update_dt = datetime.datetime.fromtimestamp(
            int(channel_info['last_update']))
        last_update_str = last_update_dt.strftime('%Y-%m-%d %H:%M:%S')
        history['last_update'] = f"online : {last_update_str}"
        reply = f"Found the channel. The last update time is {last_update_str}."

        # if node 1 node1_policy and node2_policy disabled are both false then the channel is good
        if channel_info['node1_policy']['disabled'] == False and channel_info['node2_policy']['disabled'] == False:
            history['result'] = "channel is good"
            reply += f"\nThe channel is good"
        else:
            history['result'] = "channel is not good"
            reply += f"\nThe channel is disabled"
        thischeck['history'].append(history)
        return reply

    return None

# define doBackgroundCheck


def doBackgroundCheck(thischeck, tgbot):
    if thischeck is None:
        return

    # if it paused then don't check
    if thischeck['paused']:
        return

    if ('next_check_due' in thischeck):        
        next_check_due_isostr = thischeck['next_check_due']
        next_check_due_dt = datetime.datetime.strptime(next_check_due_isostr, '%Y-%m-%dT%H:%M:%S.%f')

        if datetime.datetime.now() < next_check_due_dt:
            return
    log.debug(f"doBackgroundCheck: {thischeck}")
    # create a next_check_due that is the iso format of now plus DEFAULT_CHECK_INTERVAL_SECOND
    thischeck['next_check_due'] = (datetime.datetime.now() + datetime.timedelta(seconds=config.DEFAULT_CHECK_INTERVAL_SECONDS)).isoformat()

    # create a history dictonary that will save the result of this text
    history = {}
    history['datetime'] = datetime.datetime.now().isoformat()
    history['result'] = ''

    # if thischeck['history'] doesn't exist then create it with empty list
    if 'history' not in thischeck:
        # <--- this is where the history object will be saved if I get a valid result
        thischeck['history'] = []

    chat_id = thischeck['chat_id']

    if thischeck['check_type'] == 'node':
        # get a list of lnd peers
        # if not on the list then do a lncli connectpeer and keep waiting until the connection happens and a ping time is available, or it timesout after 1 minute
        # tgbot.send_message(chat_id, f'Getting list of peers' )
        peers_json = lncli_command('listpeers')
        # print(peers)

        if peers_json is None:
            # log an error
            log.error(f'Error getting list of peers')
            return

        # loop through peers_json
        for peer in peers_json['peers']:
            # tgbot.send_message(chat_id, f'checking peer:  {peer["pub_key"]}' )
            if peer['pub_key'] == thischeck['check_item']:
                # tgbot.send_message(chat_id, f'node {peer["pub_key"]} is online as a peer' )
                # found the peer in the list
                # check if the ping time is available
                history['result'] = "online as peer"
                if 'ping_time' in peer:
                    # ping time is available
                    # tgbot.send_message(chat_id, f'Ping time is {peer["ping_time"]}' )
                    history['pingtime'] = peer["ping_time"]
                if 'flap_count' in peer:
                    #
                    # tgbot.send_message(chat_id, f'Flap count is {peer["flap_count"]}' )
                    history['flapcount'] = peer["flap_count"]
                if 'last_flap_ns' in peer:
                    last_flap_ns = peer['last_flap_ns']
                    # convert last_flap_ns in epoch ns to a datetime object
                    last_flap_dt = datetime.datetime.fromtimestamp(
                        int(last_flap_ns) / 1e9)
                    history['flap_time'] = last_flap_dt.isoformat()
                    # tgbot.send_message(chat_id, f'Last flap time is {last_flap_dt}' )
                thischeck['history'].append(history)
                return

        # if we get here then the peer is not on the list
        # do a connectpeer
        # tgbot.send_message(chat_id, f'{thischeck["check_item"]} is not on the local peer list' )
        history['result'] = "not on list"
        nodeinfo = lncli_command(f'getnodeinfo {thischeck["check_item"]}')
        if nodeinfo is None:
            # tgbot.send_message(chat_id, )
            history['result'] = "not on graph"
            thischeck['history'].append(history)
            tgbot.send_message(
                chat_id, f' {thischeck["check_item"]} is not on the graph')
            return

        # see if the addresses exists
        if nodeinfo["node"]["addresses"] is None:
            tgbot.send_message(
                chat_id, f'peer {thischeck["check_item"]} has no addresses')
            history['result'] = "no addresses"
            thischeck['history'].append(history)
            return
        history['addresses_available'] = nodeinfo["node"]["addresses"]
        for address in nodeinfo["node"]["addresses"]:

            connect_result_json = lncli_command(
                f'connect {thischeck["check_item"]}@{address["addr"]}')
            if not connect_result_json is None:
                history['result'] = "connected"
                history['address_connected'] = address["addr"]
                # tgbot.send_message(chat_id, f'{thischeck["check_item"]} connected as  {thischeck["check_item"]}@{address["addr"]}' )
                # set the next_check_due to two minutes from now so the peer is probably still connected and we can get some more data
                thischeck['next_check'] = (datetime.datetime.now(
                ) + datetime.timedelta(minutes=2)).isoformat()
                thischeck['history'].append(history)
                return

        history['result'] = f'could not connect to any of {len(nodeinfo["node"]["addresses"])} address(es)'
        thischeck['history'].append(history)
        return

    if thischeck['check_type'] == 'channel':
        channel_info = lncli_command(f'getchaninfo {thischeck["check_item"]}')
        if channel_info is None:
            history['result'] = "not on graph"
            thischeck['history'].append(history)
            tgbot.send_message(
                chat_id, f' {thischeck["check_item"]} is not on the graph')
            return
        # print(channel_info)
        # convert the last_update time to a datetime object and then to a normal string date
        last_update_dt = datetime.datetime.fromtimestamp(
            int(channel_info['last_update']))
        last_update_str = last_update_dt.strftime('%Y-%m-%d %H:%M:%S')
        history['last_update'] = f"online : {last_update_str}"
        # reply = f"Found the channel. The last update time is {last_update_str}."

        # if node 1 node1_policy and node2_policy disabled are both false then the channel is good
        if channel_info['node1_policy']['disabled'] == False and channel_info['node2_policy']['disabled'] == False:
            history['result'] = "channel is good"
            # reply += f"\nThe channel is good"
        else:
            history['result'] = "channel is not good"
            reply += f"\nThe channel is disabled"
            tgbot.send_message(
                chat_id, f' {thischeck["check_item"]} is not good; one or both sides are disabled')
        thischeck['history'].append(history)
        return

    return None


def command_validator(text):
    # returns either None, error message if it is invalid or true, list of the words

    # if the first character is not a '/' then ignore this
    if text[0] != '/':
        return False, "Command must start with a '/'"

    # strip off the initial character
    text = text[1:]

    words = text.split()

    if words[0] not in ['monitor', 'check', 'pause', 'resume', 'list', 'help']:
        return False, f"Command must be one of: monitor, check, pause, resume, list, help"
    
    if words[0] in ['help', 'list']:
        return True, words

    # what's left is 'monitor', 'check', 'pause', 'resume' which all take second word 'channel' or 'node'
    if words[1] not in ['channel', 'node']:
        return False, f"Second word must be either 'channel' or 'node'"

    # if channel then the next word is the channel id
    if words[1] == 'channel':
        if len(words) != 3:
            return False, f"If second word is 'channel' then the third word must be the channel id"
        if not words[2].isdigit():
            return False, f"Channel id must be a number"
        return True, words
  
  
    # node is 66 characters hex
    if words[1] == 'node':
        if len(words) != 3:
            return False, f"If second word is 'node' then the third word must be the 66 character hex node  id"
        if len(words[2]) != 66:
            if not all(c in string.hexdigits for c in words[2]):
                return False, f"Node id must be 66 characters hex"
                    # validcommand = False
    return False, "Fell through"


# if this is __main__
if __name__ == "__main__":
    log.info("starting")
    # create telegram bot object
    tgBot = telegrambotapi.TelegramBot()

    memory = memoryModule.memoryClass()

    executor = concurrent.futures.ThreadPoolExecutor(max_workers=10)

    update_future = executor.submit(tgBot.get_next_update)

    interactive_checking_thread_futures = []

    spinner = spinner_generator()

    log.info("Bot started, press Ctrl+C to exit")
    try:
        # loop continuously until keypress or break
        while True:
            # wait one second
            sleep(1)
            # print next spinner on the same line overlapping and flush the buffer
            # sys.stdout.write(next(spinner))
            print(next(spinner), end='\r')

            # check_channel(next(memory.nextCheck()))
            next_check = next(memory.nextCheck())

            if not next_check is None:
                doBackgroundCheck(next_check, tgBot)
                memory.update_check(next_check)

                # check the udpate_future status

            # print(update_future.running())
            # print(update_future.cancelled())
            # print(update_future.done())

            # if there is an update then this is an incomming command, process it

            if update_future.done():
                # get the update
                update = update_future.result()
                # if the update is a message
                if (update is not None) and ('message' in update):
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
                        tgBot.save_offset()
                        update_future = executor.submit(tgBot.get_next_update)

                        continue

                    # strip off the initial character
                    text = text[1:]

                    words = text.split()

                    if words[0] in ['monitor', 'check', 'pause', 'resume', 'help']:

                        # check if the command is valid
                        validcommand = True

                        if words[0] == 'help':
                            tgBot.send_message(chat_id, help_message)
                        elif len(words) != 3:
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

                            if command_type == 'pause':
                                # find if the check already exists
                                loaded_check = memory.get_check(check_type, check_item, chat_id)
                                if loaded_check is None:
                                    reply = f"{check_item} is not being monitored"
                                else:
                                    loaded_check['paused'] = True
                                    reply = f"{check_item} is now paused"
                                    memory.update_check(loaded_check)

                            elif command_type == 'resume':
                                # find if the check already exists
                                loaded_check = memory.get_check(check_type, check_item, chat_id)
                                if loaded_check is None:
                                    reply = f"{check_item} is not being monitored"
                                else:
                                    loaded_check['paused'] = False
                                    reply = f"{check_item} is now resumed"
                                    memory.update_check(loaded_check)

                            # construct a check object which is a dictionary
                            thischeck = {'check_type': check_type,
                                         'check_item': check_item,
                                         'chat_id': chat_id,
                                         'next_check_due': datetime.datetime.now() + datetime.timedelta(seconds=config.DEFAULT_CHECK_INTERVAL_SECONDS)}

                            # if this is for command monitor then add it to the memory otherwise check it now
                            if command_type == 'monitor':
                                memory.add_check(thischeck)
                                reply = f"Adding {thischeck}"
                            else:
                                thischeck['history'] = memory.loadhistory(
                                    thischeck)
                                reply = doTheInteractiveCheck(
                                    thischeck, tgBot, chat_id)
                                memory.update_check(thischeck)

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
            else:
                if not update_future.running():

                    log.warning("update_future is not running")
                    log.warning(" exception: %s",
                                update_future.exception(timeout=1))
                    # something has gone wrong with the update_future, just restart it
                    update_future = executor.submit(tgBot.get_next_update)

    # keyboard break exception
    except KeyboardInterrupt:
        print("\nKeyboard break, wait up to 50 seconds for last poll to finish")
    # throw other exceptions and log them
    except Exception as e:
        log.exception(e)
        raise
    

    # save memory
    memory.save_memory()
    # executor.shutdown(wait=False)
    executor.shutdown(wait=False)

log.info('Stopping')
