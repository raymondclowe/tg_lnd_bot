# ontains 3 possible configurations
# 1. Windows on another machine
# 2. Linux logged in as lnd user
# 3. Linux logged in as another user
#
# in case 1 the lncli.exe should be in the bin folder and the certs folder should
# contains the admin.macaroon and the tls.cert from the node. then the ip address 
# of the server
#
# in case 2 nothing is needed.
#
# in case 3 the full path to the macaroon and tls are needed

import os


if os.name == 'nt':
    lncli_commandLine = "bin\\lncli --tlscertpath C:\\Users\\raymo\\tg_lnd_bot\\certs\\tls.key --macaroonpath C:\\Users\\raymo\\tg_lnd_bot\certs\\readonly.macaroon --rpcserver 192.168.0.113:10009"
else:
    # check if it is linux and the ~/.lnd directory exists
    if os.path.isdir(os.path.expanduser("~/.lnd")):
        lncli_commandLine = "lncli "
    else:
        lncli_commandLine = "/usr/local/bin/lncli --tlscertpath /home/rcl/tg_lnd_bot/certs/tls.key --macaroonpath /home/rcl/tg_lnd_bot/certs/readonly.macaroon"

DEFAULT_CHECK_INTERVAL_SECONDS = 60
