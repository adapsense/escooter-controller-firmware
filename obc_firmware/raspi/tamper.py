import time
import board
import threading
import RPi.GPIO as GPIO
import config
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

def tamperc():
	tamperc = TAMPER_CLIENT()
	tamperc.start()
	return tamperc

class TAMPER_CLIENT(threading.Thread):
	def __init__(self):
		threading.Thread.__init__(self,daemon = True)
		self.name = "Thread: Tamper"
		self.ALIVE = True
		self.interval = config.watchdog_period
		self.watchdog = 6
		self.ebrakeTMP = 20
		self.powerTMP = 21
		self.enclosureTMP = 16
		self.ebrakeFlag = False
		self.powerFlag = False
		self.enclosureFlag = False
		
		GPIO.setup(self.ebrakeTMP,GPIO.IN,pull_up_down=GPIO.PUD_UP)
		GPIO.setup(self.powerTMP,GPIO.IN,pull_up_down=GPIO.PUD_UP)
		#GPIO.setup(self.enclosureTMP,GPIO.IN,pull_up_down=GPIO.PUD_DOWN)
		
		GPIO.setup(self.watchdog,GPIO.OUT)
		GPIO.output(self.watchdog,1)
		
		GPIO.remove_event_detect(self.ebrakeTMP)
		GPIO.add_event_detect(self.ebrakeTMP, GPIO.BOTH, callback = self.ebrakeAlert)
		
		GPIO.remove_event_detect(self.powerTMP)
		GPIO.add_event_detect(self.powerTMP, GPIO.BOTH, callback = self.powerAlert)
		
		#GPIO.remove_event_detect(self.enclosureTMP)
		#GPIO.add_event_detect(self.enclosureTMP, GPIO.BOTH, callback = self.enclosureAlert)
	
	def ebrakeAlert(self,arg):
		self.ebrakeFlag = GPIO.input(self.ebrakeTMP)
	
	def powerAlert(self,arg):
		self.powerFlag = GPIO.input(self.powerTMP)
	
	def enclosureAlert(self,arg):
		self.enclosureFlag = GPIO.input(self.enclosureTMP)
		
	def ebrakeNormal(self):
		self.ebrakeFlag = False
	
	def powerNormal(self):
		self.powerFlag = False
	
	def enclosureNormal(self):
		self.enclosureFlag = False
	
	def stop(self):
		print("Tamper Thread Stopping Please Wait")
		self.ALIVE = False
	
	def run(self):#What Happens inside the Thread
		print("Thread Started")
		while self.ALIVE:
			#print("self.ebrakeFlag: ",self.ebrakeFlag)
			#print("self.powerFlag: ",self.powerFlag)
			#print("self.enclosureFlag: ",self.enclosureFlag)
			GPIO.output(self.watchdog,0)
			time.sleep(self.interval/2)
			GPIO.output(self.watchdog,1)
			time.sleep(self.interval/2)
		print("Sensor Thread STOPPED")

def main():
	tamperp = tamperc()
	print("Main Loop Start")
	while True:
		print(tamperp.data)
		time.sleep(0.5)

if __name__ == '__main__':
	main()
