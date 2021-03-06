import json

import datetime

from utils import log


# define the memory class
class memoryClass:
    def __init__(self):
        self.memory_filename = "memory.json"
        self.data = {'version': 1, 'checks': []}

        self.load_memory()

    def load_memory(self):
        try:
            with open(self.memory_filename, 'r') as f:
                # read whole file into a string s
                s = f.read()
                self.data = json.loads(s)
        except:
            pass

    def save_memory_to_disk(self):
        log.debug("Saving memory to disk")
        with open(self.memory_filename, 'w') as f:
            f.write(json.dumps(self.data, indent=4, sort_keys=True, default=str))

    def add_check(self, check):
        # if does not already exist based on check type, check item and chat id then append
        found = False
        for i in range(len(self.data['checks'])):
            if self.data['checks'][i]['check_type'] == check['check_type'] and self.data['checks'][i]['check_item'] == check['check_item'] and self.data['checks'][i]['chat_id'] == check['chat_id']:
                found = True
                break
        if not found:
            self.data['checks'].append(check)
            self.save_memory_to_disk()

    def loadhistory(self, check):
        for i in range(len(self.data['checks'])):
            if self.data['checks'][i]['check_type'] == check['check_type'] and self.data['checks'][i]['check_item'] == check['check_item'] and self.data['checks'][i]['chat_id'] == check['chat_id']:
                # if history exists return it otherwise create an empty empty list and return it
                try:
                    return self.data['checks'][i]['history']
                except:
                    self.data['checks'][i]['history'] = []
                    return self.data['checks'][i]['history']
                # return self.data['checks'][i].history

        return []

    def update_check(self, check):
       # loop through all the self.data['checks'] and find one with a matching check_type, check_item and chat_id
       # if found then update it with the new check
       # if not found then add it to the list
        found = False
        for i in range(len(self.data['checks'])):
            if self.data['checks'][i]['check_type'] == check['check_type'] and self.data['checks'][i]['check_item'] == check['check_item'] and self.data['checks'][i]['chat_id'] == check['chat_id']:
                self.data['checks'][i] = check
                found = True
                break
        if not found:
            self.data['checks'].append(check)
        self.save_memory_to_disk()

    def get_checks_by_chat_id(self, chat_id):
        checks = []
        for check in self.data['checks']:
            if check['chat_id'] == chat_id:
                checks.append(check)
        return checks

    def get_check(self, check_type, check_item, chat_id):
        # found = False
        for i in range(len(self.data['checks'])):
            if (self.data['checks'][i]['check_type'] == check_type and
                self.data['checks'][i]['check_item'] == check_item and
                    self.data['checks'][i]['chat_id'] == chat_id):
                return self.data['checks'][i]
                # found = True
                break
        return None

    # define a generator that
    def nextCheck_generator(self):
        while True:
            if (('checks' in self.data) and
                (len(self.data['checks']) > 0)):
                for check in self.data['checks']:
                    yield check
            else:
                yield None

    # def delete_channel_by_id(self, channelid):
    #     # delete channels for this time or before
    #     new_channelids = {}
    #     for channel in self.channels:
    #         if channelid != channelid:
    #             new_channelids[channelid] = self.channels[channelid]
    #     self.channels = new_channelids
    #     self.save_memory()

    # def delete_channel_by_user(self, user_id):
    #     # delete channels for this user
    #     for channelid in self.channels:
    #         if user_id in self.channels[channelid]:
    #             self.channels[channelid].remove(user_id)
    #             if len(self.channels[channelid]) == 0:
    #                 del self.channels[channelid]
    #     self.save_memory()
