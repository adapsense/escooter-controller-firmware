from subprocess import Popen, STDOUT, PIPE
import paho.mqtt.publish as publish
import json
import pty
import os
from statistics import median

master, slave = pty.openpty()

#Open C File
#proc = subprocess.Popen(['./bsec_bme680'], stdout=subprocess.PIPE)
proc = Popen(['./bsec_bme680'], shell=True, stdout=slave, stderr=slave, close_fds=True)
stdout = os.fdopen(master)
print (stdout.readline())
print ("a")
#line = ""
line = stdout.readline()
print (line)
#stdout = os.fdopen(master)

listIAQ_Accuracy = []
listPressure = []
listGas = []
listTemperature = []
listIAQ = []
listHumidity  = []
listStatus = []

#for line in iter(stdout.readline, ''):
while line != '':
    print("load!\n")
    lineJSON = json.loads(line) # process line-by-line
    lineDict = dict(lineJSON)
    print (lineDict['IAQ'])

    listIAQ_Accuracy.append(int(lineDict['IAQ_Accuracy']))
    listPressure.append(float(lineDict['Pressure']))
    listGas.append(int(lineDict['Gas']))
    listTemperature.append(float(lineDict['Temperature']))
    listIAQ.append(float(lineDict['IAQ']))
    listHumidity.append(float(lineDict['Humidity']))
    listStatus.append(int(lineDict['Status']))

    if len(listIAQ_Accuracy) == 20:
        #generate the median for each value
        IAQ_Accuracy = median(listIAQ_Accuracy)
        Pressure = median(listPressure)
        Gas = median(listGas)
        Temperature = median(listTemperature)
        IAQ = median(listIAQ)
        Humidity = median(listHumidity)
        Status = median(listStatus)
        
        print(IAQ)

        #clear lists
        listIAQ_Accuracy.clear()
        listPressure.clear()
        listGas.clear()
        listTemperature.clear()
        listIAQ.clear()
        listHumidity.clear()
        listStatus.clear()

        #Temperature Offset
        Temperature = Temperature + 2

        payload = {"IAQ_Accuracy": IAQ_Accuracy,"IAQ": round(IAQ, 1),"Temperature": round(Temperature, 1),"Humidity": round(Humidity, 1),"Pressure": round(Pressure, 1),"Gas": Gas,"Status": Status}
        #publish.single("bme680_wohnzimmer", json.dumps(payload), hostname="localhost")
        
    line = stdout.readline()
    line = stdout.readline()
    print (line)