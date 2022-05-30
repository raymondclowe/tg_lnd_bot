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

from command_processor import command_despatcher

# generator that returns spinner characters


def spinner_generator():
    while True:
        for c in ['|', '/', '-', '\\']:
            yield c


# define doBackgroundCheck


def doBackgroundCheck(thischeck, tgbot):
    if thischeck is None:
        return

    # if it paused then don't check
    if 'paused' in thischeck and thischeck['paused']:
        return

    if ('next_check_due' in thischeck):
        next_check_due_isostr = thischeck['next_check_due']
        # if ext_check_due_isostr contains a T then set the format string to '%Y-%m-%dT%H:%M:%S.%f'
        if 'T' in next_check_due_isostr:
            next_check_due_format = '%Y-%m-%dT%H:%M:%S'
        else:
            next_check_due_format = '%Y-%m-%d %H:%M:%S'
        if '.' in next_check_due_isostr:
            next_check_due_format += '.%f'
        next_check_due_dt = datetime.datetime.strptime(
            next_check_due_isostr, next_check_due_format)

        if datetime.datetime.now() < next_check_due_dt:
            return
        log.info(
            f"doBackgroundCheck: {thischeck['next_check_due']} {thischeck['check_type']} {thischeck['check_item']}")
    # if there is no next_check_due then it should be considered due now
    # create a next_check_due that is the iso format of now plus DEFAULT_CHECK_INTERVAL_SECOND
    thischeck['next_check_due'] = (datetime.datetime.now(
    ) + datetime.timedelta(seconds=config.DEFAULT_CHECK_INTERVAL_SECONDS)).isoformat()

    # create a history dictonary that will save the result of this test
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
            if connect_result_json is not None:
                history['result'] = "connected"
                history['address_connected'] = address["addr"]
                # tgbot.send_message(chat_id, f'{thischeck["check_item"]} connected as  {thischeck["check_item"]}@{address["addr"]}' )
                # set the next_check_due to two minutes from now so the peer is probably still connected and we can get some more data
                thischeck['next_check'] = (datetime.datetime.now(
                ) + datetime.timedelta(minutes=2)).isoformat()
                thischeck['history'].append(history)
                return
            else:
                history['result'] = "not connected: failed to connect"
                thischeck['history'].append(history)
                tgbot.send_message(
                    chat_id, f'{thischeck["check_item"]} could not connect')
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
            reply = f"\nThe channel is disabled"
            tgbot.send_message(
                chat_id, f' {thischeck["check_item"]} is not good; one or both sides are disabled')
        thischeck['history'].append(history)
        return

    return None


def command_validator(text):  # unused
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
    tg_bot = telegrambotapi.TelegramBot()

    memory = memoryModule.memoryClass()

    executor = concurrent.futures.ThreadPoolExecutor(max_workers=10)

    telegram_update_future = executor.submit(tg_bot.get_next_update)

    # interactive_checking_thread_futures = []

    spinner = spinner_generator()

    log.info("Bot started, press Ctrl+C to exit")

    listOfChecks = memory.nextCheck_generator()
    try:
        # loop continuously until keypress or break
        while True:
            log.debug("checking for next update")
            # wait one second
            sleep(1)
            # print next spinner on the same line overlapping and flush the buffer
            # sys.stdout.write(next(spinner))
            print(next(spinner), end='\r')
            reply = ""
            # check_channel(next(memory.nextCheck()))
            next_check = next(listOfChecks)

            if next_check is not None:
                log.debug(f"checking {next_check['check_item']}")
                doBackgroundCheck(next_check, tg_bot)
                memory.update_check(next_check)
            else:
                log.debug("no more checks to do")

            # if there is an update then this is an incomming command, process it

            if telegram_update_future.done():
                log.debug("telegram update is done")
                # get the update
                telegram_update = telegram_update_future.result()
                # if the update is a message
                if (telegram_update is not None) and ('message' in telegram_update):
                    log.debug("telegram update is a message")
                    # get the message
                    chat_id = telegram_update['message']['chat']['id']
                    first_name = telegram_update['message']['from']['first_name']
                    try:
                        username = telegram_update['message']['from']['username']
                    except KeyError:
                        username = first_name
                    try:
                        text = telegram_update['message']['text'].lower()
                    except KeyError:
                        text = ""

                    # if the message is a command
                    if text[0] == '/':
                        reply = command_despatcher(
                            text, chat_id, first_name, username, memory, tg_bot)
                    else:
                        reply = "Command must start with a '/'"
                    if reply:
                        tg_bot.send_message(chat_id, reply)
                tg_bot.save_offset()
                telegram_update_future = executor.submit(tg_bot.get_next_update)
            else:
                log.debug("telegram update is not done")
                if not telegram_update_future.running():

                    log.warning("update_future is not running")
                    log.warning(" exception: %s",
                                telegram_update_future.exception(timeout=1))
                    # something has gone wrong with the update_future, just restart it
                    telegram_update_future = executor.submit(tg_bot.get_next_update)

    # keyboard break exception
    except KeyboardInterrupt:
        print("\nKeyboard break, wait up to 50 seconds for last poll to finish")
    # throw other exceptions and log them
    except Exception as e:
        log.exception(e)
        raise

    memory.save_memory_to_disk()
    executor.shutdown(wait=False)

log.info('Stopping')
