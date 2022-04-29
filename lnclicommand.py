
import json
import sys

from executecommand import runcmd
from config import lncli_commandLine

def lncli_command(command):
    getinfo = lncli_commandLine + " getinfo"

    # print(getinfo)

    result, error, errorlevel = runcmd(getinfo)

    if error:
        print(error)
        return None
    else:
        try:
            resultjson = json.loads(result)
            return resultjson
        except Exception as e:
            print(f"error: {e}")
            return None
            

# __main__ to run a test if this file is run directly
if __name__ == '__main__':
    # if there is a command on the arguement line
    if len(sys.argv) > 1:
        cmdstring = sys.argv[1]
    else:    # if not, use a default command
        cmdstring = 'getinfo'
    # print(f"executing {cmdstring}")

    result = lncli_command(cmdstring)

    if result:
        print(result)
    else:
        print("no result")
        print()

