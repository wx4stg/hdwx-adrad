#!/usr/bin/env python3
# Next-gen HDWX radar plotting script
# Created 7 July 2021 by Sam Gardner <stgardner4@tamu.edu>

from datetime import datetime as dt
import pyart
from matplotlib import pyplot as plt
from os import path, getcwd, listdir
from cartopy import crs as ccrs
from metpy.plots import ctables
from metpy.plots import USCOUNTIES
import numpy as np
import warnings
from matplotlib import image as mpimage
import sys
from pathlib import Path

# plotADRAD.py <scantime>
# Get the path to this script, that'll get used a lot.
basePath = path.abspath(path.dirname(__file__))
# Get the time of the radar file we want to open from arg1.
requestedDatetime = dt.strptime(sys.argv[1], "%Y%m%d%H%M")


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
    # output/gisproducts/radar/ADRAD/productID/<year>/<month>/<day>/<hour>00/<minute>.png
    gisSaveLocation = path.join(outputBase, "gisproducts", "radar", "ADRAD", str(productID), requestedDatetime.strftime("%Y"), requestedDatetime.strftime("%m"), requestedDatetime.strftime("%d"), requestedDatetime.strftime("%H00"), requestedDatetime.strftime("%M.png"))
    # Create parent directory if it doesn't already exist
    Path(path.dirname(gisSaveLocation)).mkdir(parents=True, exist_ok=True)
    # Save GIS Image
    extent = ax.get_tightbbox(fig.canvas.get_renderer()).transformed(fig.dpi_scale_trans.inverted())
    fig.savefig(gisSaveLocation, transparent=True, bbox_inches=extent)
    # Add counties
    ax.add_feature(USCOUNTIES.with_scale("5m"), edgecolor="gray")
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
    infoString = infoString + pyart.util.datetime_from_radar(radar).strftime("%d %b %Y %H:%M:%S UTC")
    # Set title string
    ax.set_title(infoString)
    # Create custom colorbar
    cbax = fig.add_axes([ax.get_position().x0, 0.075, (ax.get_position().width/3), .02])
    fig.colorbar(plotHandle, cax=cbax, orientation="horizontal", extend="neither")
    cbax.set_xlabel(fieldToPlot.replace("_", " ")+" ("+units+")")
    # Create custom logo axes
    lax = fig.add_axes([ax.get_position().x0+2*(ax.get_position().width/3), 0.015, (ax.get_position().width/3), .1])
    lax.set_aspect(2821/11071)
    plt.setp(lax.spines.values(), visible=False)
    lax.tick_params(left=False, labelleft=False)
    lax.tick_params(bottom=False, labelbottom=False)
    lax.set_xlabel("Plot by Sam Gardner")
    atmoLogo = mpimage.imread("assets/atmoLogo.png")
    lax.imshow(atmoLogo)
    # Force image size to 1808p
    fig.set_size_inches(1920*px, 1080*px)
    staticSaveLocation = path.join(outputBase, "products", "radar", "ADRAD", str(productID), requestedDatetime.strftime("%Y"), requestedDatetime.strftime("%m"), requestedDatetime.strftime("%d"), requestedDatetime.strftime("%H00"), requestedDatetime.strftime("%M.png"))
    Path(path.dirname(staticSaveLocation)).mkdir(parents=True, exist_ok=True)
    fig.savefig(staticSaveLocation)
    plt.close(fig)

if __name__ == "__main__":
    # Get path to input directory
    radarDataDir = path.join(basePath, "radarData")
    # Get file path to the IRIS data file we want to open and make plots
    radarFileToPlot = path.join(radarDataDir, requestedDatetime.strftime("TAMU_%Y%m%d_%H%M"))
    # Read in the radar data
    radarObj = pyart.io.read(radarFileToPlot)
    # List of fields to plot formatted as (field, unit, productID)
    fieldsToPlot = [("Reflectivity", "dBZ", 120, None), ("Velocity", "m/s", 125, None)]
    # Now we check to see if SQI (or "normalized coherent power") data was saved in the radar file. If available, filter reflectivity and add it back to the radar object
    if "normalized_coherent_power" in radarObj.fields.keys():
        sqiValid = radarObj.fields["normalized_coherent_power"]["data"]
        sqiValid = np.where(sqiValid > 0.5, 1, 0)
        finalRefl = np.multiply(radarObj.fields["reflectivity"]["data"], sqiValid)
        radarObj.add_field_like("reflectivity", "reflectivity_filtered", finalRefl)
        despekFilter = pyart.correct.despeckle_field(radarObj, "reflectivity_filtered")
        fieldsToPlot.append(("Reflectivity_Filtered", "dBZ", 122, despekFilter))
    # Make the plots!
    for (fieldToPlot, units, productID, gateFilter) in fieldsToPlot:
        plot_radar(radarObj, fieldToPlot, units, productID, gateFilter=gateFilter)
