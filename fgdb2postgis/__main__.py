##
 # __main__.py
 #
 # Description: Export, Transform and load data from ESRI File Geodatabase to PostGIS
 # Author: George Ioannou
 # Copyright: Cartologic 2017
 #
 ##
import getopt, sys
from filegdb import FileGDB
from postgis import PostGIS

def show_usage():
	print "Usage: fgdb2postgis.py -f filegdb -p postgis --host=host --port=port --user=user --password=password"
	sys.exit(1)

if len(sys.argv) != 9:
	show_usage()
else:
	try:
		options, remainder = getopt.getopt(sys.argv[1:], 'hf:p:', ['fgdb=', 'pgdb=', 'host=', 'port=', 'user=', 'password='])
	except getopt.GetoptError as err:
		print str(err)
		show_usage()

for opt, arg in options:
	if opt == '-h':
		show_usage()
	elif opt in ('-f'):
		fgdb = arg
	elif opt in ('-p'):
		pgdb = arg
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

	filegdb = FileGDB(fgdb)
	filegdb.info()
	filegdb.setenv()
	filegdb.open_files()
	filegdb.process_domains()
	filegdb.process_subtypes()
	filegdb.process_relations()
	filegdb.process_schemas()
	filegdb.close_files()

	postgis = PostGIS(host, port, user, password, pgdb)
	postgis.info()
	postgis.connect()
	postgis.update_views()
	postgis.create_schemas(filegdb)
	postgis.load_database(filegdb)
	postgis.apply_sql(filegdb)
	postgis.disconnect()

	print "\nComplete!"
