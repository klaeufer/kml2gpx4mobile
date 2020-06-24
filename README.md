# Purpose

Command-line converter from kml to gpx with a focus on placemarks for import into OsmAnd and similar mobile apps. 
Supports kml `ExtendedData` by folding them into the GPX desc element.
Aims to overcome the following limitations of existing alternatives:

- Command-line converters such as gpsbabel do not seem to support `ExtendedData`
- Online converters usually have a size limit.

This work is its initial stages. 
It succeeds in converting a 22 MB kml (USFS recreation opportunities) to gpx.
The screenshot shows some of the info carried over from kml `ExtendedData`.

# Dependencies

- pykml
- gpxpy
- BeautifulSoup
- tqdm
- ogr2ogr (optional, for converting Shapefiles to kml)

# Usage

```
ogr2ogr -f KML -mapFieldType Integer64=Integer FSRecreationOpportunities.kml S_USA.RECREATIONOPPORTUNITIES.shp
./kml2gpx.py < FSRecreationOpportunities.kml > FSRecreationOpportunities.gpx
```
