# escooter-controller-firmware

How to setup a new controller
1. Flash SD card with Raspbian OS.
2. Boot the Raspberry Pi with the flashed SD card.
3. If a monitor can't be connected
   a. connect a 3G dongle to the USB port
   b. Connect through ssh to either 192.168.0.100 or 192.168.0.101
```
ssh pi@192.168.0.100
```
      or
```
ssh pi@192.168.0.101
```
   c. Password is 'raspberry'
4. Open Terminal
5. Run the following
```
sudo raspi-config
```
6. Go to 'Interfacing Options' and enable VNC, I2C and SERIAL
7. Reboot Raspberry Pi
```
sudo reboot now
```
8. Connect to Raspberry Pi through VNC
9. Ensure Raspberry Pi has Internet Connection
10. Open Terminal and update Raspberry Pi with the following
```
sudo apt-get update
sudo apt-get dist-upgrade
```
11. Clone obc_firmware to /home/pi
```
git clone https://github.com/adapsense/escooter-controller-firmware.git
```
12. Run setup
```
sh obc_firmware/setup.sh
```
13. Edit Vehicle number in obc_firmware/raspi/config/data.json
14. Edit other details in obc_firmware/raspi/config/__init__.py
