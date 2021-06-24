#! /bin/bash

sudo killall gpsd


sudo gpsd /dev/ttyS0 -F /var/run/gpsd.sock

cd ..
cd /home/pi/obc_firmware/raspi/



echo $PATH
python3 main.py



exit 0
