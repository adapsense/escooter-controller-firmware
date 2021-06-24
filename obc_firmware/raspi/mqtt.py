#Import Setup Configurations
import config
config.loggingSetup()

#Setup Logging Function
import logging
logger = logging.getLogger('MQTT')

from csv import DictWriter,writer

#Functions Needed for this File
import math
import paho.mqtt.client as paho
import time,os	#Sleep and other os config
import datetime	#Time Stamp
import threading
import psutil
from json import dumps as jdumps

DATA_PATH = 'log/gps_sensor_data.csv'
USAGE_PATH = 'log/data_usage.csv'

mode = 'a' if os.path.exists(DATA_PATH) else 'w'

#Functions Needed for RaspberryPi Run
if not config.isPC:
	try:
		import gps_client
		if config.SCOOTER:
			import smartlock_bike as smartlock
		else:
			import smartlock2 as smartlock

	except Exception as e:
		logging.error("Error @: MQTT importing Smartlock")
		logging.error(e)

##################################################

#List of Subscription Prefix
#Add BIKECODE to last part
mqtt_topics = ["lock/", "unlock/","alarm/","location/"]

#List of Ignore List
#Content will still be Received, but will not be processed
IGNORE_ARRAY = ["ACK","lat"]

DEFAULT_BIKECODE = "UPD-000"

#Subscription Status
SubbedOnce = False
CONNECTED = "CONNECTED"
DISCONNECTED = "DISCONNECTED"
PENDING = "PENDING"

report_time = config.default_report_time

##################################################

#CallBack Functions
#Should be Fast and MUST not block thread >5 seconds
def on_connect(client, userdata, flags, rc):
	global SubbedOnce
	error_list = []
	#If Connection is Successful
	if rc==0:
		print('MQTT Client Connected')
		os.system('clear')
		#Log Connection
		logger.info("\rMQTT Broker Status: \tConnected")
		#Set status
		userdata.status = CONNECTED
		"""print("Test Output")
		try:
			print(SubbedOnce)
		except Exception as e:
			print(e)
		#print(SubbedOnce,config.MQTT_CLEAN_SESSION)
		print("Test Output")"""
		#Not Clean MQTT Session, Subcribe Once Only Since Persistent
		#condNotSubbedandClean = ((SubbedOnce == False) and (config.MQTT_CLEAN_SESSION == False))
		#Subcribe to Stuff
		if (SubbedOnce == False) or (config.MQTT_CLEAN_SESSION == True):
			#Get Subscription List from Generator
			subList = userdata.subList()
			print("Topics to subscibe:\t",end = '')
			for subTopic in subList:
				try:
					print(subTopic, end = ", ")
					client.subscribe(subTopic)
				except Exception as e:
					logger.error("Subscribing Error for Topic:  \"{:s}\"".format(subTopic))
					error_list.append(subTopic)
				#Subcribe Done
				if config.DEBUGGING:
					print(subTopic, "OK")
			print('')
			#Check if There Was a Subscription Error
			if len(error_list) > 0:
				logger.error("Subscribing Error: Cannot Connect to:\n{elist}".format(elist = error_list))
			else:
				SubbedOnce = True
				logger.info("\nSubscription Completed\n")
	else:
		logging.error("Bad connection \t\tReturned code=%d"%(rc))

def on_disconnect(client, userdata, rc):
	if rc == 0:
		logging.info("MQTT Disconnected Properly")
	else:
		print(('\n'+ "DISCONNECTED\t"*5 + '\n') * 5)
		logging.error("MQTT Disconnected Unexpectedly")

def on_message(client, userdata, message):
	#Decode Message Content
	content = message.payload.decode("utf-8")
	#Check if Command is Sent and Clear UI
	if ("<" in content) and (">" in content):
		os.system('clear')
	#if config.DEBUGGING:
	#print("\n\nFrom:\t\t\t%s\nMessage:\t\t%s" % (message.topic, message.payload.decode("utf-8")))
	#print('ON Message Commanding')
	#Call Message Handler Function
	userdata.command(message)
	#print('ON Message Completed')

