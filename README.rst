====================================================
File Geodatabase to PostGIS convertor (fgdb2postgis)
====================================================
Python package providing functionality for converting esri file geodatabase to postgresql/postgis.
The tool is solving the problem related to geodatabase's subtypes, domains and relationships classes by creating Indexes and foreign key constraints among the feature classes' tables, data tables and lookup tables in the target postgresql database. There is no provision though for GDAL/OGR options in this initial release but probably it will be in the next releases.

Note:
   This library requires GDAL/OGR libraries and ESRI ArcGIS to be installed in the system.

Installation
------------
This package should be installed only on windows systems because of ArcGIS (Arcpy) limitation.

Install required packages::

    pip install numpy
    pip install psycopg2
    pip install pyyaml
    pip install git+https://github.com/gmioannou/archook.git

Install fgdb2postgis::

    pip install fgdb2postgis

Note:
  It does not automatically install GDAL/OGR libraries or ESRI ArcGIS in your system.
  You can install GDAL/OGR from `OSGeo4W <https://trac.osgeo.org/osgeo4w/>`_ or use the installation of QGIS

Usage
-----
Create a yaml file mapping the file geodatabase's feature datasets, feature classes and tables to postgresql's schemas. It is required that the yaml file have the same name with the file geodatabase with the extension .yaml

Example::

    filegdb: sample.gdb
       yaml: sample.gdb.yaml

Note:
  The Yaml file should be located in the same folder with the file geodatabase.

|

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


Schemas:
  The schemas to be created in the target postgis database.

FeatureDatasets:
  Maps the feature datasets of the geodatabase to the schemas of the target postgis database

FeatureClasses:
  Maps the feature classes of the geodatabase that do not belong to any feature dataset to the schemas of the target postgis database

Tables:
  Maps the tables of the geodatabase to the schemas of target postgis database

|

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

* DO NOT apply this tool in a production postgis database!
* The target postgis database should exists and be EMPTY.
* The tool will OVERWRITE any tables having the same name with the tables in the file geodatabase.
