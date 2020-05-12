====================================================
File Geodatabase to PostGIS converter (fgdb2postgis)
====================================================
The aim of this tool is to convert an ESRI file Geodatabase to a PostGIS database maintaining data, domains, subtypes and relationships.
The tool will copy over the feature classes as postgis layers and the tables as standard tables. The domains and subtypes will be converted to PostgreSQL lookup tables.
The tool will then create all necessary indexes and constraints to maintain the required relates between the layers, tables and lookup tables.
To recreate the same experience of the domains and subtypes in QGIS using the output data, please install the plugin `Data Manager <https://github.com/cartologic/qgis-datamanager-plugin>`_.
Now you can have domain experience in QGIS that is stored in the database and not in the QGIS project.

.. note::
   This library requires GDAL/OGR libraries and ESRI ArcGIS Pro to be installed.

Installation
------------
This package should be installed on windows systems into ArcGIS Pro conda python environment. (because of Arcpy)

Install required packages::
  * pip install numpy>=1.12.0
  * pip install psycopg2>=2.6.2
  * pip install ruamel.yaml>=0.15.35
  * pip install awesome-slugify==1.6.5

Install fgdb2postgis::

  * pip install fgdb2postgis

.. note::

  * This tool requires to have GDAL/OGR libraries and ArcGIS 10.3 or later installed.
  * ESRI Python packages usually under C:\Python27\ArcGIS10.* might not have pip included make sure to

    * Install Anaconda/Miniconda
    * Install pip if not already installed
    * Setup ESRI python and GDAL/OGR in windows path environment variable

  * Activate python environment
  
    * activate C:\\Users\\<user>\\AppData\\Local\\ESRI\\conda\\envs\\<esri-py>

Usage
-----
Create a yaml file mapping the file geodatabase's feature datasets, feature classes and tables to postgresql's schemas. It is required that the yaml file have the same name with the file geodatabase with the extension .yaml
If the yaml file does not exist it will be created automatically, splitting the file geodatabase feature datasets to postgresql schemas
Since we have the yaml file with the entire schema of the file geodatabase we can modified it and run the tool again.

Example::

    filegdb: sample.gdb
       yaml: sample.gdb.yml

.. note::
  The yaml file should be located in the same folder and having the same name as the file geodatabase.
  If the yaml file does not exist it will be created by inspecting the file geodatabase and converting the feature datasets into schemas.
  The schema lookup_tables will always be created regardless of the yaml file.

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

Command line options::

    fgdb2postgis -h
    fgdb2postgis -f filegdb
                -p postgis
                --host=host
                --port=port
                --user=user
                --password=password
                --a_srs=a_srs
                --t_srs=t_srs

.. tip::
  * This tool is tested with:

    * GDAL/OGR v 1.11.4
    * PostgreSQL v 11.7
    * PostGIS v 2.5
    * ArcGIS Pro v 2.5.1

  * The tool supports only Latin characters for field names and suptypes while domain values and descriptions might be in any locale.

.. warning::
  * DO NOT apply this tool in a production postgis database!
  * The target postgis database should exists and be EMPTY.
  * The tool will OVERWRITE any tables having the same name with the tables in the file geodatabase.

Last Update:
  * Migrate to Python 3.X (ArcGIS Pro)
  * 12 May 2020

License
-------

MIT License

Copyright (c) 2020 George Ioannou `<gmioannou@gmail.com> <gmioannou@gmail.com>`_

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.