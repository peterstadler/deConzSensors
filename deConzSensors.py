#!/usr/bin/env python3.5

from time import sleep, time
from datetime import datetime, timedelta
from pid.decorator import pidfile
#from subprocess import call
from RPi import GPIO
import requests
import json
#import config
import logging
import signal
import sys

#13: grün
#16: braun
#19: orange
#20: grün
#21: braun
#26: orange

SENSORS = [
    {
    "GPIOpinIN": 26,
    "GPIOpinOUT": 19,
    "SENSORID": 4,
    "NAME": "Garagentor"
    },
    {
    "GPIOpinIN": 20,
    "GPIOpinOUT": 13,
    "SENSORID": 2,
    "NAME": "Garagentür"
    }
]

# deConz REST API settings
APIKEY = ""         # API key for the deConz REST API
APIHOST = ""        # IP address of the deConz REST API, e.g. "192.168.1.100"
APISCHEME = "http"  # scheme for the deConz REST API, e.g. "http"

# program settings
POLL_INTERVALL = 7     # duration in seconds to wait between polls 
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', filename='/var/log/deConzSensors.log')

class mySensor:
    def ping(self):
        GPIO.output(self.gpio_out, 1)
        sumOfStates = 0
        for i in range(10): # get 10 samples of the door state
            curState = GPIO.input(self.gpio_in)
            logging.debug('current state of ' + self.name + ': ' + str(curState))
            sumOfStates += curState
            sleep(0.1)
        GPIO.output(self.gpio_out, 0)
        if sumOfStates < 5:
            if self.door_open == False:
                logging.info(self.name + ' opened')
            self.door_open = True
            setRemoteSensor(True, self.sensor_id)
        else: 
            if self.door_open == True:
                logging.info(self.name + ' closed')
                setRemoteSensor(False, self.sensor_id)
            self.door_open = False
        #delta = (datetime.now() - self.open_since).seconds   # delta in seconds between now and the door open state 
        #logging.debug(self.name + ': delta: ' + str(delta) + ' – GPIO input ' + str(self.gpio_in))
        #if self.door_open and (delta > (2 * POLL_INTERVALL)):  # only set remote sensor when we have 2 consecutive misses 
        #    logging.warning(self.name + ' open')
        #    setRemoteSensor(True, self.sensor_id)
        #self.door_open = True
    #def updateLocalSettings(self, channel):
    #    logging.debug(self.name +  ': Callback fired for GPIO input ' + str(channel))
    #    self.door_open = False
    #    self.open_since = datetime.now()
    def __init__(self, sensor_config):
        self.door_open = True
        self.open_since = datetime.now()
        self.gpio_in = sensor_config["GPIOpinIN"]
        self.gpio_out = sensor_config["GPIOpinOUT"]
        self.sensor_id = sensor_config["SENSORID"]
        self.name = sensor_config["NAME"]
        GPIO.setup(sensor_config["GPIOpinIN"], GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        GPIO.setup(sensor_config["GPIOpinOUT"], GPIO.OUT, initial=GPIO.LOW)
        #GPIO.add_event_detect(sensor_config["GPIOpinIN"], GPIO.RISING, callback=self.updateLocalSettings, bouncetime=250)

def terminate(signum, frame):
    logging.info("******************** Terminating ******************** ")
    logging.debug('Signal handler called with signal ' + str(signum))
    GPIO.cleanup()
    logging.info("************************ Exit *********************** ")
    sys.exit(0)

def init():
    logging.info("******************** Starting up ******************** ")
    signal.signal(signal.SIGINT, terminate)
    signal.signal(signal.SIGTERM, terminate)
    GPIO.setmode(GPIO.BCM)
    mySensors = []
    for sensor in SENSORS:
        logging.info("adding sensor '" + sensor["NAME"] + "' at GPIO pin " + str(sensor["GPIOpinIN"]))
        mySensors.append(mySensor(sensor))
    logging.info("***************************************************** ")
    return mySensors

def setRemoteSensor(open, sensor_id):
    url = APISCHEME + "://" + APIHOST + "/api/" + APIKEY + "/sensors/" + str(sensor_id) + "/state"
    payload = {'open': str(open).lower()}
    r = requests.put(url, data=json.dumps(payload))
    r.raise_for_status()
    logging.debug('setting remote sensor ' + str(sensor_id) + ' to ' + str(open))

# creating a PID file to prevent double execution of this script
@pidfile()

def main():
    sensors=init()              # initialize everything
    while True:                 # idle loop
        for sensor in sensors:
            sensor.ping()
            sleep(POLL_INTERVALL / len(sensors))   # sleep for the duration given as POLL_INTERVALL

if __name__ == '__main__':
    main()
