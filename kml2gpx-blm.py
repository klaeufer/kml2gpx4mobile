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

    #   <SimpleField name="FET_TYPE" type="int"/>
    #   <SimpleField name="FET_SUBTYPE" type="string"/>
    #   <SimpleField name="FET_NAME" type="string"/>
    #   <SimpleField name="ADM_UNIT_CD" type="string"/>
    #   <SimpleField name="ADMIN_ST" type="string"/>
    #   <SimpleField name="QC_REVIEWER" type="string"/>
    #   <SimpleField name="QC_DATE" type="string"/>
    #   <SimpleField name="QC_DELETE_FEATURE" type="string"/>
    #   <SimpleField name="QC_COMMENTS" type="string"/>
    #   <SimpleField name="DATA_SOURCE" type="string"/>
    #   <SimpleField name="ORIG_STATE_FET_TYPE" type="string"/>
    #   <SimpleField name="WEB_LINK" type="string"/>
    #   <SimpleField name="PHOTO_TEXT" type="string"/>
    #   <SimpleField name="created_user" type="string"/>
    #   <SimpleField name="created_date" type="string"/>
    #   <SimpleField name="last_edited_user" type="string"/>
    #   <SimpleField name="last_edited_date" type="string"/>
    #   <SimpleField name="UNIT_NAME" type="string"/>
    #   <SimpleField name="SOURCE" type="string"/>
    #   <SimpleField name="WEB_DISPLAY" type="string"/>
    #   <SimpleField name="PHOTO_LINK" type="string"/>
    #   <SimpleField name="PHOTO_THUMB" type="string"/>
    #   <SimpleField name="GlobalID" type="string"/>
    #   <SimpleField name="Original_GlobalID" type="string"/>
    #   <SimpleField name="LAT" type="float"/>
    #   <SimpleField name="LONG" type="float"/>


# fields in KML file exported from QGIS
#fields = {
#    'RECAREANAME':        'Name:        ',
#    'ACTIVITYNAME':       'Activity:    ',
#    'RECAREADESCRIPTION': 'Description: ',
#    'OPENSTATUS':         'Open/closed: ',
#    'OPEN_SEASON_START' : 'Open from:   ',
#}

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
        id = find_text_for_field(sdata, 'GlobalID')
        try:
            lon, lat = e.Point.coordinates.text.split(',')
        except:
            logging.info(f'placemark {id}: no Point found, using LON/LAT')
            lon = find_text_for_field(sdata, 'LON')
            lat = find_text_for_field(sdata, 'LAT')
        if float(lon) > 0:
            # lat/lon probably in wrong order
            lat, lon = lon, lat
            logging.warning(f'placemark {id}: switched lat/lon {lat}, {lon}')
        validate_location(lat, lon, id)
        if not is_location_within_filter_extent(lat, lon):
            logging.info(f'placemark {id}: outside filter extent, skipping')
            continue
        wpt = gpxpy.gpx.GPXWaypoint(latitude = lat, longitude = lon)
        wpt.name = find_plain_text_for_field(sdata, 'FET_NAME')
        try:
            logging.info(e.description)
            wpt.description = bs(e.description).text
        except:
            #logging.warning(f'placemark {id} has no description')
            pass
        gpx.waypoints.append(wpt)
    except:
        logging.error(f'placemark {id}: unrecoverable problem in input')

#print(len(gpx.waypoints))

print(gpx.to_xml())
