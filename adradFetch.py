#!/usr/bin/env python3
# Script for fetching unplotted ADRAD sigmet files from wdi.geos.tamu.edu
# Created 5 Januaray 2022 by Sam Gardner <stgardner4@tamu.edu>

import requests
from datetime import datetime as dt
from os import path
import json
from pathlib import Path


if __name__ == '__main__':
    basePath = path.realpath(path.dirname(__file__))
    listOfAvailable = requests.get("http://wdi.geos.tamu.edu/data/ADRAD/GR2A/TAMU/dir.list", verify=False)
    availList = listOfAvailable.text.split()
    outPath = path.join(basePath, "radarData")
    Path(outPath).mkdir(parents=True, exist_ok=True)
    for availFile in availList:
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
        radarData = requests.get("http://wdi.geos.tamu.edu/data/ADRAD/GR2A/TAMU/"+availFile, verify=False)
        with open(dlPath, "wb") as f:
            f.write(radarData.content)

    