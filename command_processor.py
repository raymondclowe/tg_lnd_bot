# despatch and process commands
# 'start', 'monitor', 'check', 'pause', 'resume', 'list', 'help'
import string

from lnclicommand import lncli_command

import datetime


def interactive_check(thischeck, tgbot, chat_id):
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

def parse_check(command):
         # validate that the syntax is correct which is /monitor {node|channel} {node_id|channel_id}
        # split into words and make sure there are three words
        words = command.split()
        if len(words) != 3:
            return  None, 'Invalid syntax. Use /monitor {node|channel} {node_id|channel_id}'
        # make sure the second words is node or chanel
        if words[1] not in ['node', 'channel']:
            return None, 'Invalid syntax. Use /monitor {node|channel} {node_id|channel_id}'
        # if the word is node then the third word needs to be 66 characters all hex
        if words[1] == 'node':
            if len(words[2]) != 66:
                return 'Invalid syntax. Use /monitor {node|channel} {node_id|channel_id}'
            if not all(c in string.hexdigits for c in words[2]):
                return None, f"Node id must be 66 characters hex"
        else: # word[1] == 'channel'
            if not words[2].isdigit():
                return None, f"Channel id must be a number"
        return words[1], words[2]

def doCommand_monitor(command, chat_id, memory):
           
        # if syntax is correct, then start monitoring the node or channel if it is not already
        # check if a monitor with these details already exists
        check_type, check_item = parse_check(command)

        if check_type is not None:
            existing_check = memory.get_check( check_type, check_item, chat_id)
        else:
            return check_item # which will contain the error message
    


        # if existing_check is none then reply error already monitoring
        if existing_check is not None:
            return f"Already monitoring {check_type} {check_item}"

        # if not then add the check to the list
        memory.add_check({'check_type': check_type, 'check_item': check_item, 'chat_id': chat_id})
        return f"Starting to monitor {check_type} {check_item}"

def doCommand_list(chat_id, memory):

    reply = f"List of all your channels and nodes\n"
    your_checks = memory.get_checks_by_chat_id(chat_id)
    for check in your_checks:
        reply += f"{check['check_type']} -> {check['check_item']} "
        if 'alias' in check:
            reply += f" ({check['alias']})"
        if 'paused' in check:
            reply += f" [paused]"
        reply += "\n"
    
    return reply
                                
def doCommand_check(command, chat_id, tg_bot):
        check_type, check_item = parse_check(command)

        if check_type is None:
            return check_item # which will contain the error message

        # now create the check dictionary and do the interactive check
        check = {'check_type': check_type, 'check_item': check_item, 'chat_id': chat_id}

        reply = interactive_check(check, tg_bot, chat_id)
    
        return reply
 

def doCommand_pause(command, chat_id, memory):
    # check if a monitor with these details already exists
    check_type, check_item = parse_check(command)

    if check_type is None:
        return check_item # which will contain the error message

    # if existing_check is none then reply error already monitoring
    existing_check = memory.get_check( check_type, check_item, chat_id)
    if existing_check is None:
        return f"You are not monitoring {check_type} {check_item}"
    # if not then add the check to the list
    existing_check['paused'] = True
    memory.update_check(existing_check)
    return f"Pausing monitoring {check_type} {check_item}"

def doCommand_resume(command, chat_id, memory):
    # check if a monitor with these details already exists
    check_type, check_item = parse_check(command)

    if check_type is None:
        return check_item # which will contain the error message

    # if existing_check is none then reply error already monitoring
    existing_check = memory.get_check( check_type, check_item, chat_id)
    if existing_check is None:
        return f"You are not monitoring {check_type} {check_item}"
    # if not then add the check to the list
    existing_check['paused'] = False
    memory.update_check(existing_check)
    return f"Resuming monitoring {check_type} {check_item}"


def command_despatcher(command, chat_id, first_name, username, memory, tg_bot):

    # if command starts with /start
    if command.startswith('/start'):
        return f'Hello {first_name}(@{username})! I am a lightning network monitor bot. Say /help for help'

    elif command.startswith('/help'):
        # load the help_text.md and return it as a reply
        with open('help_text.md', 'r') as help_text:
            return help_text.read()

    elif command.startswith('/monitor '):
        # call the monitor function
        return doCommand_monitor(command, chat_id, first_name, username, memory)

    elif command.startswith('/list'):
        # call the list function
        return doCommand_list(chat_id, memory)

    # '/check' command
    elif command.startswith('/check'):
        # call the check function
        return doCommand_check(command, chat_id, tg_bot)

    # pause command
    elif command.startswith('/pause'):
        # call the pause function
        return doCommand_pause(command, chat_id, memory)
    
    # resume command
    elif command.startswith('/resume'):
        # call the resume function
        return doCommand_resume(command, chat_id, memory)


    pass