#!/bin/bash

export PYTHONPATH="/home/nx4/git/ServerConnection/mavlink" # assigne python path for pymavlink dialect
#export PIXHAWK_PORT="/dev/ttyTHS0:115200"
chmod 777 /dev/ttyTHS0 # enable to access Pixhawk4(baudrate = 115200)
python3 ServerConnection.py # get RELAYSERVER_IP
#printf $RELAYSERVER_IP # for debugging
#mavlink-routerd -e $RELAYSERVER_IP -e 127.0.0.1 $PIXHAWK_PORT # connect mavlink router