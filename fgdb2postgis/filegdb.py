##
 # filegdb.py
 #
 # Description: Read file geodatabase, create tables for subtypes and domains
 #              Prepare sql scripts for indexes and foreign key constraints
 # Author: George Ioannou
 # Copyright: Cartologic 2017
 #
 ##
import os
import yaml
from os import path

# locate and import arcpy
try:
	import archook
	archook.get_arcpy()
	import arcpy
except ImportError:
	print "Unable to locate arcpy module..."
	exit(1)

class FileGDB:
	def __init__(self, workspace, a_srs):
		self.workspace = workspace
		self.a_srs = a_srs
		self.workspace_path = ""
		self.sqlfolder_path = ""
		self.yamlfile_path = ""
		self.schemas = []
		self.feature_datasets = {}
		self.feature_classes = {}
		self.tables = {}
		self.init_paths()
		self.parse_yaml()
		self.indexes = []
		self.constraints = []

	#-------------------------------------------------------------------------------
	# Initialize file geodatabase environment
	#
	def init_paths(self):
		# workspace path
		workspace_path = path.join(os.getcwd(), self.workspace)
		workspace_dir = path.dirname(workspace_path)
		workspace_base = path.basename(workspace_path)

		# sqlfolder, yamlfile path
		sqlfolder_base = "%s.sql" % workspace_base
		yamlfile_base = "%s.yaml" % workspace_base
		sqlfolder_path = path.join(workspace_dir, sqlfolder_base)
		yamlfile_path = path.join(workspace_dir, yamlfile_base)

		# set current object instance props
		self.workspace_path = workspace_path
		self.sqlfolder_path = sqlfolder_path
		self.yamlfile_path = yamlfile_path

	def info(self):
		print "\nFileGDB Info:"
		print " Workspace: %s" % self.workspace_path
		print " Coord System: %s" % self.a_srs
		print " Sqlfolder: %s" % self.sqlfolder_path
		print " Yamlfile: %s" % self.yamlfile_path

	def setenv(self):
		print "\nSetting arcpy environment ..."
		arcpy.env.workspace = self.workspace
		arcpy.env.overwriteOutput = True

	#-------------------------------------------------------------------------------
	# Parse the yaml file and map data to schemas
	#
	def parse_yaml(self):
		# parse yaml file and map datasets, feature classes, tables to schemas
		if path.exists(self.yamlfile_path):
			yf = open(self.yamlfile_path)
			data_map = yaml.load(yf)

			for key_type, value_items in data_map.items():
				if (key_type == "Schemas"):
					self.schemas = value_items
				elif (key_type == "FeatureDatasets"):
					self.feature_datasets = value_items
				elif (key_type == "FeatureClasses"):
					self.feature_classes = value_items
				elif (key_type == "Tables"):
					self.tables = value_items
			yf.close()
		else:
			print "\nYaml file not found."
			print "Data will be loaded into the public schema!"

		# lookup_tables is a default schema and it will host subtypes, domains
		if 'lookup_tables' not in self.schemas:
			self.schemas.append('lookup_tables')

	#-------------------------------------------------------------------------------
	# Open sql files
	#
	def open_files(self):
		print "\nInitializing sql files ..."

		if not path.exists(self.sqlfolder_path):
			os.mkdir(self.sqlfolder_path)

		self.f_create_schemas = open(path.join(self.sqlfolder_path, "create_schemas.sql"), "w")
		self.f_split_schemas = open(path.join(self.sqlfolder_path, "split_schemas.sql"), "w")
		self.f_create_indexes = open(path.join(self.sqlfolder_path, "create_indexes.sql"), "w")
		self.f_create_constraints = open(path.join(self.sqlfolder_path, "create_constraints.sql"), "w")
		self.f_find_data_errors = open(path.join(self.sqlfolder_path, "find_data_errors.sql"), "w")
		self.f_fix_data_errors = open(path.join(self.sqlfolder_path, "fix_data_errors.sql"), "w")

		self.write_headers()

	#-------------------------------------------------------------------------------
	# close sql files
	#
	def close_files(self):
		print "\nClosing sql files ..."
		self.f_create_schemas.close()
		self.f_split_schemas.close()
		self.f_create_indexes.close()
		self.f_create_constraints.close()
		self.f_find_data_errors.close()
		self.f_fix_data_errors.close()

	#-------------------------------------------------------------------------------
	# Process domains
	# Convert domains to tables
	#
	def process_domains(self):
		print "\nProcessing domains ..."

		self.write_it(self.f_create_indexes, "\n-- Domains")
		self.write_it(self.f_create_constraints, "\n-- Domains")
		self.write_it(self.f_split_schemas, "\n-- Domains")

		# create table for each domain
		domains_list = arcpy.da.ListDomains(self.workspace)
		for domain in domains_list:
			self.create_domain_table(domain)

		# create fk constraints for data tables referencing domain tables
		tables_list = arcpy.ListTables()
		tables_list.sort()

		for table in tables_list:
			self.create_constraints_referencing_domains(table)

		# create fk constraints for feature classes referencing domain tables
		# stand-alone feature classes
		fc_list = arcpy.ListFeatureClasses("*", "")
		fc_list.sort()

		for fc in fc_list:
			self.create_constraints_referencing_domains(fc)

		# feature classes in feature datasets
		fds_list = arcpy.ListDatasets("*", "Feature")
		fds_list.sort()

		for fds in fds_list:
			fc_list = arcpy.ListFeatureClasses("*", "", fds)
			fc_list.sort()

			for fc in fc_list:
				self.create_constraints_referencing_domains(fc)

	#-------------------------------------------------------------------------------
	# Create domain table and insert records (list of values)
	#
	def create_domain_table(self, domain):
		domain_name = domain.name.replace(" ", "")
		domain_table = "%s_lut" % domain_name

		domain_field = "Code"
		domain_field_desc = "Description"
		domain_field_type = domain.type

		print " %s" % domain_table

		arcpy.CreateTable_management(self.workspace, domain_table)
		arcpy.AddField_management(domain_table, domain_field, domain_field_type)
		arcpy.AddField_management(domain_table, domain_field_desc, "String")

		if (domain.domainType == "CodedValue"):
			# sort coded values
			arcpy.SortCodedValueDomain_management(self.workspace, domain.name, domain_field, "Ascending")

			# insert rows in domain table
			cur = arcpy.da.InsertCursor(domain_table, "*")
			oid = 1
			for code, desc in domain.codedValues.items():
				# print " %s %s" % (code, desc)
				cur.insertRow([oid, code, desc])
				oid += 1
			del cur
		elif (domain.domainType == "Range"):
			# insert rows in domain table
			cur = arcpy.da.InsertCursor(domain_table, "*")
			cur.insertRow([0, domain.range[0], "Min value"])
			cur.insertRow([1, domain.range[1], "Max value"])
			del cur

			# print range min and max values
			print " %d %s" % (domain.range[0], "Min value")
			print " %d %s" % (domain.range[1], "Max value")
		else:
			print " Unknown domain type"
			return

		# create index
		self.create_index(domain_table, domain_field)
		self.split_schemas(domain_table, "lookup_tables")

	#-------------------------------------------------------------------------------
	# Create foraign key constraints to tables referencing domain tables
	#
	def create_constraints_referencing_domains(self, layer):
		dmcode = "Code"
		dmcode_desc = "Description"

		subtypes = arcpy.da.ListSubtypes(layer)

		for stcode, v1 in subtypes.iteritems():
			for k2, v2 in v1.iteritems():
				if k2 == 'Default':
					stdefault = v2

				elif k2 == 'Name':
					stname = v2

				elif k2 == 'SubtypeField':
					if v2 != '':
						# stfield = v2.upper()
						stfield = v2
						sttable = "%s_%s_lut" % (layer, stfield)
					else:
						stfield = '--'
						sttable = '--'

				elif k2 == 'FieldValues':
					for dmfield, v3 in v2.iteritems():
						if v3[1] is not None:
							dmtable = v3[1].name + '_lut'
							self.create_foreign_key_constraint(layer, dmfield, dmtable, dmcode)


	#-------------------------------------------------------------------------------
	# Process subtypes
	# Convert subtypes to tables
	#
	def process_subtypes(self):
		print "\nProcessing subtypes ..."

		self.write_it(self.f_create_indexes, "\n-- Subtypes")
		self.write_it(self.f_create_constraints, "\n-- Subtypes")
		self.write_it(self.f_split_schemas, "\n-- Subtypes")

		# create subtypes table for tables
		tables_list = arcpy.ListTables()
		tables_list.sort()

		for table in tables_list:
			self.create_subtypes_table(table)

		# create subtypes table for feature classes
		# stand-alone feature classes
		fc_list = arcpy.ListFeatureClasses("*", "")
		fc_list.sort()

		for fc in fc_list:
			self.create_subtypes_table(fc)

		# feature classes in feature datasets
		fds_list = arcpy.ListDatasets("*", "Feature")
		fds_list.sort()

		for fds in fds_list:
			fc_list = arcpy.ListFeatureClasses("*", "", fds)
			fc_list.sort()

			for fc in fc_list:
				self.create_subtypes_table(fc)

	#-------------------------------------------------------------------------------
	# Create subtypes table for layer - field and insert records (list of values)
	#
	def create_subtypes_table(self, layer):
		subtypes = arcpy.da.ListSubtypes(layer)

		subtype_fields = {key: value['SubtypeField'] for key, value in subtypes.iteritems()}
		subtype_values = {key: value['Name'] for key, value in subtypes.iteritems()}

		key, field = subtype_fields.items()[0]

		if key != 0:

			# convert to upper case to avoid esri filed alias
			field = field.upper()

			# find subtype field type
			for f in arcpy.ListFields(layer):
				if f.name.upper() == field:
					field_type = f.type

			subtypes_table = "%s_%s_lut" % (layer, field)
			print(" %s" % subtypes_table)

			# create subtype table
			arcpy.CreateTable_management(self.workspace, subtypes_table)
			arcpy.AddField_management(subtypes_table, field, field_type)
			arcpy.AddField_management(subtypes_table, "Description", "String")

			# insert rows
			cur = arcpy.da.InsertCursor(subtypes_table, "*")
			oid = 1
			for code, desc in subtype_values.iteritems():
				# print "  %s %s" % (code, desc)
				cur.insertRow([oid, code, desc])
				oid += 1

			del cur

			self.create_index(subtypes_table, field)
			self.create_foreign_key_constraint(layer, field, subtypes_table, field)
			self.split_schemas(subtypes_table, "lookup_tables")


	#-------------------------------------------------------------------------------
	# Process relations
	# Create necessary indexes and foreign key constraints to support each relation
	#
	def process_relations(self):
		print "\nProcessing relations ..."

		self.write_it(self.f_create_indexes, "\n-- Relations (tables and feature classes)")
		self.write_it(self.f_create_constraints, "\n-- Relations (tables and feature classes)")

		relClassSet = self.get_relationship_classes()

		for relClass in relClassSet:
			rel = arcpy.Describe(relClass)
			if rel.isAttachmentRelationship:
				continue

			rel_origin_table = rel.originClassNames[0]
			rel_destination_table = rel.destinationClassNames[0]

			rel_primary_key = rel.originClassKeys[0][0]
			rel_foreign_key = rel.originClassKeys[1][0]

			print " %s" % rel.name
			# print " %s -> %s" % (rel_origin_table, rel_destination_table)

			self.create_index(rel_origin_table, rel_primary_key)
			self.create_foreign_key_constraint(rel_destination_table, rel_foreign_key, rel_origin_table, rel_primary_key)

			# prcess data errors (fk)
			str_data_errors_fk = '\\echo %s (%s) -> %s (%s);' % (rel_destination_table, rel_foreign_key, rel_origin_table, rel_primary_key)
			self.write_it(self.f_find_data_errors, str_data_errors_fk)

			str_data_errors = 'SELECT COUNT(*) FROM "%s" dest WHERE NOT EXISTS (SELECT 1 FROM "%s" orig WHERE dest."%s" = orig."%s");'
			str_data_errors = str_data_errors % (rel_destination_table, rel_origin_table, rel_foreign_key, rel_primary_key)

			self.write_it(self.f_find_data_errors, str_data_errors)

			str_fix_errors_1 = 'INSERT INTO "%s" ("%s")' % (rel_origin_table, rel_primary_key)
			str_fix_errors_2 = 'SELECT DISTINCT detail."%s" \n  FROM "%s" AS detail \n LEFT JOIN "%s" AS master ON detail."%s" = master."%s" \n WHERE master.id IS NULL;\n'
			str_fix_errors_2 = str_fix_errors_2 % (rel_foreign_key, rel_destination_table, rel_origin_table, rel_foreign_key, rel_primary_key)

			self.write_it(self.f_fix_data_errors, str_fix_errors_1)
			self.write_it(self.f_fix_data_errors, str_fix_errors_2)

	#-------------------------------------------------------------------------------
	# Prepare relationship classes set and return it to the calling routine
	#
	def get_relationship_classes(self):
		# initiate feature classes list
		fcs = []

		# get feature classes and tables at geodatabase's root
		for item in arcpy.ListFeatureClasses("*"):
			fcs.append(item)
		for item in arcpy.ListTables("*"):
			fcs.append(item)

		# get fetature classes and tables within feature datasets
		fds = arcpy.ListDatasets("*","Feature")
		for fd in fds:
			arcpy.env.workspace = self.workspace + '\\' + fd
			for fc in arcpy.ListFeatureClasses("*"):
				fcs.append(fd + '/' + fc)
			for tb in arcpy.ListTables("*"):
				fcs.append(fd + '/' + tb)

		# create relationship classes set
		arcpy.env.workspace = self.workspace
		relClasses = set()
		for i,fc in enumerate(fcs):
			desc = arcpy.Describe(fc)
			for j,rel in enumerate(desc.relationshipClassNames):
				relClasses.add(rel)

		return relClasses


	#-------------------------------------------------------------------------------
	# Process Schemas
	# Prepare sql to split Tables and Feature Classes in Schemas
	#
	def process_schemas(self):
		print "\nProcessing schemas ..."

		# create extension postgis
		str_create_extension = "\nCREATE EXTENSION IF NOT EXISTS postgis;"
		self.write_it(self.f_create_schemas, str_create_extension)

		# create schemas
		for schema in self.schemas:
			if schema == 'public':
				continue

			str_drop_schema = '\nDROP SCHEMA IF EXISTS \"%s\" CASCADE;' % schema
			str_create_schema = 'CREATE SCHEMA \"%s\";' % schema
			self.write_it(self.f_create_schemas, str_drop_schema)
			self.write_it(self.f_create_schemas, str_create_schema)

		# split feature classes within feature datasets to schemas
		self.write_it(self.f_split_schemas, "\n-- FeatureDatasets:")
		print " FeatureDatasets"
		for schema, datasets in self.feature_datasets.items():
			if schema == 'public':
				continue

			for fds in datasets:
				fc_list = arcpy.ListFeatureClasses("*", "", fds)
				fc_list.sort()
				for fc in fc_list:
					self.split_schemas(fc, schema)

		# split feature classes outside of feature datasets to schemas
		self.write_it(self.f_split_schemas, "\n-- FeatureClasses:")
		print " FeatureClasses"
		for schema, fcs in self.feature_classes.items():
			if schema == 'public':
				continue

			for fc in fcs:
				if arcpy.Exists(fc):
					self.split_schemas(fc, schema)

		# split tables to schemas
		self.write_it(self.f_split_schemas, "\n-- Tables:")
		print " Tables"
		for schema, tables in self.tables.items():
			if schema == 'public':
				continue

			for table in tables:
				if arcpy.Exists(table):
					self.split_schemas(table, schema)

	#-------------------------------------------------------------------------------
	# Compose and write sql to alter the schema of a table
	#
	def split_schemas(self, table, schema):
		str_split_schemas = "ALTER TABLE \"%s\" SET SCHEMA \"%s\";" % (table, schema)
		self.write_it(self.f_split_schemas, str_split_schemas)

	#-------------------------------------------------------------------------------
	# Create indexes
	#
	def create_index(self, table, field):
		idx_name = "%s_%s_idx" % (table, field)

		if idx_name not in self.indexes:
			self.indexes.append(idx_name)
			str_index = "CREATE UNIQUE INDEX \"%s\" ON \"%s\" (\"%s\"); \n" % (idx_name, table, field)
			self.write_it(self.f_create_indexes, str_index)

	#-------------------------------------------------------------------------------
	# Create foreign key constraints
	#
	def create_foreign_key_constraint(self, table_details, fkey, table_master, pkey):
		fkey_name = "%s_%s_%s_fkey" % (table_details, fkey, table_master)

		if fkey_name not in self.constraints:
			self.constraints.append(fkey_name)
			str_constraint = 'ALTER TABLE "%s" ADD CONSTRAINT "%s" FOREIGN KEY ("%s") REFERENCES "%s" ("%s") NOT VALID; \n'
			str_constraint = str_constraint % (table_details, fkey_name, fkey, table_master, pkey)
			self.write_it(self.f_create_constraints, str_constraint)

	#-------------------------------------------------------------------------------
	# Write headers to sql files
	#
	def write_headers(self):
		str_message = "SET client_min_messages TO warning;"

		self.write_it(self.f_create_schemas, str_message)
		self.write_it(self.f_create_indexes, str_message)
		self.write_it(self.f_create_constraints, str_message)
		self.write_it(self.f_split_schemas, str_message)
		self.write_it(self.f_fix_data_errors, str_message)

	#-------------------------------------------------------------------------------
	# Write string to given open file
	#
	def write_it(self, out_file, string):
		out_file.write(string + "\n")
