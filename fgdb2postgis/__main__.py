##
 # __main__.py
 #
 # Description: Export, Transform and load data from ESRI File Geodatabase to PostGIS
 # Author: George Ioannou
 # Copyright: Cartologic 2017
 #
 ##
import getopt, sys
from .filegdb import FileGDB
from .postgis import PostGIS
from .version import get_version

reload(sys)
sys.setdefaultencoding('utf8')

def show_usage():
	print "Usage:"
	print "  fgdb2postgis.py -v"
	print "  fgdb2postgis.py -h"
	print "  fgdb2postgis.py -f filegdb"
	print "                  -p postgis"
	print "                  --a_srs=a_srs"
	print "                  --t_srs=t_srs"
	print "                  --host=host"
	print "                  --port=port"
	print "                  --user=user"
	print "                  --password=password"

	sys.exit(1)

def show_version():
	print "Version: %s"%(get_version()) 
	sys.exit(1)

if len(sys.argv) not in [2,11]:
	show_usage()
else:
	try:
		options, remainder = getopt.getopt(sys.argv[1:], 'hvf:p:', ['fgdb=', 'pgdb=', 'a_srs=', 't_srs=', 'host=', 'port=', 'user=', 'password='])
	except getopt.GetoptError as err:
		print str(err)
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
		a_srs = arg
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

#-------------------------------------------------------------------------------
# Main - Instantiate the required database objects and perform the conversion
#
def main():

	filegdb = FileGDB(fgdb, a_srs)
	filegdb.info()
	filegdb.open_files()
	filegdb.process_domains()
	filegdb.process_subtypes()
	filegdb.process_relations()
	filegdb.process_schemas()
	filegdb.close_files()

	postgis = PostGIS(host, port, user, password, pgdb, t_srs)
	postgis.info()
	postgis.connect()
	postgis.update_views()
	postgis.create_schemas(filegdb)
	postgis.load_database(filegdb)
	postgis.apply_sql(filegdb)
	postgis.disconnect()

	filegdb.cleanup()

	print "\nComplete!"
