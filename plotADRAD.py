#!/usr/bin/env python3
# Next-gen HDWX radar plotting script
# Created 7 July 2021 by Sam Gardner <stgardner4@tamu.edu>

from datetime import datetime as dt
import pyart
from matplotlib import pyplot as plt
from os import path, listdir, remove, chmod
from cartopy import crs as ccrs
from metpy.plots import ctables
from metpy.plots import USCOUNTIES
import numpy as np
import warnings
from matplotlib import image as mpimage
import sys
from pathlib import Path
from atomicwrites import atomic_write
import json

# plotADRAD.py <scantime>
# Get the path to this script, that'll get used a lot.
basePath = path.abspath(path.dirname(__file__))

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

def writeJson(productID, scanTime, gisInfo):
    if productID == 120:
        productDesc = "ADRAD 0.5° Reflectivity PPI"
        productPath = "gisproducts/radar/ADRAD/"+str(productID)
        isGIS = True
    elif productID == 121:
        productDesc = "ADRAD 0.5° Reflectivity PPI"
        productPath = "products/radar/ADRAD/"+str(productID)
        isGIS = False
    elif productID == 122:
        productDesc = "ADRAD 0.5° Reflectivity PPI (Quality-controlled)"
        productPath = "gisproducts/radar/ADRAD/"+str(productID)
        isGIS = True
    elif productID == 123:
        productDesc = "ADRAD 0.5° Reflectivity PPI (Quality-controlled)"
        productPath = "products/radar/ADRAD/"+str(productID)
        isGIS = False
    elif productID == 124:
        productDesc = "ADRAD 0.5° Signal Quality Index"
        productPath = "products/radar/ADRAD/"+str(productID)
        isGIS = False
    elif productID == 125:
        productDesc = "ADRAD 0.5° Velocity PPI"
        productPath = "gisproducts/radar/ADRAD/"+str(productID)
        isGIS = True
    elif productID == 126:
        productDesc = "ADRAD 0.5° Velocity PPI"
        productPath = "products/radar/ADRAD/"+str(productID)
        isGIS = False
    publishTime = dt.utcnow()
    productDict = {
        "productID" : productID,
        "productDescription" : productDesc,
        "productPath" : productPath,
        "productReloadTime" : 60,
        "lastReloadTime" : publishTime.strftime("%Y%m%d%H%M"),
        "isForecast" : False,
        "isGIS" : isGIS,
        "fileExtension" : "png"
    }
    productDictJsonPath = path.join(basePath, "output", "metadata", str(productID)+".json")
    Path(path.dirname(productDictJsonPath)).mkdir(parents=True, exist_ok=True)
    with atomic_write(productDictJsonPath, overwrite=True) as jsonWrite:
        json.dump(productDict, jsonWrite, indent=4)
    chmod(productDictJsonPath, 0o644)
    runPathExtension = scanTime.strftime("%Y/%m/%d/%H00/")
    # Now we need to write a json for the product run in output/metadata/products/<productID>/<runTime>.json
    productRunDictPath = path.join(basePath, "output", "metadata", "products", str(productID), scanTime.strftime("%Y%m%d%H00")+".json")
    # Create parent directory if it doesn't already exist.
    Path(path.dirname(productRunDictPath)).mkdir(parents=True, exist_ok=True)
    # If the json file already exists, read it in to to discover which frames have already been generated
    if path.exists(productRunDictPath):
        with open(productRunDictPath, "r") as jsonRead:
            oldData = json.load(jsonRead)
        # Add previously generated frames to a list, framesArray
        framesArray = oldData["productFrames"]
    else:
        # If that file didn't exist, then create an empty list instead
        framesArray = list()
    # Now we need to add the frame we just wrote, as well as any that exist in the output directory that don't have metadata yet. 
    # To do this, we first check if the output directory is not empty.
    productRunPath = path.join(basePath, "output", productPath, runPathExtension)
    if len(listdir(productRunPath)) > 0:
        # If there are files inside, list them all
        frameNames = listdir(productRunPath)
        # get an array of integers representing the minutes past the hour of frames that have already been generated
        frameMinutes = [int(framename.replace(".png", "")) for framename in frameNames if ".png" in framename]
        # Loop through the previously-generated minutes and generate metadata for each
        for frameMin in frameMinutes:
            frmDict = {
                "fhour" : 0, # forecast hour is 0 for non-forecasts
                "filename" : str(frameMin)+".png",
                "gisInfo" : gisInfo,
                "valid" : str(int(scanTime.strftime("%Y%m%d%H00"))+frameMin)
            }
            # If this dictionary isn't already in the framesArray, add it
            if frmDict not in framesArray:
                framesArray.append(frmDict)
    productRunDict = {
        "publishTime" : publishTime.strftime("%Y%m%d%H%M"),
        "pathExtension" : runPathExtension,
        "runName" : scanTime.strftime("%d %b %Y %HZ"),
        "availableFrameCount" : len(framesArray),
        "totalFrameCount" : len(framesArray),
        "productFrames" : sorted(framesArray, key=lambda dict: int(dict["valid"])) # productFramesArray, sorted by increasing valid Time
    }
    with atomic_write(productRunDictPath, overwrite=True) as jsonWrite:
        json.dump(productRunDict, jsonWrite, indent=4)
    chmod(productRunDictPath, 0o644)
    # Now we need to create a dictionary for the product type (TAMU)
    productTypeID = 1
    # Output for this json is output/metadata/productTypes/1.json
    productTypeDictPath = path.join(basePath, "output/metadata/productTypes/"+str(productTypeID)+".json")
    # Create output directory if it doesn't already exist
    Path(path.dirname(productTypeDictPath)).mkdir(parents=True, exist_ok=True)
    # Create empty list that will soon hold a dict for each of the products generated by this script
    productsInType = list()
    # If the productType json file already exists, read it in to discover which products it contains
    if path.exists(productTypeDictPath):
        with open(productTypeDictPath, "r") as jsonRead:
            oldProductTypeDict = json.load(jsonRead)
        # Add all of the products from the json file into the productsInType list...
        for productInOldDict in oldProductTypeDict["products"]:
            # ...except for the one that's currently being generated (prevents duplicating it)
            if productInOldDict["productID"] != productID:
                productsInType.append(productInOldDict)
    # Add the productDict for the product we just generated
    productsInType.append(productDict)
    # Create productType Dict
    productTypeDict = {
        "productTypeID" : productTypeID,
        "productTypeDescription" : "TAMU",
        "products" : sorted(productsInType, key=lambda dict: dict["productID"]) # productsInType, sorted by productID
    }
    # Write productType dict to json
    with open(productTypeDictPath, "w") as jsonWrite:
        json.dump(productTypeDict, jsonWrite, indent=4)
    # Ensure correct file permissions
    chmod(productTypeDictPath, 0o644)
    

