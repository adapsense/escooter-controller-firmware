
import os
from gps import *
from time import *
import time
import json
import threading

import config

import logging
logger = logging.getLogger("GPS")
# Set logger to NOT use root logger Settings
logger.propagate = False
#Create File handler and format
fh = logging.FileHandler('log/gps.log')
fh.setLevel(logging.DEBUG)
logFormatter = logging.Formatter('%(asctime)s %(name)-10s %(message)s')
fh.setFormatter(logFormatter)
logger.addHandler(fh)

def gpsdReset():
	#Reset DAEMON outside
	os.system('clear') #clear the terminal (optional)
	logger.info("Resetting GPSD")
	#Kills Alls Possible Running GPSD instances
	try:
		if config.isRaspi():
			os.system("sudo killall gpsd")
			#starts GPSD with Serial0 feed
			os.system("sudo gpsd /dev/ttyS0 -F /var/run/gpsd.sock")
		else:
			print("\nNot Running in Raspberrypi\n")

		logger.info("GPSD command completed")
		return True

	except Exception as e:
		print (e)
		return False

def gpsc():
	gpsc = GPS_CLIENT()
	gpsc.start()
	return gpsc

class GPS_CLIENT(threading.Thread):
	def __init__(self, interval = 2):
		#create separate thread for this function
		threading.Thread.__init__(self,daemon = True)
		self.name = "Thread: GPS"

		#Set stream info
		while True:
			try:
				self.gps = gps(mode=WATCH_ENABLE) #starting the stream of info
				break
			except Exception as e:
				print(e)
				print("Trying to Reconnect")
				gpsdReset()
		#self.current_value = None


		
		self.ALIVE = True #setting the thread running to true

		self.interval = interval
		self.savePower = config.POWERSAVING

		self.lat = 0
		self.prevLat = 0
		self.long = 0
		self.prevLong = 0
	def stop(self):
		if config.DEBUGGING:
			print("GPS Thread Stopping Please Wait")
		self.ALIVE = False

	def run(self):#What Happens inside the Thread
		while self.ALIVE:
			#this will continue to loop and grab EACH set of gpsd info to clear the buffer
			self.gps.next()

			if self.savePower:
				time.sleep(self.interval)

		if config.DEBUGGING:
			print("GPS Thread STOPPED")

	def coordinates(self):
		# Log if current Location is not the same as Prev Locations
		accuracy = 8
		self.lat = round(self.gps.fix.latitude,accuracy)
		self.long = round(self.gps.fix.longitude,accuracy)
		if self.lat != self.prevLat or self.long != self.prevLong:
			self.prevLat = self.lat
			self.precLong = self.long
			#logger.info(("\"LAT\":%f\"LONG\":%f" % (self.lat , self.long)))
			#logger.info("\'coord\' :{:>20.10f}, {:<20.10f}\}".format(self.lat , self.long))
			logger.info( str(json.dumps({'coordinates' : (self.lat, self.long)}) ) )
		return self.gps.fix.latitude,self.gps.fix.longitude
		#return self.lat , self.long

	def getLat(self):
		return self.gps.fix.latitude
	def getLong(self):
		return self.gps.fix.longitude

	def estError(self):
		pass

##################################################


def main():
	print('Test Functionality')
	gpsp = gpsc() # create the thread
	try:
		# start it up
		while True:
			#It may take a second or two to get good data
			#print gpsd.fix.latitude,', ',gpsd.fix.longitude,'  Time: ',gpsd.utc

			os.system('clear')

			print()
			print (' GPS reading')
			print ('----------------------------------------')
			print ('latitude    ' , gpsp.gps.fix.latitude)
			print ('longitude   ' , gpsp.gps.fix.longitude)
			print("Both",gpsp.coordinates())
			print ('time utc    ' , gpsp.gps.utc,' + ', gpsp.gps.fix.time)
			print ('altitude (m)' , gpsp.gps.fix.altitude)

			print ('eps speed    ' , gpsp.gps.fix.eps)
			print ('epx long    ' , gpsp.gps.fix.epx)
			print ('epy lat     ' , gpsp.gps.fix.epy)
			print ('epv vert    ' , gpsp.gps.fix.epv)
			print ('ept time    ' , gpsp.gps.fix.ept)
#			print ('speed (m/s) ' , gpsp.gps.fix.speed)
#			print ('climb  m/s  ' , gpsp.gps.fix.climb)
			print ('track DEGREE' , gpsp.gps.fix.track)
			print ('mode        ' , gpsp.gps.fix.mode)
			print("")
#			print ('sats        ' , gpsp.gps.satellites)

			time.sleep(5) #set to whatever

	except (KeyboardInterrupt, SystemExit): #when you press ctrl+c
		print("Error @:gps client  @MAIN")

		print ("\nKilling Thread...")
		gpsp.ALIVE = False
		#gpsp.join() # wait for the thread to finish what it's doing
		print ("Done.\nExiting.")


if __name__ == '__main__':
	main()
