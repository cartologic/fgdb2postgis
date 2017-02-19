=============================
fgdb2postgis
=============================

Python library providing functionality for converting file esri/geodatabase to postgresql/postgis
The tool is solving the problem with geodatabase's subtypes, domains and relationships.
It is not focusing to provide options for GDAL/OGR in this initial release but it will in future releases.

Note that this library requires GDAL/OGR tools and ESRI ArcGIS to be installed in the system.

Installation
------------
This tool should be installed only on windows systems because of ArcGIS (Arcpy)

Install required packages::

    pip install numpy
    pip install psycopg2
    pip install pyyaml
    pip install git+https://github.com/gmioannou/archook.git

Install fgdb2postgis::

    pip install fgdb2postgis --process-dependency-links

Note that it does not automatically install GDAL/OGR tools or ESRI ArcGIS in your system.
You can install GDAL/OGR by using [OSGeo4W](https://trac.osgeo.org/osgeo4w/).

Usage
-----
Create a YAML file mapping file geodatabase's feature datasets, feature classes and tables to postgresql's schemas

Naming convention::

    filegdb: sample.gdb
       yaml: sample.gdb.yaml

Note that Yaml file should live in the same folder with the file geodatabase.

Yaml file example::

    Schemas:
      - Administrative
      - Epidemiology
      - Radioactivity
      - Seismic
    FeatureDatasets:
      Epidemiology:
      - Epidemiology
      Radioactivity:
      - Radioactivity
      Seismic:
      - Seismic
    FeatureClasses:
      Administrative:
        - sectors
        - governorates
        - sub_sectors
    Tables:
      Epidemiology:
      - EpidemiologyTS
      - EpidemiologyTST
      Radioactivity:
      - RadiationTS
      - RadiationTST
      Seismic:
      - EarthquakeTS
      - SeismicTST

Command line options::

    fgdb2postgis -h
    fgdb2postgis -f filegdb
                 -p postgis
                 --host=host
                 --port=port
                 --user=user
                 --password=password

Restrictions
------------

* DO NOT apply this tool in a production postgresql database.
* The postgresql database should exists and be EMPTY!
* The tool will OVERWRITE any tables having the same name with tables in filegdb.
