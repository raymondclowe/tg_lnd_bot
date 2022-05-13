#!/bin/bash
set -x #echo onq

cd /home/rcl/tg_lnd_bot
pwd
source .venv3.8/bin/activate
python3 tg_lnd_bot.py
