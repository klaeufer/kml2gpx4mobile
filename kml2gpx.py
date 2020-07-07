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

placemarks = root.xpath(
    '//k:Placemark',
    namespaces={'k': 'http://www.opengis.net/kml/2.2'})
logging.info(f'found {len(placemarks)} placemarks')

# TODO read these fields from the kml file itself!
# TODO make the mapping to their display names configurable

fields = {
'OPENSTATUS': 'Open/closed:  ',
'OPEN_SEASO': 'From:         ',
'OPEN_SEA_1': 'To:           ',
'OPERATIONA': 'Operational:  ',
'FEEDESCRIP': 'Fees:         ',
'RESERVATIO': 'Reservations: ',
'RESTRICTIO': 'Restrictions: ',
'MARKERACTI': 'Activities:   ',
'SPOTLIGHTD': 'Spotlighted:  ',
'ATTRACTION': 'Attraction:   ',
'ACCESSIBIL': 'Access:       ',
'FORESTNAME': 'Forest:       '
}

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

# TODO filter by extent - make configurable

# northeast
#west_filter = -97.5
#east_filter = -8.2
#north_filter = 49.5
#south_filter = 36.5

west_filter = -178
east_filter = -8
north_filter = 62
south_filter = 10

def is_location_within_filter_extent(lat, lon):
    return south_filter <= float(lat) <= north_filter and west_filter <= float(lon) <= east_filter

        
gpx = gpxpy.gpx.GPX()
count = 0
for e in tqdm(placemarks):
    try:
        sdata = e.ExtendedData.SchemaData
        id = find_text_for_field(sdata, 'RECAREAID')
        try:
            lon, lat = e.Point.coordinates.text.split(',')
        except:
            logging.info(f'placemark {id}: no Point found, using LON/LAT')
            lon = find_text_for_field(sdata, 'LONGITUDE')
            lat = find_text_for_field(sdata, 'LATITUDE')
        if float(lon) > 0:
            # lat/lon probably in wrong order
            lat, lon = lon, lat
            logging.warning(f'placemark {id}: switched lat/lon {lat}, {lon}')
        validate_location(lat, lon, id)
        if not is_location_within_filter_extent(lat, lon):
            logging.info(f'placemark {id}: outside filter extent, skipping')
            continue
        wpt = gpxpy.gpx.GPXWaypoint(latitude = lat, longitude = lon)
        wpt.name = find_text_for_field(sdata, 'RECAREANAM')
        desc = find_plain_text_for_field(sdata, 'RECAREADES')
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
        logging.error(f'placemark {id}: unrecoverable problem in input')

print(gpx.to_xml())