def plot_radar(radar, fieldToPlot, units, productID, gateFilter=None, plotRadius=160, rangeRingStep=160):
    # Create figure and axes
    fig = plt.figure()
    ax = plt.axes(projection=ccrs.epsg(3857))
    # Get a reference to one pixel unit for image resizing
    px = 1/plt.rcParams["figure.dpi"]
    # Give the image a reasonable size. The GIS-aware image will not be exactly 1920 by 1080, as it'll be trimmed when we set the extent, and the static image will have to be sized again later to for proper sizing, but this will give us a reasonably large image.
    fig.set_size_inches(1920*px, 1080*px)
    # Get MetPy's NWS colortable
    if "reflectivity" in fieldToPlot.lower():
        norm, cmap = ctables.registry.get_with_steps("NWSReflectivity", 5, 5)
    elif "velocity" in fieldToPlot.lower():
        norm, cmap = ctables.registry.get_with_steps("NWS8bitVel", 5, 5)
        norm = None
    cmap.set_under("#00000000")
    cmap.set_over("black")
    # Plot the data
    ADRADMapDisplay = pyart.graph.RadarMapDisplay(radar)
    # I want to create a custom colorbar/embelishments/title later, so disable those for now
    ADRADMapDisplay.plot_ppi_map(fieldToPlot.lower(), norm=norm, cmap=cmap, title_flag=False, colorbar_flag=False, ax=ax, fig=fig, width=2*plotRadius*1000, height=2*plotRadius*1000, gatefilter=gateFilter, embelish=False)
    # Get a handle to the pcolormesh which will be used to generate our colorbar later
    plotHandle = ax.get_children()[0]
    # Plot range rings
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore")
        ADRADMapDisplay.plot_range_rings(range(0, plotRadius+1, rangeRingStep), col="gray", ls="dotted")
    # Save GIS-Aware figure now
    outputBase = path.join(basePath, "output")
    # Get scan time for metadata
    if requestedDatetime is None:
        radarScanDT = pyart.util.datetime_from_radar(radar)
    else:
        radarScanDT = requestedDatetime
    # output/gisproducts/radar/ADRAD/productID/<year>/<month>/<day>/<hour>00/<minute>.png
    gisSaveLocation = path.join(outputBase, "gisproducts", "radar", "ADRAD", str(productID), radarScanDT.strftime("%Y"), radarScanDT.strftime("%m"), radarScanDT.strftime("%d"), radarScanDT.strftime("%H00"), radarScanDT.strftime("%M.png"))
    # Create parent directory if it doesn't already exist
    Path(path.dirname(gisSaveLocation)).mkdir(parents=True, exist_ok=True)
    # Save GIS Image
    extent = ax.get_tightbbox(fig.canvas.get_renderer()).transformed(fig.dpi_scale_trans.inverted())
    fig.savefig(gisSaveLocation, transparent=True, bbox_inches=extent)
    # Get lat/lon bounds for metadata
    point1 = ccrs.PlateCarree().transform_point(ax.get_extent()[0], ax.get_extent()[2], ccrs.epsg(3857))
    point2 = ccrs.PlateCarree().transform_point(ax.get_extent()[1], ax.get_extent()[3], ccrs.epsg(3857))
    gisInfo = [str(point1[1])+","+str(point1[0]), str(point2[1])+","+str(point2[0])]
    # Write metadata for GIS Image
    writeJson(productID, radarScanDT, gisInfo)
    # Add counties
    ax.add_feature(USCOUNTIES.with_scale("5m"), edgecolor="gray")
    # Now we force 1920x1080
    fig.set_size_inches(1920*px, 1080*px)
    # Force ax to expand to figure
    ax.set_box_aspect(9/16)
    # Give our plot a title, we'll start with an emtpy string
    infoString = str()
    # Instrument name can sometimes be bytes or string, so try to decode it, then add it to the title string
    if "instrument_name" in radar.metadata.keys():
        insStr = radar.metadata["instrument_name"]
        try:
            insStr = insStr.decode()
        except (UnicodeDecodeError, AttributeError, TypeError):
            pass
        infoString = insStr
    # This is ADRAD-specific, will append "SOAP SURV"
    if "sigmet_task_name" in radar.metadata.keys():
        infoString = infoString + " " +radar.metadata["sigmet_task_name"].decode().replace("  ", "")
    # else we can just use the standard volume coverage pattern numbers
    elif "vcp_pattern" in radar.metadata.keys():
        infoString = infoString + " VCP-" +str(radar.metadata["vcp_pattern"])
    # Add that this is a plan-position indicator
    infoString = infoString + " PPI\n"
    # Add PRF information, if available
    if "prt" in radar.instrument_parameters:
        prf = np.round(1/np.mean(radar.instrument_parameters["prt"]["data"]), 0)
        infoString = infoString + "Avg. PRF: " + str(prf) + " Hz"
    # Add elevation
    elevation = np.round(radar.fixed_angle["data"][0], 1)
    infoString = infoString + "    Elevation: " + str(elevation) + "°"
    # Add max range, if available
    if "unambiguous_range" in radar.instrument_parameters:
        maxRange = np.round(np.max(radar.instrument_parameters["unambiguous_range"]["data"])/1000, 0)
        infoString = infoString + "    Max Range: " + str(maxRange) + " km\n"
    # Add scan time
    infoString = infoString + "Valid " + pyart.util.datetime_from_radar(radar).strftime("%d %b %Y %H:%M:%S UTC")
    # Create custom colorbar
    cbax = fig.add_axes([.01,0.065,(ax.get_position().width/3),.02])
    fig.colorbar(plotHandle, cax=cbax, orientation="horizontal", extend="neither")
    cbax.set_xlabel(fieldToPlot.replace("_", " ")+" ("+units+")")
    # Create title axes
    tax = fig.add_axes([ax.get_position().x0+cbax.get_position().width+.01,0.03,(ax.get_position().width/3),.045])
    title = tax.text(0.5, 0.5, infoString, horizontalalignment="center", verticalalignment="center", fontsize=14)
    plt.setp(tax.spines.values(), visible=False)
    tax.tick_params(left=False, labelleft=False)
    tax.tick_params(bottom=False, labelbottom=False)
    tax.set_xlabel("Python HDWX -- Send bugs to stgardner4@tamu.edu")
    # Create custom logo axes
    lax = fig.add_axes([(.99-(ax.get_position().width/3)),0,(ax.get_position().width/3),.08])
    lax.set_aspect(2821/11071)
    plt.setp(lax.spines.values(), visible=False)
    lax.tick_params(left=False, labelleft=False)
    lax.tick_params(bottom=False, labelbottom=False)
    atmoLogo = mpimage.imread("assets/atmoLogo.png")
    lax.imshow(atmoLogo)
    # Move ax for optimal spacing
    ax.set_position([.005, cbax.get_position().y0+cbax.get_position().height+.005, .99, (.99-(cbax.get_position().y0+cbax.get_position().height))])
    # Save image
    staticSaveLocation = path.join(outputBase, "products", "radar", "ADRAD", str(productID+1), radarScanDT.strftime("%Y"), radarScanDT.strftime("%m"), radarScanDT.strftime("%d"), radarScanDT.strftime("%H00"), radarScanDT.strftime("%M.png"))
    Path(path.dirname(staticSaveLocation)).mkdir(parents=True, exist_ok=True)
    fig.savefig(staticSaveLocation)
    writeJson(productID+1, radarScanDT, ["0,0", "0,0"])
    if productID == 122:
        sqiFig, (ax1, ax2) = plt.subplots(1, 2, subplot_kw=dict(projection=ccrs.epsg(3857)))
        sqicmap = plt.get_cmap("rainbow")
        ADRADMapDisplay.plot_ppi_map("reflectivity", norm=norm, cmap=cmap, title_flag=True, colorbar_flag=False, ax=ax1, fig=sqiFig, width=2*plotRadius*1000, height=2*plotRadius*1000, gatefilter=None, embelish=True)
        reflHandle = ax1.get_children()[0]
        ax1.add_feature(USCOUNTIES.with_scale("5m"), edgecolor="gray")
        cbax1 = sqiFig.add_axes([ax1.get_position().x0, 0.075, (ax1.get_position().width/3), .02])
        sqiFig.colorbar(reflHandle, cax=cbax1, orientation="horizontal")
        cbax1.set_xlabel("Reflectivity (dBZ)")
        ADRADMapDisplay.plot_ppi_map("normalized_coherent_power", mask_tuple=("reflectivity", 1), vmin=0, vmax=1, cmap=sqicmap, title_flag=True, colorbar_flag=False, ax=ax2, fig=sqiFig, width=2*plotRadius*1000, height=2*plotRadius*1000, gatefilter=None, embelish=True)
        sqiHandle = ax2.get_children()[0]
        ax2.add_feature(USCOUNTIES.with_scale("5m"), edgecolor="gray")
        cbax2 = sqiFig.add_axes([ax2.get_position().x0, 0.075, (ax2.get_position().width/3), .02])
        sqiFig.colorbar(sqiHandle, cax=cbax2, orientation="horizontal")
        cbax2.set_xlabel("Signal Quality Index")
        sqiFig.set_size_inches(1920*px, 1080*px)
        staticSQICompSaveLocation = path.join(outputBase, "products", "radar", "ADRAD", str(productID+2), radarScanDT.strftime("%Y"), radarScanDT.strftime("%m"), radarScanDT.strftime("%d"), radarScanDT.strftime("%H00"), radarScanDT.strftime("%M.png"))
        Path(path.dirname(staticSQICompSaveLocation)).mkdir(parents=True, exist_ok=True)
        sqiFig.savefig(staticSQICompSaveLocation)
        writeJson(productID+2, radarScanDT, ["0,0", "0,0"])
    plt.close(fig)

