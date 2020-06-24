#!/usr/bin/env python

import sys

from pykml import parser
from pykml.parser import Schema
from pykml.helpers import set_max_decimal_places

import gpxpy
import gpxpy.gpx
from lxml import etree
from bs4 import BeautifulSoup

from tqdm import tqdm

# parse kml

root = parser.parse(sys.stdin).getroot()
print('kml22gx validation:', Schema("kml22gx.xsd").validate(root), file=sys.stderr)
print('ogckml22 validation:', Schema("ogckml22.xsd").validate(root), file=sys.stderr)
set_max_decimal_places(root, max_decimals={'longitude': 6,'latitude': 6})

# https://developer.mozilla.org/en-US/docs/Web/XPath/Functions
# https://devhints.io/xpath

placemarks = root.xpath('/k:kml//k:Placemark', namespaces={'k': 'http://www.opengis.net/kml/2.2'})
print(f'found {len(placemarks)} placemarks', file=sys.stderr)

# TODO read these fields from the kml file itself!
# TODO make the mapping to their display names configurable

fields = {
"OPENSTATUS": 'Open/closed:  ',
"OPEN_SEASO": 'From:         ',
"OPEN_SEA_1": 'To:           ',
"OPERATIONA": 'Operational:  ',
"FEEDESCRIP": 'Fees:         ',
"RESERVATIO": 'Reservations: ',
"RESTRICTIO": 'Restrictions: ',
"MARKERACTI": 'Activities:   ',
"SPOTLIGHTD": 'Spotlighted:  ',
"ATTRACTION": 'Attraction:   ',
"ACCESSIBIL": 'Access:       ',
"FORESTNAME": 'Forest:       '
}

# write gpx

def find_text_for_attrib(sdata, name):
    return ''.join(sdata.xpath(f'./*[@name="{name}"]/text()')).strip()
    
gpx = gpxpy.gpx.GPX()
count = 0
for e in tqdm(placemarks):
    try:
        sdata = e.ExtendedData.SchemaData
        try:
            pos = e.Point.coordinates.text.split(',')
            lon = pos[0]
            lat = pos[1]
        except:
            print('no Point found, using LON/LAT', file=sys.stderr)
            lon = find_text_for_attrib(sdata, "LONGITUDE")
            lat = find_text_for_attrib(sdata, "LATITUDE")
        if float(lon) > 0:
            # lat/lon probably in wrong order
            lat, lon = lon, lat
            print(f'WARNING: switched lat/lon {lat}, {lon}', file=sys.stderr)
        wpt = gpxpy.gpx.GPXWaypoint(longitude = lon, latitude = lat)
        wpt.name = find_text_for_attrib(sdata, "RECAREANAM")
        desc = BeautifulSoup(find_text_for_attrib(sdata, "RECAREADES"), features="lxml").get_text()
        desc += '\n'
        for field in fields:
            fdata = BeautifulSoup(find_text_for_attrib(sdata, field), features="lxml").get_text()
            if len(fdata) > 0:
                desc += '\n'
                desc += fields[field]
                desc += fdata
        wpt.description = desc
        gpx.waypoints.append(wpt)
    except:
        print("problem with placemark", find_text_for_attrib(e.ExtendedData.SchemaData, "RECAREANAM"), file=sys.stderr)

print(gpx.to_xml())