def on_publish(client,userdata,mid):
	#print('\n\n\n\n',max(userdata.midList),'\n\n\n\n')
	#Get POsition of mid in midList
	try:
		pos = userdata.midList.index(mid)
	except Exception:
		pos = 0
	#Remove queue items until MID
	if mid > max(userdata.midList):
		userdata.midList = []
	else:
		userdata.midList = userdata.midList[pos:]

####################################################################################################

class mqtt_feed(threading.Thread):
	def __init__(self, code = DEFAULT_BIKECODE, SL = None,gpsc = None, sensors = None, tamper = None):

		def load_specs():
			#Get Data from config file
			self.SPECS = config.BIKEDATA()
			self.data = self.SPECS.DATA
			if config.DEBUGGING:
				print("\n\nSpecs in Specs Files:\n", self.data)
				print("Name from Specs File:\t", self.data["name"])
			#BIKE NAME/ CODE
			self.BIKECODE = code
			self.BIKECODE = self.data['name']
			"""
			if self.data["name"] != BIKECODE:
				if BIKECODE == "UPD-000":
					self.BIKECODE = self.data["name"]
				else:
					print("Error in Name ", BIKECODE,"vs",self.data["name"])
					#self.BIKECODE = BIKECODE
			else:
				self.BIKECODE = self.data["name"]"""

		def GPSnSL():
			#Checking If Testing on RASPI
			if config.RASPI:
				#GPS Function Import
				if gpsc != None:
					if config.DEBUGGING:
						print("\nGPSC Received")
					self.gps = gpsc
				else:
					print("\nInitiating OWN GPSC Instance")
					self.gps = gps_client.gpsc()
						#self.gps = gpsc
						#self.gps.start()
				if SL != None:
					if config.DEBUGGING:
						print("\nSmartlock Received")
					self.smartlock = SL
				else:
					print("Initializing Own SmartLock instance")
					self.smartlock = smartlock.slc()
					#self.smartlock = smartlock.SMARTLOCK()
					#self.smartlock.start()
				if sensors != None:
					self.sensors = sensors
				else:
					self.sensors = None
				if tamper != None:
					self.tamper = tamper
				else:
					self.tamper = None
                                    
			#If Not raspberry
			else:
				print("Not Using Raspberry Pi")
				#No GPS and I2C for NON raspi
				if config.DEBUGGING:
					print("\tIgnoring GPS and SMARTLOCK")
				self.gps = None
				self.smartlock = None
				self.sensors = None
				self.tamper = None

		def MQTT_inits():
			self.reportTimeStamp = None
			self.measureTimeStamp = datetime.datetime.now()
			# Start MQTT Client
			#self.mqttc = paho.Client(client_id="",clean_session = True, userdata = self, protocol=paho.MQTTv311)
			self.mqttc = paho.Client(client_id=self.BIKECODE,clean_session = config.MQTT_CLEAN_SESSION, userdata = self, protocol=paho.MQTTv311,transport="websockets")
			self.status = PENDING
			#SubbedOnce = False
			#define MQTT Callbacks
			self.mqttc.on_connect=on_connect
			self.mqttc.on_message=on_message
			self.mqttc.on_publish=on_publish
			#SET RECONNECT PARAMETERS
			self.mqttc.reconnect_delay_set(min_delay=1, max_delay=config.MAX_DOWNTIME)
			#set WILL message incase of Unexpected Disconnection after MAX_DOWNTIME
			self.mqttc.will_set(("connection/" + self.BIKECODE), payload = "{!!!!!IMPROPER!!!!!}")
			#Define MQTT sub topics
			#Topic with Most ACtion
			self.maintopic = "location/" + self.BIKECODE
			self.createSubList()
			self.midList = []
			self.totalUsage = psutil.net_io_counters(nowrap=True).bytes_sent

		def thread_init():
			#self.thread = threading.Thread.__init__(self,daemon = False)
			threading.Thread.__init__(self,daemon = False)
			self.name = "Thread: MQTT Report"
			self.ALIVE = False
			self.interval = config.reportInterval

		def reload_lock():
			pass

		load_specs()
		GPSnSL()
		MQTT_inits()
		thread_init()
		trials = 10
		while trials >0:
			try:
				self.connect()
				break
			except Exception as e:
				trials -= 1
		#Start Thread That Receives Messages
		self.mqttc.loop_start()
		self.prev_lat = 0
		self.prev_long = 0
		self.data_count = 0
		self.prev_status = "L"
		#self.maintopic_buffer = []
		self.data_buffer = []
		self.field_names = ['datetime','Latitude','Longitude','Temperature','Humidity','Pressure','IAQ','Altitude']
		self.DATA_PATH = DATA_PATH
		self.USAGE_PATH = USAGE_PATH
		self.alarmFlag = False
		if not os.path.exists(self.DATA_PATH):
			with open(self.DATA_PATH, 'a+', newline='') as write_obj:
				# Create a writer object from csv module
				csv_writer = writer(write_obj)
				# Add contents of list as last row in the csv file
				csv_writer.writerow(self.field_names)
		reload_lock()

	def __enter__(self):# called using with statement
		return self

	def connect(self):
		if config.DEBUGGING:
			print("Staring MQTT Link\nBIKECODE = \t\t%s"%(self.BIKECODE))
		if config.isOnline():
			logger.info("Connecting to: {:>30s}:{:<5d}".format( config.broker_ip ,config.broker_port))
			try:
				self.mqttc.tls_set()
				self.mqttc.ws_set_options(path=config.broker_path)
				self.mqttc.username_pw_set(config.broker_username,password = config.broker_password)
				self.mqttc.connect(config.broker_ip,port = config.broker_port)#connect
				#self.mqttc.loop_forever()
				return 0
			except Exception as e:
				#print("Error @:")
				print("Error @:MQTT connect")
				print(e)
		else:
			logger.error("No Internet connection detected")
			if self.smartlock != None:
				logger.info("Lock Override Initiated")
				self.smartlock.lock(override = True)
			raise Exception("Internet Connection ERROR")

	def subList(self):
		return self.topics

	def createSubList(self,topics = mqtt_topics):
		#self.BIKECODE = 'UPD-000'
		#Reset Topics List
		self.topics = topics
		logger.debug("BIKE ID= %s" % (self.BIKECODE))
		logger.debug("Subscribing to:")
		#Make combine topics with Bikename
		for i,tpic in enumerate(topics):
			self.topics[i] = tpic + self.BIKECODE
			logger.debug(self.topics[i])

	def run(self):
		def tamper_handler():
			print("Tamper breached!")
			if self.tamper.ebrakeFlag:
				self.reportAlarm("ebrake")
			if self.tamper.powerFlag:
				self.reportAlarm("power")
				report_time = config.lowpower_report_time
			if self.tamper.enclosureFlag:
				self.reportAlarm("enclosure")
			if tamper_triggered == False: #Start of tamper
				self.prev_status = self.smartlock.DeviceCode
				self.orderSmartlock("<LOCK>")
				time.sleep(1)
			else:
				self.orderSmartlock("<ALARM>")

		def tamper_reset():
			report_time = config.default_report_time
			if self.prev_status == "U":
				self.orderSmartlock("<UNLOCK>")
			elif self.prev_status == "A":
				self.orderSmartlock("<ALARM>")
			else:
				self.orderSmartlock("<LOCK>")
			print("Tamper reset!")

		self.ALIVE = True
		tamper_triggered = False
		#While not connected
		while self.status != CONNECTED:
			pass
		#while gps is connected but not active
		while (self.gps != None) and (not self.gps.ALIVE):
			pass
		#Main Loop
		while self.ALIVE:
			if self.tamper.ebrakeFlag or self.tamper.powerFlag or self.tamper.enclosureFlag:
				tamper_handler()
				tamper_triggered = True
			elif tamper_triggered:
				tamper_reset()
				tamper_triggered = False
			elif self.alarmFlag:
				self.orderSmartlock("<ALARM>")
			if self.status == "CONNECTED":
				#Report to Server Every Interval
				#self.data['lock_status'] = self.smartlock.DeviceCode
				self.report()
				measureTime = (datetime.datetime.now() - self.measureTimeStamp).seconds / 60
				if measureTime > config.measure_time:
					publishUsage = psutil.net_io_counters(nowrap=True).bytes_sent - self.totalUsage
					self.totalUsage = self.totalUsage + publishUsage
					self.measureTimeStamp = datetime.datetime.now()
					with open(self.USAGE_PATH, 'a+', newline='') as write_obj:
						# Create a writer object from csv module
						usage_fields = ['datetime','usage']
						csv_writer = DictWriter(write_obj, fieldnames=usage_fields)
						# Add dictionary in the csv
						csv_writer.writerow({'datetime': datetime.datetime.now().isoformat(' '), 'usage': publishUsage})
						print("*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=")
						print("Time: ",datetime.datetime.now().isoformat(' ')," Sent (B): ",publishUsage)
						print("*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=")
				#Check if report Reached Server
				#print("MID List Size:%d" % len(self.midList), end = '')
				if len(self.midList)>config.maxReportsFailed:
					print("Auto lock triggereed\nAuto lock triggereed\nAuto lock triggereed\nAuto lock triggereed\nAuto lock triggereed\nAuto lock triggereed\nAuto lock triggereed\nAuto lock triggereed\nAuto lock triggereed\nAuto lock triggereed\nAuto lock triggereed\n")
					self.smartlock.lock()
				#self.report()
			time.sleep(self.interval)

	def pause(self,pause = True):
		if pause:
			print("Pausing")
			self.mqttc.loop_stop()
		elif not pause:
			print("Unpausing")
			self.mqttc.loop_start()

	def __exit__(self, *a):
		self.stop()

	def disconnect(self):
		self.mqttc.disconnect() #disconnect

	def stop(self):
		self.ALIVE = False
		self.SPECS.save()
		for topic in self.topics:
			self.mqttc.publish(topic,"{\"name\":\""+self.BIKECODE+"\",\"message\":\"STOPPING\",\"lock_status\": \"L\"}")
		logger.info("Closing MQTT for %s" % (self.BIKECODE))
		self.disconnect()
		self.mqttc.loop_stop() #stop loop
		logger.info("Closed MQTT for %s" % (self.BIKECODE))

	def orderSmartlock(self, order):
		print('\n\n Order Recieved\n\n\n', order)
		if self.smartlock != None:
			if order == "<ALARM>":
				self.smartlock.alarm()
			elif order == "<UNLOCK>":
				self.smartlock.unlock(True)
			elif order == "<LOCK>":
				self.smartlock.lock(True)
			elif order == "<DISABLE>":
				print('Sent disable')
				self.smartlock.disable()
			else:
				logger.log("Error {:s} invalid order".format(order))
		else:
			print("SMARTLOCK Function Not Integrated")

	def reportAlarm(self,tamper):
		print('\n Reporting Alarm\n',tamper)
		if tamper == "ebrake":
			self.mqttc.publish(("tamper/" + self.BIKECODE),"{\"name\":\""+self.BIKECODE+"\",\"message\":\"ALARM EBRAKE\"}")
		elif tamper == "power":
			self.mqttc.publish(("tamper/" + self.BIKECODE),"{\"name\":\""+self.BIKECODE+"\",\"message\":\"ALARM POWER\"}")
		elif tamper == "enclosure":
			self.mqttc.publish(("tamper/" + self.BIKECODE),"{\"name\":\""+self.BIKECODE+"\",\"message\":\"ALARM ENCLOSURE\"}")

	def command(self,message):
		#Receives Commands and Directs them to proper functions
		#Decode Message Content
		content = message.payload.decode("utf-8")
		def sendACK():
			print("\nReceived",content,"Command")
			#Acknowledge Command Received but Not Yet Done
			self.mqttc.publish("presence","command\n"+content+"\nreceived")
			#Acknowledge Command Completed
			if content == "<UNLOCK>":
				self.mqttc.publish(message.topic,"{\"name\":\""+self.BIKECODE+"\",\"message\":\"UNLOCK ACK\"}")
			elif content == "<LOCK>":
				self.mqttc.publish(message.topic,"{\"name\":\""+self.BIKECODE+"\",\"message\":\"LOCK ACK\"}")
			elif content == "<ALARM>":
				self.mqttc.publish(message.topic,"{\"name\":\""+self.BIKECODE+"\",\"message\":\"ALARM ACK\"}")
			elif content == "<DISABLE>":
				print("ADD DISABLE Function")
				self.mqttc.publish(message.topic,"{\"name\":\""+self.BIKECODE+"\",\"message\":\"DISABLE ACK\"}")
				print("STOPPING CURRENT ACTIVITY")
			elif content == "<RESTART>":
				print("ADD Restart Function")
				self.mqttc.publish(message.topic,"{\"name\":\""+self.BIKECODE+"\",\"message\":\"RESTART ACK\"}")
				print("Restarting ")
			elif content == "<REQUEST>":
				print("\nLOCATION REQUESTED")
				self.mqttc.publish("presence","command\n"+content+"\nreceived")
			else:
				self.mqttc.publish("presence","command\n"+content+"\nreceived")
				print("Error ACK Unkown\nError ACK Unkown\nError ACK Unkown\nError ACK Unkown\nError ACK Unkown\nError ACK Unkown")
			if config.DEBUGGING:
				print("ACK's Sent Returning")
			self.report(True)
		if (content == "<ALARM>") and ("alarm/" in message.topic):
			print("ALARM\tALARM\tALARM\tALARM\tALARM\nALARM\tALARM\tALARM\tALARM\tALARM\nALARM\tALARM\tALARM\tALARM\tALARM\nALARM\tALARM\tALARM\tALARM\tALARM\n")
			self.orderSmartlock(content)
			self.alarmFlag = True
			sendACK()
		elif (content == "<UNLOCK>") and ("unlock/" in message.topic):
			self.orderSmartlock(content)
			self.alarmFlag = False
			sendACK()
		elif (content == "<LOCK>") and ("lock/" in message.topic) and ("unlock" not in message.topic):
			self.orderSmartlock(content)
			sendACK()
		elif content == "<DISABLE>":
			self.orderSmartlock(content)
			sendACK()
		elif content == "<REQUEST>":
			print("\nLOCATION REQUESTED")
			self.mqttc.publish("presence","command\n"+content+"\nreceived")
			self.report(True)
			sendACK()
		elif content == "<RESTART>":
			self.orderSmartlock("<LOCK>")
			print("\nReset Requested REQUESTED")
			self.mqttc.publish("presence","command\n"+content+"\nreceived")
			self.report(True)
			time.sleep(10)
			os.system("sudo reboot now")
			sendACK()
		else:
			#Ignore All Messages with Content Listed to Ignore
			if all(elem not in content for elem in IGNORE_ARRAY):
				self.mqttc.publish("presence","ERROR\n"+content+"\nNot Recognized")
			else:
				#Uncomment to print Out ALL received unidentified Message
				if ["<",">"] in content:
					print("Received Unidentified Command:", content)
				else:
					pass
		if config.DEBUGGING:
			print("Message Processing Completed")

	def measure(self, lat1, lat2, lon1, lon2):
		R = 6378.137 #Radius of earth in KM
		dLat = math.radians(lat2 - lat1)
		dLon = math.radians(lon2 - lon1)
		a = math.sin(dLat/2)**2 + (math.cos(math.radians(lat1))*math.cos(math.radians(lat2))*(math.sin(dLon/2)**2))
		d = R*2000*math.atan2(math.sqrt(a),math.sqrt(1-a))
		return d #in meters

	def decideReport(self, data):
		reportTime = (datetime.datetime.now() - self.reportTimeStamp).seconds / 60
		if math.isnan(self.data["lat"]) or math.isnan(self.data["long"]):
			print("GPS is Nan")
			if (reportTime > config.noGPS_report_time) and (self.data_count == 0):
				self.data_buffer.append(data.copy())
				self.data_count = 1
				self.data['message'] = 'No GPS'
				return True
			elif (reportTime > report_time) and (self.data_count > 0):
				return True
			else:
				return False
		else:
			print("Report time elapsed: ",reportTime, " Limit: ",report_time)
			if reportTime > report_time:
				if self.data_count < 1:
					self.data_buffer.append(data.copy())
					self.data_count = 1
				print("Now reporting")
				return True
			else:
				distance = self.measure(self.prev_lat, self.data["lat"], self.prev_long, self.data["long"])
				self.prev_lat = self.data["lat"]
				self.prev_long = self.data["long"]
				if distance < config.min_movement:
					print("Not Moving")
				else:
					print("Buffering Data ", self.data_count)
					print("Data: ", data)
					self.data_buffer.append(data.copy())
					if self.data_count < (config.max_sample-1):
						self.data_count = self.data_count + 1
					else:
						self.data_buffer.pop(0)
				return False

	def report(self,forceReport=False):
		#Check if Initial Report
		if self.reportTimeStamp == None:
			self.reportTimeStamp = datetime.datetime.now()
		#If not Initial Report
		else:
			#Check Last Report Timeout Reached
			if (datetime.datetime.now() - self.reportTimeStamp).seconds > 60*60:
				os.system("clear")
				logger.error("Error Connection Should be Restarting")
		time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
		#Check if Connected to MQTT Server
		if self.status == CONNECTED:
			#Update Data TimeStamp
			self.data.update(time = time)
			#GPS
			#If Testing With PC OR NO GPS CLIENT DETECTED
			if self.gps == None:#
				logger.debug("No GPS Client Detected")
				self.data["lat"], self.data["long"] = 12.00124201, 121.223424 #"TEST LAT" , "TEST LONG"
			else:
				self.data["lat"], self.data["long"] = self.gps.coordinates()
			#Smartlock
			#If Testing With PC OR NO SMARTLOCK Process Detected
			if self.smartlock == None:
				logger.debug("No SmartLock Client Detected")
				self.data["lock_status"] = "U"
				pass
			else:
				self.data["lock_status"] = self.smartlock.DeviceCode
			#sensors
			if self.sensors == None:
				pass
			else:
				self.data.update(self.sensors.data)
				with open(self.DATA_PATH, 'a+', newline='') as write_obj:
					# Create a writer object from csv module
					dict_writer = DictWriter(write_obj, fieldnames=self.field_names)
					# Add dictionary in the csv
					dict_writer.writerow({'datetime': datetime.datetime.now().isoformat(' '), 'Latitude': self.data["lat"], 'Longitude': self.data["long"], 'Temperature': self.sensors.Temperature, 'Humidity': self.sensors.Humidity, 'Pressure': self.sensors.Pressure, 'IAQ': self.sensors.IAQ, 'Altitude': self.sensors.Altitude})
			try:
				if config.TEST:
					self.data['message'] = 'SIMULATOR'
			except:
				if self.tamper.ebrakeFlag or self.tamper.powerFlag or self.tamper.enclosureFlag:
					self.data['message'] = 'Tampered:'
					if self.tamper.ebrakeFlag:
						self.data['message'] = self.data['message'] + ' EBrake'
					if self.tamper.powerFlag:
						self.data['message'] = self.data['message'] + ' Power'
					if self.tamper.enclosureFlag:
						self.data['message'] = self.data['message'] + ' Enclosure'
				elif math.isnan(self.data["lat"]) or math.isnan(self.data["long"]):
					self.data['message'] = 'No GPS'
				else:
					self.data['message'] = 'LIVE'
			#Publish Data
			if forceReport:
                            self.data_buffer.append(self.data.copy())
                            decide = forceReport
			else:
                            decide = self.decideReport(self.data)
			if decide:
				result, mid = self.mqttc.publish(self.maintopic,(jdumps(self.data_buffer)) )
				self.midList.append(mid)
				self.data_buffer.clear()
				self.data_count = 0
				self.reportTimeStamp = datetime.datetime.now()
			return True
		else:
			logger.debug("Calling to Report\n\nBUT\n\nNot Connected to MQTT Server\n\n")
			return False

if __name__ == '__main__':
	with mqtt_feed() as b:
		while True:
			b.start()
			command = input("Enter Command with <>:")
			if "<" in command and ">" in command:
				b.mqttc.publish("location/UPD-000",command)
			else:
				if input("Exit? (Y/N)").upper() == 'Y':
					break
