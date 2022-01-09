#!/bin/bash
# Product generation script for hdwx-adrad

if [ -f status.txt ]
then
  echo "lockfile found, exiting"
  exit
fi
touch status.txt
if [ -f plotcmds.txt ]
then
    rm plotcmds.txt
fi

$CONDA_PREFIX/bin/python3 adradFetch.py
plotcmdStr=`cat plotcmds.txt`
IFS=$'\n' plotcmdArr=($plotcmdStr)
for plotcmd in "${plotcmdArr[@]}"
do
    eval "$plotcmd"
done

$CONDA_PREFIX/bin/python3 cleanup.py