if __name__ == "__main__":
    # Get path to input directory
    radarDataDir = path.join(basePath, "radarData")
    if len(sys.argv) > 1:
        # Get the time of the radar file we want to open from arg1.
        requestedDatetime = dt.strptime(sys.argv[1], "%Y%m%d%H%M")
        # Get file path to the IRIS data file we want to open and make plots
        radFileName = path.join(radarDataDir, requestedDatetime.strftime("TAMU_%Y%m%d_%H%M"))
        radarFilesToPlot = [radFileName]
    else:
        radarFilesToPlot = [path.join(radarDataDir, radFileName) for radFileName in sorted(listdir(radarDataDir))]
    for radarFileToPlot in radarFilesToPlot:
        # Read in the radar data
        try:
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore")
                radarObj = pyart.io.read(radarFileToPlot)
                if len(sys.argv) <= 1:
                    requestedDatetime = pyart.util.datetime_from_radar(radarObj)
        except Exception as e:
            remove(radarFileToPlot)
            exit()
        # List of fields to plot formatted as (field, unit, productID)
        fieldsToPlot = [("Reflectivity", "dBZ", 120, None), ("Velocity", "m/s", 125, None)]
        # Now we check to see if SQI (or "normalized coherent power") data was saved in the radar file. If available, filter reflectivity and add it back to the radar object
        if "normalized_coherent_power" in radarObj.fields.keys():
            sqiValid = radarObj.fields["normalized_coherent_power"]["data"]
            sqiValid = np.where(sqiValid > 0.38, 0, 1)
            finalRefl = np.ma.masked_array(radarObj.fields["reflectivity"]["data"], mask=sqiValid)
            radarObj.add_field_like("reflectivity", "reflectivity_filtered", finalRefl)
            despekFilter = pyart.correct.despeckle_field(radarObj, "reflectivity_filtered")
            fieldsToPlot.append(("Reflectivity_Filtered", "dBZ", 122, despekFilter))
        # Make the plots!
        for (fieldToPlot, units, productID, gateFilter) in fieldsToPlot:
            writeToStatus("Plotting "+fieldToPlot+" "+path.basename(radarFileToPlot))
            plot_radar(radarObj, fieldToPlot, units, productID, gateFilter=gateFilter)
        remove(radarFileToPlot)
