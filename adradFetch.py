#!/usr/bin/env python3
# Script for fetching unplotted ADRAD sigmet files from wdi.geos.tamu.edu
# Created 5 Januaray 2022 by Sam Gardner <stgardner4@tamu.edu>

import requests
from datetime import datetime as dt
from os import path, write
import json
from pathlib import Path
import sys

def writeToCmd(stringToWrite):
    if path.exists(path.join(basePath, "plotcmds.txt")):
        currentCmdFile = open(path.join(basePath, "plotcmds.txt"), "r")
        currentStr = open(path.join(basePath, "plotcmds.txt"), "r").read()
        currentCmdFile.close()
    else:
        currentStr = ""
    if stringToWrite not in currentStr:
        with open(path.join(basePath, "plotcmds.txt"), "a") as cmdw:
            cmdw.write(stringToWrite)
            cmdw.close()

def writeToStatus(stringToWrite):
    print(stringToWrite)
    stringToWrite = stringToWrite+"\n"
    if path.exists(path.join(basePath, "status.txt")):
        currentStatusFile = open(path.join(basePath, "status.txt"), "r")
        currentStr = open(path.join(basePath, "status.txt"), "r").read()
        currentStatusFile.close()
    else:
        currentStr = ""
    if stringToWrite not in currentStr:
        with open(path.join(basePath, "status.txt"), "a") as statw:
            statw.write(stringToWrite)
            statw.close()


if __name__ == '__main__':
    basePath = path.realpath(path.dirname(__file__))
    listOfAvailable = requests.get("http://wdi.geos.tamu.edu/data/ADRAD/GR2A/TAMU/dir.list", verify=False)
    availList = listOfAvailable.text.split()
    outPath = path.join(basePath, "radarData")
    Path(outPath).mkdir(parents=True, exist_ok=True)
    for availFile in availList:
        writeToStatus("Checking: "+availFile)
        if "TAMU" not in availFile:
            continue
        scanTime = dt.strptime(availFile, "TAMU_%Y%m%d_%H%M")
        metadataPath = path.join(basePath, "output", "metadata", "products", "120", scanTime.strftime("%Y%m%d%H00")+".json")
        if path.exists(metadataPath):
            with open(metadataPath, "r") as jsonRead:
                runData = json.load(jsonRead)
            validTimes = list()
            [validTimes.append(productFrame["valid"]) for productFrame in runData["productFrames"]]
            if int(scanTime.strftime("%Y%m%d%H%M")) in validTimes:
                continue
        dlPath = path.join(outPath, availFile)
        if path.exists(dlPath):
            continue
        writeToStatus("Downloading... "+availFile)
        radarData = requests.get("http://wdi.geos.tamu.edu/data/ADRAD/GR2A/TAMU/"+availFile, verify=False)
        with open(dlPath, "wb") as f:
            f.write(radarData.content)
        writeToStatus(availFile+" Succeeded!")
        writeToCmd(sys.executable+" "+path.join(basePath, "plotADRAD.py")+" "+scanTime.strftime("%Y%m%d%H%M")+"\n")

    