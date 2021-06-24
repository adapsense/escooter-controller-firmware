
import smbus


from ina219 import INA219

from ina219 import DeviceRangeError
from socket import error as socket_error


import time
from queue import Queue



import config


import logging
logger = logging.getLogger('SMARTLOCK')


SHUNT_OHMS = 0.1
MAX_EXPECTED_AMPS = 2.0

LOCK_VOLTAGE = 2.5
UNLOCK_VOLTAGE = 1.5
CURRENT_MIN_ACTIVE = 20 #mA
CURRENT_MAX = 400 #mA
CURRENT_MAX_UNLOCK = 400 #mA
#CURRENT_MAX = 0.50 #mA
BUFFER_DELAY = 3 #Seconds from 1 Execution to Another


I2CBUS = 1 #RPI
OBC_ADD = 0X0d
LOCK_SENSOR_ADD  = 0x40
POWER_SENSOR_ADD = 0x44

ALARM = "A"
LOCK = "L"
UNLOCK = "U"
DONE = "D"#D to stop after disable

largespace = "                                                   \r"



"""
class Foo:
    def __init__(self):
        print('__init__ called')
    def __enter__(self):
        print('__enter__ called')
        return self
    def __exit__(self, *a):
        print('__exit__ called')#Reminder Code incase init enter exit confusion
"""



import RPi.GPIO as GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
import threading




# GPIO Thread
# Independent Monitoring and Response of IO's of Raspberry Pi
# Blinking Lights Means Action is still in progress
class raspIO(threading.Thread):

    def __init__(self,resetLenght = 20000, SL = None):
        self.smartlock = SL

        if config.DEBUGGING:
            print("Initializing Raspberry GPIO")

        self.thread = threading.Thread.__init__(self,daemon = True)
        self.name = "Thread: GPIO"
        self.resetLenght = resetLenght #milliseconds before program will start to reset
        self.ports = {}


        #Inputs
        self.PB = 17
        GPIO.setup(self.PB,GPIO.IN, pull_up_down = GPIO.PUD_UP)
        GPIO.remove_event_detect(self.PB)
        GPIO.add_event_detect(self.PB, GPIO.FALLING, callback = self.buttonpress,bouncetime = self.resetLenght)

        self.press = False
        self.pressCount = 0

        #Outputs
        """bikeself.wLED = 26
        self.rLED = 13
        self.gLED = 19"""

        self.wLED = 19
        self.rLED = 13
        self.gLED = 26

        self.wLED_ON = True
        self.rLED_ON = True
        self.gLED_ON = True

        self.wLED_BLINK = True
        self.rLED_BLINK = False
        self.gLED_BLINK = False

        GPIO.setup(self.rLED, GPIO.OUT)
        GPIO.setup(self.gLED, GPIO.OUT)
        GPIO.setup(self.wLED, GPIO.OUT)

        self.selfcheck()


    def run (self):
        count = 0
        def PB_HANDLER():
            print("Reset Button Has Been Pushed")
            self.press = False
            self.pressCount = self.pressCount + 1
            if self.pressCount == 5:
                print("\n\nRestart Triggered\n\n")
                #os.system("sudo reboot now")

        def LED_Manager(LED, ON, BLINK):
            """if config.VERBOSE:
                print("\rLED:ON",LED,ON,end = '    ')"""
            GPIO.output(LED,ON)

            if BLINK:
                ON = not ON
            return ON

        #Main System Indicators
        #White Light
        wLED_ON = True
        while True:
            #Check If Item Is Pressed
            if (self.press):
                PB_HANDLER()

            count += 1
            if count >= 4:
                #GPIO.setmode(GPIO.BCM)
                self.wLED_ON = LED_Manager(self.wLED,self.wLED_ON,self.wLED_BLINK)
                count = 1
            #print("RED: ", (self.rLED,self.rLED_ON,self.rLED_BLINK))
            self.rLED_ON = LED_Manager(self.rLED,self.rLED_ON,self.rLED_BLINK)
            self.gLED_ON = LED_Manager(self.gLED,self.gLED_ON,self.gLED_BLINK)

            time.sleep(0.25)


    # Inputs
    def buttonpress(self,arg):
        print(arg)
        self.press = True


    #Check All IOs of Raspi
    def selfcheck(self):
        t = .05
        #blinks LEDS until done
        for i in range(0,25):
            GPIO.output(self.rLED, 1)
            GPIO.output(self.gLED, 1)
            GPIO.output(self.wLED, 1)
            time.sleep(t)

            GPIO.output(self.rLED, 0)
            GPIO.output(self.gLED, 0)
            GPIO.output(self.wLED, 0)
            time.sleep(t*2)
            t = t = 0.01
        #print("self checking complete")

    #Lock Status Indicator
    def lock(self,blink = False):
        self.rLED_BLINK = blink
        self.rLED_ON = True
        #self.gLED_ON = False
        GPIO.output(self.rLED, self.rLED_ON)
        #GPIO.output(self.gLED, self.gLED_ON)

    #Unlock Status Indicator
    def unlock(self,blink = False):
        self.gLED_BLINK = blink
        self.rLED_ON = False
        self.gLED_ON = False
        GPIO.output(self.rLED, self.rLED_ON)
        GPIO.output(self.gLED, self.gLED_ON)

    def alarm(self,blink = False):
        #self.rLED_BLINK = blink
        self.gLED_BLINK = blink
        #self.rLED_ON = False
        self.gLED_ON = True
        #GPIO.output(self.rLED, self.rLED_ON)
        GPIO.output(self.gLED, self.gLED_ON)



