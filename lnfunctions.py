import json
# import sys

from lnclicommand import lncli_command


def getNodeinfo(node_pubkey):
    # get the node info
    node_info_result = lncli_command(f'getnodeinfo {node_pubkey}')
    if node_info_result is None:
        return None
    if 'node' in node_info_result:
        return node_info_result['node']
    return None

def getNodeAlias(node_pubkey):
    # get the node info
    node_Alias_result = getNodeinfo(node_pubkey)
    if node_Alias_result is None:
        return None
    if 'alias' in node_Alias_result:
        return node_Alias_result['alias']
    return None

# __main__ to run a test if this file is run directly
if __name__ == '__main__':
    result = getNodeAlias('02f1a8c87607f415c8f22c00593002775941dea48869ce23096af27b0cfdcc0b69')
    print(result)

