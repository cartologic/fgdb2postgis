====================================================
File Geodatabase to PostGIS converter (fgdb2postgis)
====================================================
The aim of this tool is to convert an ESRI file Geodatabase to a PostGIS database maintaining data, domains, subtypes and relationships.
The tool will copy over the feature classes as postgis layers and the tables as standard tables. The domains and subtypes will be converted to PostgreSQL lookup tables.
The tool will then create all necessary indexes and constraints to maintain the required relates between the layers, tables and lookup tables.
To recreate the same experience of the domains and subtypes in QGIS using the output data, please install the plugin `Data Manager <https://github.com/cartologic/qgis-datamanager-plugin>`_.
Now you can have domain experience in QGIS that is stored in the database and not in the QGIS project.

.. note::
   This library requires GDAL/OGR libraries and ESRI ArcGIS to be installed in the system.

Installation
------------
This package should be installed only on windows systems because of ArcGIS (Arcpy) limitation.

Install required packages::

    pip install numpy>=1.12.0
    pip install psycopg2>=2.6.2
    pip install pyyaml>=3.12
    pip install archook==1.1.0

Install fgdb2postgis::

    pip install fgdb2postgis

.. note::

 * This tool requires to have GDAL/OGR libraries and ArcGIS 10.3 or later installed.
 * ESRI Python packages usually under C:\Python27\ArcGIS10.* might not have pip included make sure to
    * install pip if not already installed
    * setup ESRI python and GDAL/OGR in the windows path

Usage
-----
Create a yaml file mapping the file geodatabase's feature datasets, feature classes and tables to postgresql's schemas. It is required that the yaml file have the same name with the file geodatabase with the extension .yaml

Example::

    filegdb: sample.gdb
       yaml: sample.gdb.yaml

.. note::
  The Yaml file should be located in the same folder with the file geodatabase.
  If run without the yaml file will convert the full database and load it into the public schema.
  The schema lookup_tables will always be created regardless of the yaml file.

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
  Mapping of the geodatabase's feature datasets to the schemas of the target postgis database

FeatureClasses:
  Mapping of the geodatabase's feature classes that do not belong to any feature dataset to the schemas of the target postgis database

Tables:
  Mapping of the geodatabase's tables to the schemas of target postgis database

|

Command line options::

    fgdb2postgis -h
    fgdb2postgis -f filegdb
                 -p postgis
                 --host=host
                 --port=port
                 --user=user
                 --password=password

.. tip::
  * This tool is tested with PostGRES v 9.5 and PostGIS v 2.2
  * Currently the tool support only Latin Name fields and suptypes, domain values can be in any   language, make sure to set the corresponding windows domain

.. warning::
  * DO NOT apply this tool in a production postgis database!
  * The target postgis database should exists and be EMPTY.
  * The tool will OVERWRITE any tables having the same name with the tables in the file geodatabase.

Credits
-------

Credit goes to `James Ramm <ramshacklerecording@gmail.com>`_ who kindly developed and shared the archook package.

License
-------
GNU Public License (GPL) Version 3
