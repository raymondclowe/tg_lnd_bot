import json
import datetime

def keystoint(x):
    return {int(k): v for k, v in x.items()}


from dataclasses import dataclass



# define a data structure class called check with an id, a check_type, a user_id and a check_value
@dataclass
class checkType:
    id: int
    check_type: str # check_type is either "node" or "channel"
    user_id: int # tg chat id
    check_value: str # check_value is either a node or a channel id
    last_checked: datetime.datetime 
    next_check_due: datetime.datetime  
    last_result_ok_at: datetime.datetime
    last_result: str = ""
    last_result_ok: bool = False
    check_interval: int = (60 * 5)


# define the memory class
class memoryClass:
    def __init__(self):
        self.memory_filename = "memory.json"
        self.checks = {}
        
        self.load_memory()

    def load_memory(self):
        try:
            with open(self.memory_filename, 'r') as f:
                self.channels = json.load(f, object_hook=keystoint)
        except:
            pass

    def save_memory(self):
        with open(self.memory_filename, 'w') as f:
            json.dump(self.channels, f)

    def add_check(self, check):
        self.checks.append(check)
        self.save_memory()
    
    
    # define a generator that 
    def nextCheck(self):
        if self.checks:
            while True:
                for check in self.checks:
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
