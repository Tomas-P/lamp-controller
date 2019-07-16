#!/usr/bin/python3
import sys
assert sys.version.startswith('3.7')

from gpiozero import LED
import glob
from subprocess import run
import re
import threading
from time import sleep
from datetime import datetime, time
from queue import SimpleQueue

MEASURE_EXPR = re.compile('t=(\d{5})\n')
MEASUREMENTS_FILENAME = "TemperatureData.tsv"
RELAY_PIN = 22
DAWN = time(hour=5, minute=30)
DUSK = time(hour=21, minute=5)
Glob_Q = SimpleQueue() # we use the queue for control
# signalling between threads
# we do this because queues are thread safe. most python objects are not.

def locate_devices():

    #find all attached temp sensors

    devices = glob.glob('/sys/bus/w1/devices/*')

    return sorted([d for d in devices if 'master' not in d])

def ask_device(device_name):

    # get output of device

    p = run(['cat', device_name+'/w1_slave'], capture_output=True)

    return p.stdout.decode()

def interpret_reading(reading):

    # convert the output string into a numerical measurement

    return int(MEASURE_EXPR.findall(reading)[0]) / 1000

def create_headings():
    with open(MEASUREMENTS_FILENAME, 'a') as handle:
        handle.write("Time\tDevice 1 Reading\tDevice 2 Reading\n")


# take temperature measurements at regular intervals and save them
def measure():
    # run this in a thread
    d1, d2 = locate_devices()
    while True:

        t1 = interpret_reading(ask_device(d1))
        t2 = interpret_reading(ask_device(d2))
        now = str(datetime.now())

        if Glob_Q.empty(): # computation continues

            with open(MEASUREMENTS_FILENAME, 'a') as fhandle:

                fhandle.write(f"{now}\t{t1}\t{t2}\n")

        else: # time to stop
            break

        sleep(60) # gives approx 1-minute time fidelity



def control_lamp():
    # run this in a thread

    with LED(RELAY_PIN) as hlamp: # hopefully this cleans up properly in threads

        while True:

            if Glob_Q.empty(): # computation continues

                now = datetime.time(datetime.now())

                if DAWN <= now <= DUSK: # day condition
                    hlamp.off()

                elif DUSK < now or now < DAWN: # night condition
                    hlamp.on() # apparatus is for a
                    # high night temperature experiment

            else: # time to stop
                break

            # only check to turn on the lamp every 5 minutes
            sleep(5 * 60)

def main(keep):
    # reset contents of the measurements file
    create_headings()
    # create threads to control tasks
    measure_thread = threading.Thread(target=measure)
    lamp_thread = threading.Thread(target=control_lamp)

    # begin tasks of other threads
    measure_thread.start()
    lamp_thread.start()

    # allow threads to do their task for however long
    # keep is a measure of the total experiment time in days
    sleep(keep * 60 * 60 * 24)

    # send an end operation signal to the other threads
    Glob_Q.put('end')

    # wait for the other threads to clean up resources
    measure_thread.join()
    lamp_thread.join()

    # program is now finished
    return None


if __name__ == '__main__':
    hours = int(input("How many days will the experiment run for? "))
    main(hours)
