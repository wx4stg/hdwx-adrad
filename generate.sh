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

if [ -f ~/mambaforge/envs/HDWX/bin/python3 ]
then
    ~/mambaforge/envs/HDWX/bin/python3 adradFetch.py
if [ -f ~/miniconda3/envs/HDWX/bin/python3 ]
then
    ~/miniconda3/envs/HDWX/bin/python3 adradFetch.py
fi
plotcmdStr=`cat plotcmds.txt`
IFS=$'\n' plotcmdArr=($plotcmdStr)
for plotcmd in "${plotcmdArr[@]}"
do
    eval "$plotcmd"
done

if [ -f ~/mambaforge/envs/HDWX/bin/python3 ]
then
    ~/mambaforge/envs/HDWX/bin/python3 cleanup.py
fi
if [ -f ~/miniconda3/envs/HDWX/bin/python3 ]
then
    ~/miniconda3/envs/HDWX/bin/python3 cleanup.py
fi