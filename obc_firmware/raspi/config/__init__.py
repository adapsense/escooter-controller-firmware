
# Contains Setup Data for easier control over all items
#Debugging Output Configs

SCOOTER = True

#DEBUGGING = False
DEBUGGING = True

VERBOSE = False

MQTT_RECONNECT = False
MQTT_CLEAN_SESSION = False

PROTO = True
POWERSAVING = False
POWERSAVING_INTERVAL = 2#

broker_ip="do.adapsense.com"
broker_port=8083
broker_path="/mqtt"
broker_username="scooter2"
broker_password="@d@ps3ns3"

reportInterval = 3
maxReportsFailed = 300
MAX_DOWNTIME = 60
min_movement = 5 #Number of meters considered as "no movement"
max_sample = 5 #Number of data sets to gather before transmission
measure_time = 60 #Number of minutes between data usage checking
default_report_time = 1 #Number of minutes between reporting
noGPS_report_time = 5 #Number of minutes of no valid GPS data before force sending a report with invalid GPS coordinates
lowpower_report_time = 5 #Number of minutes between reporting during Power tamper
watchdog_period = 0.24 #Number of seconds each cycle of the watchdog signal lasts

def restartFunction(pw):
	import os
	if pw == 'upbikeshareAdmin':
		os.system('sudo reboot now')
	else:
		print("ERROR: Restart Called")

##########################################################################################

#Logging
def loggingSetup():
	import logging

	#Log Stream handler
	#Prints Only The Message Since Other Data Are Not Usually IMportant RealTime
	msg_format = '%(message)s'
	consoleHandler = logging.StreamHandler()
	if DEBUGGING:
		consoleHandler.setLevel(logging.DEBUG)
	else:
		consoleHandler.setLevel(logging.INFO)

	consoleFormatter = logging.Formatter(msg_format)
	consoleHandler.setFormatter(consoleFormatter)


	#File handler
	#Format Reports All Possible Data Useful for Remote Debugging
	log_format = '%(asctime)s %(levelname)-8s %(name)-10s %(message)s \tThread:%(threadName)-20s Func: %(funcName)-15s in %(filename)s #: %(lineno)-4d '

	fh = logging.FileHandler('log/system.log')
	fh.setLevel(logging.INFO)

	logFormatter = logging.Formatter(log_format)
	fh.setFormatter(logFormatter)


	#Set Handlers
	handlers = [fh, consoleHandler]
	#logging.getLogger().addHandler(consoleHandler)
	logging.basicConfig(level=logging.INFO,
						handlers = handlers
						)


##########################################################################################
#Platform Data

def getSerial(): #Of raspberrypi
# Extract serial from cpuinfo file
	cpuserial = "0000000000000000"
	try:
		f = open('/proc/cpuinfo','r')
		for line in f:
			if line[0:6] == 'Serial':
				cpuserial = line[10:26]
		f.close()
	except:
		cpuserial = "Serial_Not_Found"
		#Should be removed after testing
		if isPC():
			cpuserial = "000000002a50a0b1"
	return cpuserial




import platform
def detectPlatform():# detect OS used
	#print("Platform Data:",platform.uname())
	if platform.uname()[0] == "Linux":
		if platform.uname()[1] == "raspberrypi":
			if DEBUGGING:
				#print(platform.uname())
				pass
			PC = False
			RASPI = True
			return PC, RASPI
	else:
		PC = True
		RASPI = False
		return PC, RASPI

def isPC():
	PC, RASPI = detectPlatform()
	if DEBUGGING:
		print("isPC:",PC)
	return PC

def isRaspi():
	try:
		if TEST:
			PC, RASPI = True, False
			return False
	except:
		pass

	PC, RASPI = detectPlatform()
	if DEBUGGING:
		print("isRaspi",RASPI)
	return RASPI


PC = isPC()
RASPI = isRaspi()



##########################################################################################
# Web Functions

import urllib.request as urllib
def isOnline(url = None, timeout = 5):
	try:
		if url != None:
			if DEBUGGING:
				print("Checking Connection to:", url)
		else:
			if DEBUGGING:
				print("Checking Internet Access")
			url = 'http://216.58.192.142'
	#		urllib.urlopen("mqtt://54.254.208.136",timeout = 1)

		urllib.urlopen(url, timeout= timeout)#second
		return True

	except Exception as e:
		print(e)
		return False

##########################################################################################

import threading
def displayThreads():
	print("########################################################################")
	print("All Live threads:\t")
	for item in threading.enumerate():
		print("\t",item.name)
	print("########################################################################")



##########################################################################################
#Bike Data Loader

import json, copy, datetime
class BIKEDATA():
	# only import if called to reduce

	DATA_FILE = "config/data.json"
	def __init__(self, path = DATA_FILE):

		self.gaplen = 25
		self.DATA = {}
		self.load()
		#self.DATA["name"] = "UPD-000"

		self.DATA["lat"] =  14.550720
		self.DATA["long"] = 120.987217
		self.DATA_PATH = path



	def load(self,filename=DATA_FILE):
		if filename != None:
			fn = filename

		print('{:{slen}s}{:50s}'.format("Loading Data from:",fn,slen = self.gaplen))

		with open(fn, 'r') as fp:
			self.DATA = json.load(fp)
		print('{:{slen}s}{:50s}'.format("DATA Loaded:",json.dumps(self.DATA), slen = self.gaplen))


	def save(self,filename=DATA_FILE):
		
		#print('{:{slen}s}{d1}'.format('INSIDE SAVE DATA', d1 = self.DATA, slen = self.gaplen))
		if filename != None:
			fn = filename
		dict1 = self.DATA.copy()
		#print('dict1', dict1)
		#del dict1['lat']
		#del dict1['long']
		#print('dict1', dict1)

		#print("Saving Data to:{:>10s} <- {dic1}".format(fn, dic1 = dict1), self.DATA)
		print("{:{slen}s}{:>10s} ".format('Saving Data to:',fn, slen = self.gaplen))
		print('{:>{slen}s}{d1}'.format('', d1 = dict1, slen = self.gaplen))
		with open(self.DATA_PATH, 'w') as fp:
			json.dump(dict1, fp)
		#print("DATA:\t\t\t",dict1)


	def add(self,key = None, val = None):
		if key == None or val == None:
			print("Value Error:",key,val)
		else:
			print("Adding Pair:\t\"",key,"\":",val)
			self.DATA[key] = val

	def update(self,dict2 = None,key = None, val = None):
		if key == 'name':
			return
		print("OLD:", self.DATA)
		if key != None and val != None:
			self.add(key,val)
		else:
			print("Incomplete Data\nNothing Done")

		if dict2 != None:
			print("Updating new data:", dict2)
			self.DATA.update(dict2)

		print("New",self.DATA)

	def lockStatus(self, lock_status = None):
		ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
		#print(ts)

		if lock_status is not None:
			print('{:<{slen}s}{:2s}'.format('New Lock Status:',lock_status, slen = self.gaplen))
			self.DATA['lock_status'] = lock_status
			self.DATA['timestamp'] = ts
			self.save()
		if 'lock_status' in  self.DATA:
			return self.DATA['lock_status']
		else:
			return 'L'



##########################################################################################


if __name__ == '__main__':
	print("Calling From Main")
	a = getserial()
	print(a)
	"""print(internet_on())
	a = BIKEDATA()
	print(a.DATA)
	a.DATA.update({"lat": 121.000068})
	print(a.DATA)

	a.save()
	a.load()"""
