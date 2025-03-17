##
# __main__.py
#
# Description: Export, Transform and load data from ESRI File Geodatabase to PostGIS
# Author: George Ioannou
# Copyright: Cartologic 2017-2020
#
##
import getopt
import sys

from fgdb2postgis.filegdb import FileGDB
from fgdb2postgis.postgis import PostGIS
from fgdb2postgis.version import get_version


def show_usage():
    print("Usage:")
    print("  fgdb2postgis.py -v")
    print("  fgdb2postgis.py -h")
    print("  fgdb2postgis.py -f filegdb")
    print("                  -p postgis")
    print("                  --t_srs=t_srs")
    print("                  --host=host")
    print("                  --port=port")
    print("                  --user=user")
    print("                  --password=password")
    print("")
    print("Note: --a_srs is also accepted for backward compatibility but is ignored")

    sys.exit(1)


def show_version():
    print("Version: {0}".format(get_version()))
    sys.exit(1)


if len(sys.argv) not in [2, 10, 11]:
    show_usage()
else:
    try:
        options, remainder = getopt.getopt(sys.argv[1:], 'hvf:p:', [
                                           'fgdb=', 'pgdb=', 'a_srs=', 't_srs=', 'host=', 'port=', 'user=', 'password='])
    except getopt.GetoptError as err:
        print(str(err))
        show_usage()

for opt, arg in options:
    if opt == '-h':
        show_usage()
    elif opt == '-v':
        show_version()
    elif opt in ('-f'):
        fgdb = arg
    elif opt in ('-p'):
        pgdb = arg
    elif opt in ('--a_srs'):
        # Ignore a_srs, just accept it for backward compatibility
        pass
    elif opt in ('--t_srs'):
        t_srs = arg
    elif opt in ('--host'):
        host = arg
    elif opt in ('--port'):
        port = arg
    elif opt in ('--user'):
        user = arg
    elif opt in ('--password'):
        password = arg

# -------------------------------------------------------------------------------
# Main - Instantiate the required database objects and perform the conversion
#

def main():

    # Initialize FileGDB with just the workspace path
    filegdb = FileGDB(fgdb, t_srs)
    filegdb.info()
    filegdb.open_files()

    # Process schema elements
    filegdb.process_domains()
    filegdb.process_subtypes()
    filegdb.process_relations()
    filegdb.process_schemas()

    # Initialize PostGIS
    postgis = PostGIS(pgdb, host, port, user, password)
    postgis.info()

    # Load the database
    postgis.load_database(filegdb)

    # Process the database
    postgis.process_database(filegdb)

    # Close files
    filegdb.close_files()

    print("\nDone!")


# -------------------------------------------------------------------------------
# Main - Instantiate the required database objects and perform the conversion
#

if __name__ == "__main__":
    main()
