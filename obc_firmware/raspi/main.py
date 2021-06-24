
#Import ALL Configurations
import config
config.loggingSetup()
import logging
logger = logging.getLogger('MAIN')


import time, os
from threading import Timer
import errno
from socket import error as socket_error


from mqtt import mqtt_feed

if config.isRaspi():
	print("Importing Others")
	import gps_client
	if config.SCOOTER:
		import sensors
		print("\n\n\nUSING E-SCOOTER\n\n\n")
		import smartlock_scooter as smartlock
		time.sleep(1)
	else:
		import smartlock_bike as smartlock
	#from smartlock import SMARTLOCK
	import RPi.GPIO as GPIO
	import tamper
	#os.system("clear")
	print("Done Importing")






"""
Full System
Initialize All Funcs
Run all Threads

"""
def MQTTOnline(mqttc):
	if mqttc.status == "CONNECTED":
		return 0

	print("MQTT Broker Status: \tWaiting .", end = '')
	count  = 1
	total = 0
	while mqttc.status != "CONNECTED":
		count += 1
		state = count % 3
		if state == 1:
			print("\rMQTT Broker Status: \tWaiting .  ", end = '')
		elif state == 2:
			print("\rMQTT Broker Status: \tWaiting .. ", end = '')
		elif state == 3:
			print("\rMQTT Broker Status: \tWaiting ...", end = '')
		time.sleep(0.25)
		if (count / 4) >= (30):
			mqttc.smartlock.lock()

	return 0





class fullSystem():
	def __init__(self):
		#Initialize Threads and their Functions
		if config.isRaspi():
			self.gpsc = gps_client.gpsc()
			#self.gpsc = gps_client.GPS_CLIENT()
			#self.gpsc.start()

			self.smartlock = smartlock.slc()
			#self.smartlock = SMARTLOCK()
			#self.smartlock.start()
			if config.SCOOTER:
				self.sensors = sensors.sensorsc()
			else:
				self.sensors = None
			self.tamper = tamper.tamperc()
		else:
			self.gpsc = None
			self.smartlock = None
			self.sensors = None
			self.tamper = None

		self.mqttc = mqtt_feed(gpsc = self.gpsc,SL = self.smartlock, sensors = self.sensors, tamper = self.tamper)
		self.mqttc.start()
		self.ALIVE = True

	def restart():
		#exit()
		return

	def main(self):

		strinput = "No"
		strtemp = "aaa"
		self.ALIVE = True

		#Runnning Loop
		while self.ALIVE:
			logging.debug("Starting Full System")
			try:
				#
				MQTTOnline(self.mqttc)
				self.mqttc.data["Closing"] = False

				#main system

				#Exit conditions
				while strinput != "STOP":# Start once and Stops if properly stopped only
					if self.mqttc == 1:
						strinput = "STOP"
					else:
						strtemp = input("\nType \"stop\" to Stop\n(Case Not Sensitve):\n").upper()
						print(strtemp)
						if strtemp == "STOP":
							strtemp = input("Confirm? (Y/N)").upper()
							if strtemp == "Y":
								strinput = "STOP"
								break
							else:
								print("Continued")


				self.mqttc.data["Closing"] = True
				self.mqttc.report()
				self.ALIVE = False





			except (KeyboardInterrupt, SystemExit): #when you press ctrl+c
				print("Interrupted")
				print ("\nKilling Thread...")
				#gpsc.join() # wait for the thread to finish what it's doing

				#Remove on Final
				self.ALIVE = False

			#Exception For GPSD Errors
			except socket_error as serr:
				content = str(serr)
				print("ERROR Content:", content)

				#GPS Problems
				if content == "[Errno 111] Connection refused":
					#print(serr.errno)
					gps_client.gpsdReset()


				#I2C problems
				elif content == "[Errno 121] Remote I/O error":
					print("Please Check Device Connections")
					self.ALIVE = False
				else:
					print(serr)

			except Exception as e:
				print (e)

			finally:
				self.mqttc.stop()
				if config.isRaspi():
					self.gpsc.stop()
					self.smartlock.stop()
					self.sensors.stop()
					self.tamper.stop()

					if config.DEBUGGING:
						print("Waiting For SMARTLOCK to STOP")
					self.smartlock.join()
					if config.DEBUGGING:
						print("SmartLock Closed Properly")

				logger.info("Program Closed Properly")
				print('You can close the window now')

def main():
	os.system('clear')
	logger.info('\n\nSystem Started\n')
	a = fullSystem()
	a.main()


if __name__ == "__main__":
	for i in range(1,20):
		print(i)
		time.sleep(1)
	main()
