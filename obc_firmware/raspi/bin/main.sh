#! /bin/bash

sudo killall gpsd


# Return to main directory
cd ..
#Update Directory
git pull origin master

cd /home/pi/obc_firmware/raspi/

sudo gpsd /dev/ttyS0 -F /var/run/gpsd.sock

echo $PATH
python3 main.py


exit 0
