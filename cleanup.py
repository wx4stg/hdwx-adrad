#!/usr/bin/env python3
# Purges no-longer-needed files from adrad plotting
# Created on 19 December 2021 by Sam Gardner <stgardner4@tamu.edu>

from datetime import datetime as dt, timedelta
from os import path, walk, remove

def writeToStatus(stringToWrite):
    print(stringToWrite)
    stringToWrite = stringToWrite+"\n"
    with open(path.join(basePath, "status.txt"), "a") as statw:
        statw.write(stringToWrite)
        statw.close()

if __name__ == "__main__":
    now = dt.now()
    basePath = path.dirname(path.abspath(__file__))
    writeToStatus("Cleaning up...")
    modelDataPath = path.join(basePath, "radarData")
    outputPath = path.join(basePath, "output")
    if path.exists(modelDataPath):
        for root, dirs, files in walk(modelDataPath):
            for name in files:
                filepath = path.join(path.join(basePath, root), name)
                createTime = dt.fromtimestamp(path.getmtime(filepath))
                if createTime < now - timedelta(hours=2):
                    remove(filepath)
                    writeToStatus(filepath+" deleted.")
    if path.exists(outputPath):
        for root, dirs, files in walk(outputPath):
            for name in files:
                filepath = path.join(path.join(basePath, root), name)
                if filepath.endswith(".json"):
                    deleteAfter = timedelta(days=2)
                else:
                    deleteAfter = timedelta(minutes=20)
                createTime = dt.fromtimestamp(path.getmtime(filepath))
                if createTime < now - deleteAfter:
                    remove(filepath)
                    writeToStatus(filepath+" deleted.")
    remove(path.join(basePath, "status.txt"))