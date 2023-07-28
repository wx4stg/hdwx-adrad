#!/usr/bin/env python3
# Script for fetching unplotted ADRAD sigmet files from wdi.geos.tamu.edu
# Created 5 Januaray 2022 by Sam Gardner <stgardner4@tamu.edu>

import requests
from datetime import datetime as dt
from os import path, listdir
import json
from pathlib import Path
import sys
import shutil
from time import sleep
import subprocess


if __name__ == '__main__':
    basePath = path.realpath(path.dirname(__file__))
    didPlotSomething = False
    listOfAvailable = list()
    print("Starting ADRAD download...")
    if path.isdir("/mnt/data/GR2A/TAMU/"):
        counter = 0
        while not path.exists("/mnt/data/GR2A/TAMU/dir.list"):
            counter = counter + 1
            if counter > 6000:
                break
            sleep(.01)
        listOfAvailable = sorted(listdir("/mnt/data/GR2A/TAMU/"))
    else:
        listOfAvailable = requests.get("https://wdi.geos.tamu.edu/data/ADRAD/GR2A/TAMU/dir.list", verify=False)
        listOfAvailable = listOfAvailable.text.split()
    outPath = path.join(basePath, "radarData")
    Path(outPath).mkdir(parents=True, exist_ok=True)
    for availFile in listOfAvailable:
        print("Checking: "+availFile)
        if "TAMU" not in availFile:
            continue
        if ".TAMU" in availFile:
            continue
        dlPath = path.join(outPath, availFile)
        if path.exists(dlPath):
            continue
        scanTime = dt.strptime(availFile, "TAMU_%Y%m%d_%H%M")
        metadataPath = path.join(basePath, "output", "metadata", "products", "120", scanTime.strftime("%Y%m%d%H00")+".json")
        if path.exists(metadataPath):
            with open(metadataPath, "r") as jsonRead:
                runData = json.load(jsonRead)
            validTimes = list()
            [validTimes.append(productFrame["valid"]) for productFrame in runData["productFrames"]]
            if scanTime.strftime("%Y%m%d%H%M") in validTimes:
                continue
        print("Downloading... "+availFile)
        radarData = ""
        if path.exists("/mnt/data/GR2A/TAMU/"+availFile):
            shutil.copyfile("/mnt/data/GR2A/TAMU/"+availFile, dlPath)
            print(availFile+" copied!")
            if "--no-gis" in sys.argv:
                subprocess.run([sys.executable, "plotADRAD.py", scanTime.strftime("%Y%m%d%H%M"), "--no-gis"])
            else:
                subprocess.run([sys.executable, "plotADRAD.py", scanTime.strftime("%Y%m%d%H%M")])
            didPlotSomething = True
        else:
            radarData = requests.get("https://wdi.geos.tamu.edu/data/ADRAD/GR2A/TAMU/"+availFile, verify=False)
            if radarData.status_code == 200:
                with open(dlPath, "wb") as f:
                    f.write(radarData.content)
                print(availFile+" Succeeded!")
                if "--no-gis" in sys.argv:
                    subprocess.run([sys.executable, "plotADRAD.py", scanTime.strftime("%Y%m%d%H%M"), "--no-gis"])
                else:
                    subprocess.run([sys.executable, "plotADRAD.py", scanTime.strftime("%Y%m%d%H%M")])
                didPlotSomething = True
            else:
                print(availFile+" failed "+radarData.content.decode())
    if didPlotSomething == False:
        sleep(30)