#! /bin/bash
#echo $PATH

sudo killall gpsd
sudo gpsd /dev/ttyS0 -F /var/run/gpsd.sock
cd /home/pi/obc_firmware/raspi/
python3 main.py

exit 0
