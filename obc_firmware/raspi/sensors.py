import time
import board
from subprocess import Popen, STDOUT, PIPE
import json
import pty
import os
from statistics import median
import threading

def sensorsc():
	sensorsc = SENSOR_CLIENT()
	sensorsc.start()
	return sensorsc

class SENSOR_CLIENT(threading.Thread):
	def __init__(self):

		threading.Thread.__init__(self,daemon = True)
		self.name = "Thread: Sensor BME"
		self.ALIVE = True
		self.interval = 1
		self.Temperature = 0.0
		self.Humidity = 0.0
		self.Pressure = 0.0
		self.Altitude = 0.0
		self.IAQ = 0.0

		self.data = {}
		
		master, slave = pty.openpty()
		bsec = Popen(['./bsec_bme680/bsec_bme680'], shell=True, stdout=slave, stderr=slave, close_fds=True)

		self.stdout = os.fdopen(master)
		line = self.stdout.readline()

	def stop(self):
		print("Sensors Thread Stopping Please Wait")
		self.ALIVE = False

	def run(self):#What Happens inside the Thread
		print("Thread Started")
		listIAQ_Accuracy = []
		listPressure = []
		listGas = []
		listTemperature = []
		listIAQ = []
		listHumidity = []
		listStatus = []
		while self.ALIVE:
			time.sleep(self.interval)
			line = self.stdout.readline()
			if (line != '') and (line[0] == "{"):
				lineJSON = json.loads(line)
				lineDict = dict(lineJSON)
				
				listIAQ_Accuracy.append(int(lineDict['IAQ_Accuracy']))
				listPressure.append(float(lineDict['Pressure']))
				listGas.append(int(lineDict['Gas']))
				listTemperature.append(float(lineDict['Temperature']))
				listIAQ.append(float(lineDict['IAQ']))
				listHumidity.append(float(lineDict['Humidity']))
				listStatus.append(int(lineDict['Status']))
				
				if len(listIAQ_Accuracy) == 2:
					#generate the median for each value
					self.IAQ_Accuracy = median(listIAQ_Accuracy)
					self.Pressure = median(listPressure)
					self.Gas = median(listGas)
					self.Temperature = median(listTemperature)
					self.IAQ = median(listIAQ)
					self.Humidity = median(listHumidity)
					self.Status = median(listStatus)
					
					#clear lists
					listIAQ_Accuracy.clear()
					listPressure.clear()
					listGas.clear()
					listTemperature.clear()
					listIAQ.clear()
					listHumidity.clear()
					listStatus.clear()
					
					#Temperature Offset
					self.Temperature = self.Temperature + 2
					self.Altitude = 44330.0 * (1.0 - ((self.Pressure /1013.25)**0.1903))
			
					self.data['Temperature']= "%0.1f C" % self.Temperature
					self.data['IAQ']= "%0.2f " % self.IAQ
					self.data['Humidity']= "%0.1f %%" % self.Humidity
					self.data['Pressure']= "%0.3f hPa" % self.Pressure
					self.data['Altitude']= "%0.2f meters" % self.Altitude
		print("Sensor Thread STOPPED")
def main():
	sensorsp = sensorsc()
	print("Main Loop Start")
	while True:
		print(sensorsp.data)
		time.sleep(0.5)


if __name__ == '__main__':
	main()
