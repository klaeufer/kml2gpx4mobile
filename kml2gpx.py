#!/usr/bin/env python3

import sys
import logging

from pykml import parser
from pykml.parser import Schema
from pykml.helpers import set_max_decimal_places

import gpxpy
import gpxpy.gpx
from bs4 import BeautifulSoup as bs

from tqdm import tqdm

logging.basicConfig(level=logging.DEBUG)

# parse kml

root = parser.parse(sys.stdin).getroot()
set_max_decimal_places(root, max_decimals={'longitude': 6,'latitude': 6})

logging.info('kml22gx validation: %r', Schema('kml22gx.xsd').validate(root))
logging.info('ogckml22 validation: %r', Schema('ogckml22.xsd').validate(root))

# https://developer.mozilla.org/en-US/docs/Web/XPath/Functions
# https://devhints.io/xpath

ns = '{http://www.opengis.net/kml/2.2}'

# discover ExtendedData fields
# TODO make the mapping to their display names configurable

fieldElements = root.Document.Schema.findall(ns + 'SimpleField')
fields = list(map(lambda f: f.get('name'), fieldElements))
for field in fields:
    logging.info(f'discovered ExtendedData field {field}')

# retrieve placemarks
    
placemarks = root.Document.Folder.findall(ns + 'Placemark')
logging.info(f'found {len(placemarks)} placemarks')

# write gpx

def find_text_for_field(sdata, name):
    return ''.join(sdata.xpath(f'./*[@name="{name}"]/text()')).strip()

def find_plain_text_for_field(sdata, name):
    return bs(find_text_for_field(sdata, name), features='lxml').get_text()

# TODO make configurable - this is from the USFS dataset

west_bounding_coordinate = -177.596546
east_bounding_coordinate = -8.244094
north_bounding_coordinate = 61.082222
south_bounding_coordinate = 11.358620

def validate_location(lat, lon, id):
    try:
        assert south_bounding_coordinate <= float(lat) <= north_bounding_coordinate
        assert west_bounding_coordinate <= float(lon) <= east_bounding_coordinate
    except AssertionError:
        logging.warning(f'placemark {id}: lat/lon {lat}, {lon} outside extent')

gpx = gpxpy.gpx.GPX()
count = 0
for e in tqdm(placemarks):
    try:
        name = e.name.text
        logging.info(f'found placemark {name}')
    except:
        logging.error('no placemark name field found - please configure one %r', e)
        name = 'UNKNOWN'
    try:
        lon, lat = e.Point.coordinates.text.split(',')
    except:
        logging.error('no Point subelement found - please configure lat/lon fields')
        sys.exit(2)
    if float(lon) > 0:
        # lat/lon probably in wrong order
        lat, lon = lon, lat
        logging.warning(f'placemark {id}: switched lat/lon {lat}, {lon}')
    validate_location(lat, lon, id)
    wpt = gpxpy.gpx.GPXWaypoint(latitude = lat, longitude = lon)
    wpt.name = name
    desc = ''
    for field in fields:
        fdata = find_plain_text_for_field(e.ExtendedData.SchemaData, field)
        if len(fdata) > 0:
            desc += field
            desc += ': '
            desc += fdata
            desc += '\n'
    wpt.description = desc
    gpx.waypoints.append(wpt)

print(gpx.to_xml())
