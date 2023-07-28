#!/usr/bin/env python3
# python-based HDWX radar plotting script
# Created 7 July 2021 by Sam Gardner <stgardner4@tamu.edu>

from datetime import datetime as dt
import pyart
from matplotlib import pyplot as plt
from os import path, listdir, remove
from cartopy import crs as ccrs
from metpy.plots import USCOUNTIES
import numpy as np
import warnings
from matplotlib import colors as pltcolors
import sys
from pathlib import Path

# plotADRAD.py <scantime>
# Get the path to this script, that'll get used a lot.
basePath = path.abspath(path.dirname(__file__))
hasHelpers = False
if path.exists(path.join(basePath, "HDWX_helpers.py")):
    import HDWX_helpers
    hasHelpers = True

def plot_radar(radar, fieldToPlot, units, productID, gateFilter=None, plotRadius=160, rangeRingStep=160):
    # Create figure and axes
    fig = plt.figure()
    ax = plt.axes(projection=ccrs.epsg(3857))
    # Get a reference to one pixel unit for image resizing
    px = 1/plt.rcParams["figure.dpi"]
    # Give the image a reasonable size. The GIS-aware image will not be exactly 1920 by 1080, as it'll be trimmed when we set the extent, and the static image will have to be sized again later to for proper sizing, but this will give us a reasonably large image.
    fig.set_size_inches(1920*px, 1080*px)
    # Get colorblind-friendly color table
    if "reflectivity" in fieldToPlot.lower():
        cmap = "pyart_ChaseSpectral"
        vmin=-10
        vmax=80
    elif "velocity" in fieldToPlot.lower():
        cmap = "pyart_balance"
        vmin=-30
        vmax=30
    # Plot the data
    ADRADMapDisplay = pyart.graph.RadarMapDisplay(radar)
    # I want to create a custom colorbar/embellishments/title later, so disable those for now
    ADRADMapDisplay.plot_ppi_map(fieldToPlot.lower(), cmap=cmap, vmin=vmin, vmax=vmax, title_flag=False, colorbar_flag=False, add_grid_lines=False, ax=ax, fig=fig, width=2*plotRadius*1000, height=2*plotRadius*1000, gatefilter=gateFilter, embellish=False)
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
    if "--no-gis" not in sys.argv:
        # output/gisproducts/radar/ADRAD/productID/<year>/<month>/<day>/<hour>00/<minute>.png
        gisSaveLocation = path.join(outputBase, "gisproducts", "radar", "ADRAD", str(productID), radarScanDT.strftime("%Y"), radarScanDT.strftime("%m"), radarScanDT.strftime("%d"), radarScanDT.strftime("%H00"), radarScanDT.strftime("%M.png"))
        # Create parent directory if it doesn't already exist
        Path(path.dirname(gisSaveLocation)).mkdir(parents=True, exist_ok=True)
        # Save GIS Image
        extent = ax.get_tightbbox(fig.canvas.get_renderer()).transformed(fig.dpi_scale_trans.inverted())
        if hasHelpers:
            HDWX_helpers.saveImage(fig, gisSaveLocation, transparent=True, bbox_inches=extent)
        else:
            fig.savefig(gisSaveLocation, transparent=True, bbox_inches=extent)
        # Get lat/lon bounds for metadata
        point1 = ccrs.PlateCarree().transform_point(ax.get_extent()[0], ax.get_extent()[2], ccrs.epsg(3857))
        point2 = ccrs.PlateCarree().transform_point(ax.get_extent()[1], ax.get_extent()[3], ccrs.epsg(3857))
        gisInfo = [str(point1[1])+","+str(point1[0]), str(point2[1])+","+str(point2[0])]
        # Write metadata for GIS Image
        if hasHelpers:
            HDWX_helpers.writeJson(basePath, productID, radarScanDT, path.basename(gisSaveLocation), radarScanDT, gisInfo, 60)
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
        infoString = infoString + "    Max Range: " + str(maxRange) + " km"
    if hasHelpers:
        HDWX_helpers.dressImage(fig, ax, infoString, pyart.util.datetime_from_radar(radar), plotHandle=plotHandle, colorbarLabel=fieldToPlot.replace("_", " ")+" ("+units+")")
    # Save image
    staticSaveLocation = path.join(outputBase, "products", "radar", "ADRAD", str(productID+1), radarScanDT.strftime("%Y"), radarScanDT.strftime("%m"), radarScanDT.strftime("%d"), radarScanDT.strftime("%H00"), radarScanDT.strftime("%M.png"))
    Path(path.dirname(staticSaveLocation)).mkdir(parents=True, exist_ok=True)
    if hasHelpers:
        HDWX_helpers.saveImage(fig, staticSaveLocation)
        HDWX_helpers.writeJson(basePath, productID+1, radarScanDT, path.basename(staticSaveLocation), radarScanDT, ["0,0", "0,0"], 60)
    else:
        fig.savefig(staticSaveLocation)
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
            continue
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
            print("Plotting "+fieldToPlot+" "+path.basename(radarFileToPlot))
            plot_radar(radarObj, fieldToPlot, units, productID, gateFilter=gateFilter)
        remove(radarFileToPlot)
