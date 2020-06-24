#!/usr/bin/env python3

import sys
import logging

from pykml import parser
from pykml.parser import Schema
from pykml.helpers import set_max_decimal_places

import gpxpy
import gpxpy.gpx
from lxml import etree
from bs4 import BeautifulSoup as bs

from tqdm import tqdm

logging.basicConfig(level=logging.DEBUG)

# parse kml

root = parser.parse(sys.stdin).getroot()
set_max_decimal_places(root, max_decimals={'longitude': 6,'latitude': 6})

logging.info('kml22gx validation: %r', Schema("kml22gx.xsd").validate(root))
logging.info('ogckml22 validation: %r', Schema("ogckml22.xsd").validate(root))

# https://developer.mozilla.org/en-US/docs/Web/XPath/Functions
# https://devhints.io/xpath

placemarks = root.xpath(
    '//k:Placemark',
    namespaces={'k': 'http://www.opengis.net/kml/2.2'})
logging.info('found %s placemarks', len(placemarks))

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

def find_text_for_field(sdata, name):
    return ''.join(sdata.xpath(f'./*[@name="{name}"]/text()')).strip()

def find_plain_text_for_field(sdata, name):
    return bs(find_text_for_field(sdata, name), features="lxml").get_text()

gpx = gpxpy.gpx.GPX()
count = 0
for e in tqdm(placemarks):
    try:
        sdata = e.ExtendedData.SchemaData
        try:
            lon, lat = e.Point.coordinates.text.split(',')
        except:
            logging.info('no Point found, using LON/LAT')
            lon = find_text_for_field(sdata, "LONGITUDE")
            lat = find_text_for_field(sdata, "LATITUDE")
        if float(lon) > 0:
            # lat/lon probably in wrong order
            lat, lon = lon, lat
            logging.warning(f'switched lat/lon {lat}, {lon}')
        wpt = gpxpy.gpx.GPXWaypoint(latitude = lat, longitude = lon)
        wpt.name = find_text_for_field(sdata, "RECAREANAM")
        desc = find_plain_text_for_field(sdata, "RECAREADES")
        desc += '\n'
        for field in fields:
            fdata = find_plain_text_for_field(sdata, field)
            if len(fdata) > 0:
                desc += '\n'
                desc += fields[field]
                desc += fdata
        wpt.description = desc
        gpx.waypoints.append(wpt)
    except:
        logging.error("problem with placemark", find_text_for_field(e.ExtendedData.SchemaData, "RECAREANAM"))

print(gpx.to_xml())