def slc():
    slc = SMARTLOCK()
    slc.start()
    return slc



class SMARTLOCK(threading.Thread):
    def __init__(self):

        #Create Thread for smartlock Management
        #initialize self with thread pointer
        self.thread = threading.Thread.__init__(self,daemon = False)
        self.name = "Thread: SmartLock"
        self.q = Queue(maxsize=1)

        #Thread Items
        self.ALIVE = True
        self.acceptingJobs = False
        self.OVERRIDE_DISABLE = False
        self.OVERRIDE_COMMAND = False

        #self.initINA219()

        #Start connection with smartlock
        self.I2C = smbus.SMBus(I2CBUS)


        self.lockingStatus = "NONE"
        self.STATUS_LOCK = None

        self.STATUS_CHANGED = True
        self.prevState = 'D'
        self.DeviceCode = 'D'


        self.gpio = raspIO(SL = self)
        self.gpio.start()

    def initINA219(self):
        try:
            #calibrate INA219 HERE
            #load calibration data here
            self.lock_monitor = INA219(shunt_ohms=SHUNT_OHMS, max_expected_amps=MAX_EXPECTED_AMPS,address = LOCK_SENSOR_ADD)
            #self.lock_monitor = INA219(shunt_ohms=SHUNT_OHMS, address = LOCK_SENSOR_ADD)
            self.lock_monitor.configure(voltage_range=self.lock_monitor.RANGE_32V, gain = self.lock_monitor.GAIN_AUTO)
            self.setINA = True

        except socket_error as serr:
            content = str(serr)
            print(content)
            #I2C problems
            if content == "[Errno 121] Remote I/O error":
                print("Please Check Device INA219 Connection")
            else:
                print(serr)
            #exit()


#################################################################

    def __enter__(self):

        if config.isRaspi():
            return self
        else:
            print("Not Using Raspberry Pi")
            return None




#################################################################



    def __exit__(self, *a):
        self.stop()

    #Function to Call that Does All Closing Items
    def stop(self):
        print("Locking before exit")

        #Add Lock To Queue
        #Needed to shut off
        self.lock()

        #Disable Any Additional Jobs frrom Being accepted
        self.acceptingJobs = True

        #Kill Thread After Final Job is Completed
        self.ALIVE = False
        config.displayThreads()


        self.join()
        print("SMARTLOCK : LOCKED\n NOW CLOSING")

        #Turn off os and stop locking
        #GPIO.cleanup()

        #Turn off os but keep on locking
        self.gpio.wLED_ON = False
        self.gpio.wLED_BLINK = False
        time.sleep(0.3)

#################################################################
#Thread Functions


    def I2CLIVE_Thread(self):
        code = 'None'
        def resetTimer():
            self.Live = threading.Timer(1,self.I2CLIVE_Thread)
            self.Live.daemon = True
            self.Live.name = "Timer: I2C Live"
            self.Live.start()
        def printCode(c):
            print("\rLock:", c, end = "  ")

        def updateLED():
            if self.DeviceCode is not None:
                code = self.DeviceCode
                if (code == '*'):
                    pass

                else:
                    code = code.upper()
                    #printCode(code)

                if code == 'L':
                    """
                    if self.setINA:
                        self.setINA = False"""
                    #self.gpio.lock()
                    #printCode(code)
                elif code == 'U':
                    """
                    if self.setINA:
                        self.setINA = False"""
                    #self.gpio.unlock()
                    #printCode(code)
                elif code == 'A' or code == '!':
                    #self.gpio.alarm()
                    """
                    if self.setINA:
                        self.setINA = False"""
                    #printCode(code)
                elif code == 'D' or '*':
                    #print("\rSMARTLOCK Fresh Start:\t", end = '')
                    if self.STATUS_LOCK == False:
                        self.disable()
                        #self.STATUS_LOCK = True
                        #self.unlock()
                        return
                    elif self.STATUS_LOCK == True:
                        self.disable()
                        self.STATUS_LOCK = False
                        #self.lock()
                    #else:
                    #   print("\tNo Locking Setup Detected",end = '')
                else:

                    print("\n\n\nDevice Code Error: %s\n\n\n" % (code))


        if self.ALIVE:
            resetTimer()
            updateLED()



    def run(self):
        self.ALIVE = True
        def worker(job):
            if job == ALARM:
                self.alarmSeq()
            elif job == LOCK:
                self.lockSeq()
            elif job == UNLOCK:
                self.unlockSeq()
            elif job == DONE:
                self.disableSeq()
            else:
                print("Error Code:", job)

        #Start Second Thread
        self.I2CLIVE_Thread()

        #While ALIVE or Queue is not Empty
        while self.ALIVE or not self.q.empty():
            job = self.q.get()
            if job is not None:
                #Remove Job from Queue
                self.q.task_done()
                if config.DEBUGGING:
                    print("SMARTLOCK New Job")
                worker(job)
                time.sleep(3)

        print("NOT ALIVE I2C THREAD")
        print("NOT ALIVE I2C THREAD")
        print("NOT ALIVE I2C THREAD\n\n\n")


        print("Locking @ Thread Closing")
        self.lockSeq()
        print("Locking Complete Now Closing")




#################################################################



    #Get Current Lock Code
    def getDeviceCode(self, silent = False):
        try:


            return self.DeviceCode

        except Exception as e:
            self.setINA = False
            logger.exception('Error occurred while Getting Device Code ' + str(e))
            print("\n\n\n\nRemote I/O Error: Attiny85 Not Responding Properly\n\n\n",e)
            return 'DISCONNECTED'

    def getLockStatus(self,fromME = False):
        #Gets Current Lock Status ONLY
        if config.DEBUGGING:
            print("Checking Lock Status")

        try:
            #Get Device Last Executed Command
            currentCode = self.DeviceCode
            #Return Device Codes
            return currentCode

        except Exception as e:
            print(e)
            return "Device Connection ERROR"



    #Sends Device Command to the SmartLock Controller
    def sendCommand(self,order = None):
        #receives letter and sends utF 8  equivalent
        if config.VERBOSE:
            print("Sending Order:",order)

        try:
            #self.I2C.write_byte(OBC_ADD,ord(order))
            print("\r\t Sent:", order,'\t', end = '')
            return True
        except Exception as e:
            print(e)
            return False





    def getCurrent(self):

        try:
            #I = abs(self.lock_monitor.current())# Use Current for final Test
            I = self.lock_monitor.current()# Use Current for final Test

            V = self.lock_monitor.voltage()
            if config.VERBOSE:
                print("Voltage: %.2f " % (V), end = '\t')
                print("DriveCurrent mA: %.2f"% (I),end = '')
            else:
                print("\r\t\t\tV: %.2f\t I(mA): %.2f" % (V,I),end = '')
            #return I
            return abs(I)

        except DeviceRangeError as e:
            # Current out of device range with specified shunt resister
            print("\n\n",e)

            """
            print("Motor Voltage",self.lock_monitor.voltage())
            print("Motor Power",self.lock_monitor.power())
            print("Motor Current",self.lock_monitor.current())
            """


    def waitMotorMax(self,currentCode, maxCurrent = CURRENT_MAX):
        def waitcheck():
            read = self.getLockStatus()
            stopwait = False
            while not stopwait:
                read = self.getLockStatus()
                print("\r Code = %c <- %c"%(read,currentCode), end= '')
                if read != currentCode:
                    print("Errors\n\n")
                    try:
                        self.sendCommand(currentCode)
                        #print(read)
                        pass
                    except:
                        print('no\n\n\n')
                        time.sleep(1)

                read = self.getLockStatus()
                if read == currentCode:
                    stopwait = True

                time.sleep(0.5)
                #Wait for motor Current to Stabilize
            time.sleep(10)


        #waitcheck()



        count = 0

        driveCurrent = 50# self.getCurrent()


        start_time = time.time()
        total_count = 1

        #Wait for Current to Exceed Locking Current Value or not OVERRIDE_DISABLE
        """while driveCurrent < maxCurrent and (not self.OVERRIDE_DISABLE):# DEBGUG Change to >

            #Gap Between Checks
            time.sleep(.1)


            count = count + 1
            total_count = total_count + 1
            #Refresh Command incase Attiny85 Failures or Motor Driving Problems
            if (count > 50) or (driveCurrent < CURRENT_MIN_ACTIVE):
                read = self.getLockStatus()
                if read != currentCode:
                    waitcheck()
                    total_count = 0
                count = 0


            if total_count >= 50*10:
                driveCurrent = maxCurrent + 10"""


        print("")# For Debuggin Purposes



        #if driveCurrent >= maxCurrent or self.OVERRIDE_DISABLE:
            #print("Current Limit Reached Disabling")
        if self.OVERRIDE_DISABLE:
            print("Override Command Received\nOverride Command Received\nOverride Command Received")
            self.OVERRIDE_DISABLE = False

        sent = self.sendCommand(DONE)
        time.sleep(2)

        return


    def addQ(self, code):
        if self.acceptingJobs:
            print("NOT ACCEPTING COMMANDS ANYMORE")
            return
        else:
            while(self.q.full()):
                self.q.get_nowait()
                self.q.task_done()
            self.q.put(code)



    def disable(self):
        self.OVERRIDE_DISABLE = True
        self.addQ(DONE)
    def disableSeq(self):

        self.OVERRIDE_DISABLE = False
        sent = self.sendCommand(DONE)

    def alarm(self):
        self.addQ(ALARM)
    def alarmSeq(self):
        def beep(length):
            #Send Alarm Signal
            #self.I2C.write_byte(OBC_ADD,ord(ALARM))
            #print("A")
            time.sleep(length)
            #self.I2C.write_byte(OBC_ADD,ord(DONE))
            #print("")

        def wait(lenght):
            time.sleep(lenght)
        prevstatus = self.DeviceCode
        self.DeviceCode = ALARM
        a4 = beep
        R = wait
        f4 = beep
        c5 = beep
        e5 = beep
        f5 = beep
        g5 = beep
        def decodebeat(func, len):
            len = len/100
            func(len)
        def SW1(): #Star Wars Imperial March
            melody1 = [  a4, R,  a4, R,  a4, R,  f4, R, c5, R,  a4, R,  f4, R, c5, R, a4, R,  e5, R,  e5, R,  e5, R,  f5, R, c5, R,  g5, R,  f5, R,  c5, R, a4, R]
            beats1  = [  50, 20, 50, 20, 50, 20, 40, 5, 20, 5,  60, 10, 40, 5, 20, 5, 60, 80, 50, 20, 50, 20, 50, 20, 40, 5, 20, 5,  60, 10, 40, 5,  20, 5, 60, 40]
            for pos,len in enumerate(beats1):
                decodebeat(melody1[pos], len)

            return "A"


        def pattern():
            beep(.5)
            wait(.2)
            beep(.5)
            wait(.5)
            beep(.2)
            wait(.8)

            beep(.9)
            wait(.1)
            #print("Pattern Complete")
            return "A"
        #if config.DEBUGGING:
            #print ("Inside Smartlock ALARM")

        self.gpio.alarm()

        #Send Alarm Signal
        #sent = self.sendCommand(ALARM)
        sent = pattern()
        #sent = SW1()
        #if config.DEBUGGING:
            #print("Command Sent:",sent)

        if(sent):

            #register change in state
            self.STATUS_CHANGED = True
            self.lockingStatus = "DONE"

            print("DONE ALARMING\n\n\n")

        else:
            self.lockingStatus = "DEVICE Connection Error"
            print("Device Connection Error")
        #self.DeviceCode = prevstatus


    def unlock(self,override = False):
        #print("UNLOCKING\nUNLOCKING\nUNLOCKING\nUNLOCKING\nUNLOCKING\nUNLOCKING\n")
        if override:
            self.disable()
            self.OVERRIDE_COMMAND = True
            logger.warning("Override Command: Unlock")
        self.addQ(UNLOCK)

    def unlockSeq(self):
        logger.debug("Inside Smartlock UNlock")

        #Prompt Before Locking
        #warning

        #Update GPIO To Locking IN Progress
        self.gpio.unlock(blink = True)
        time.sleep(3)

        self.gpio.unlock()
        self.DeviceCode = UNLOCK

    def lock(self,override = False):
        if override:
            self.disable()
            self.OVERRIDE_COMMAND = True
            logger.warning("Override Command: Lock")
        self.addQ(LOCK)

    def lockSeq(self):
        logger.debug("Inside Smartlock lock")

        #Prompt Before Locking
        #warning()

        #Update GPIO To Locking IN Progress
        self.gpio.lock(blink = True)
        time.sleep(3)

        self.gpio.lock()
        self.DeviceCode = LOCK



if __name__ == "__main__":
    try:
        with SMARTLOCK() as a:
            a.start()
            #sent = a.sendCommand(DONE)
            a.lock()
            time.sleep(30)


            print(unlock)

            a.unlock()
            time.sleep(30)
            #threading.enumerate()

            #a.join()
            print("Program Done")
            #a.lock()"""

    finally:
        print("Program Complete Now Closing")

    pass
