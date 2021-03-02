##
# filegdb.py
#
# Description: Read file geodatabase, create tables for subtypes and domains
#              Prepare sql scripts for indexes and foreign key constraints
# Author: George Ioannou
# Copyright: Cartologic 2017-2020
#
##
from os import getcwd, mkdir, path

from ruamel.yaml import YAML
from slugify import slugify

import arcpy

yaml = YAML()


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
        self.indexes = []
        self.constraints = []
        self.init_paths()
        self.setenv()
        self.parse_yaml()

    # -------------------------------------------------------------------------------
    # Initialize file geodatabase environment
    #
    def init_paths(self):
        # workspace path
        workspace_path = path.join(getcwd(), self.workspace)
        workspace_dir = path.dirname(workspace_path)
        workspace_base = path.basename(workspace_path)

        # sqlfolder, yamlfile path
        sqlfolder_base = "{}.sql".format(workspace_base)
        yamlfile_base = "{}.yml".format(workspace_base)
        sqlfolder_path = path.join(workspace_dir, sqlfolder_base)
        yamlfile_path = path.join(workspace_dir, yamlfile_base)

        # set current object instance props
        self.workspace_path = workspace_path
        self.sqlfolder_path = sqlfolder_path
        self.yamlfile_path = yamlfile_path

    def info(self):
        print("\nFileGDB Info:")
        print(" Workspace: {0} ({1})".format(self.workspace_path, self.a_srs))
        print(" Sqlfolder: {0}".format(self.sqlfolder_path))
        print(" Yamlfile: {0}".format(self.yamlfile_path))

    def setenv(self):
        print("\nSetting arcpy environment ...")
        arcpy.env.workspace = self.workspace
        arcpy.env.overwriteOutput = True

    # -------------------------------------------------------------------------------
    # Parse the yaml file and map data to schemas
    #
    def parse_yaml(self):
        # parse yaml file and map datasets, feature classes, tables to schemas
        if not path.exists(self.yamlfile_path):
            print("\nCreating default YAML file ...")
            self.create_yaml()

        with open(self.yamlfile_path, 'r') as ymlfile:
            data_map = yaml.load(ymlfile)
            for key_type, value_items in data_map.items():
                if (key_type == "Schemas"):
                    self.schemas = value_items
                elif (key_type == "FeatureDatasets"):
                    self.feature_datasets = value_items
                elif (key_type == "FeatureClasses"):
                    self.feature_classes = value_items
                elif (key_type == "Tables"):
                    self.tables = value_items

        # lookup_tables is a default schema and it will host subtypes, domains
        if 'lookup_tables' not in self.schemas:
            self.schemas.append('lookup_tables')

    # -------------------------------------------------------------------------------
    # Open sql files
    #
    def open_files(self):
        print("\nInitializing sql files ...")

        if not path.exists(self.sqlfolder_path):
            mkdir(self.sqlfolder_path)

        self.f_create_schemas = open(
            path.join(self.sqlfolder_path, "create_schemas.sql"), "w")
        self.f_split_schemas = open(
            path.join(self.sqlfolder_path, "split_schemas.sql"), "w")
        self.f_create_indexes = open(
            path.join(self.sqlfolder_path, "create_indexes.sql"), "w")
        self.f_create_constraints = open(
            path.join(self.sqlfolder_path, "create_constraints.sql"), "w")
        self.f_find_data_errors = open(
            path.join(self.sqlfolder_path, "find_data_errors.sql"), "w")
        self.f_fix_data_errors = open(
            path.join(self.sqlfolder_path, "fix_data_errors.sql"), "w")

        self.write_headers()

    # -------------------------------------------------------------------------------
    # close sql files
    #
    def close_files(self):
        print("\nClosing sql files ...")
        self.f_create_schemas.close()
        self.f_split_schemas.close()
        self.f_create_indexes.close()
        self.f_create_constraints.close()
        self.f_find_data_errors.close()
        self.f_fix_data_errors.close()

    # -------------------------------------------------------------------------------
    # Process domains
    # Convert domains to tables
    #
    def process_domains(self):
        print("\nProcessing domains ...")

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

    # -------------------------------------------------------------------------------
    # Create domain table (list of values)
    #
    def create_domain_table(self, domain):
        domain_name = slugify(domain.name, separator='_', lowercase=False)
        domain_table = "{}_lut".format(domain_name)

        domain_field = "Code"
        domain_field_desc = "Description"

        print(" {}".format(domain_table))

        if not arcpy.Exists(domain_table):
            arcpy.DomainToTable_management(
                self.workspace, domain.name, domain_table, domain_field, domain_field_desc)

        # create index
        self.create_index(domain_table, domain_field)
        self.split_schemas(domain_table, "lookup_tables")

    # -------------------------------------------------------------------------------
    # Create foraign key constraints to tables referencing domain tables
    #
    def create_constraints_referencing_domains(self, layer):
        dmcode = "Code"
        dmcode_desc = "Description"
        subtypes = {}

        try:
            subtypes = arcpy.da.ListSubtypes(layer)
        except:
            # By default any other errors will be caught here
            e = sys.exc_info()[1]
            print(e.args[0])

        for stcode, v1 in subtypes.items():
            for k2, v2 in v1.items():
                if k2 == 'Default':
                    stdefault = v2

                elif k2 == 'Name':
                    stname = v2

                elif k2 == 'SubtypeField':
                    if v2 != '':
                        stfield = v2
                        sttable = "{0}_{1}_lut".format(layer, stfield)
                    else:
                        stfield = '--'
                        sttable = '--'

                elif k2 == 'FieldValues':
                    for dmfield, v3 in v2.items():
                        if v3[1] is not None:
                            dmname = slugify(
                                v3[1].name, separator='_', lowercase=False)
                            dmtable = dmname + '_lut'
                            self.create_foreign_key_constraint(
                                layer, dmfield, dmtable, dmcode)

    # -------------------------------------------------------------------------------
    # Process subtypes
    # Convert subtypes to tables
    #

    def process_subtypes(self):
        print("\nProcessing subtypes ...")

        self.write_it(self.f_create_indexes, "\n-- Subtypes")
        self.write_it(self.f_create_constraints, "\n-- Subtypes")
        self.write_it(self.f_split_schemas, "\n-- Subtypes")

        # create subtypes table for tables
        tables_list = arcpy.ListTables()
        tables_list.sort()

        for table in tables_list:
            self.create_subtypes_table(table)

        # create subtypes table for stand-alone featureclasses
        fc_list = arcpy.ListFeatureClasses("*", "")
        fc_list.sort()

        for fc in fc_list:
            self.create_subtypes_table(fc)

        # create subtypes table for featureclasses in datasets
        fds_list = arcpy.ListDatasets("*", "Feature")
        fds_list.sort()

        for fds in fds_list:
            fc_list = arcpy.ListFeatureClasses("*", "", fds)
            fc_list.sort()

            for fc in fc_list:
                self.create_subtypes_table(fc)

    # -------------------------------------------------------------------------------
    # Create subtypes table for layer/field and insert records (list of values)
    #
    def create_subtypes_table(self, layer):
        subtypes_dict = {}

        try:
            subtypes_dict = arcpy.da.ListSubtypes(layer)
        except:
            # By default any other errors will be caught here
            e = sys.exc_info()[1]
            print(e.args[0])

        if subtypes_dict:

            subtype_fields = {key: value['SubtypeField']
                              for key, value in subtypes_dict.items()}
            subtype_values = {key: value['Name']
                              for key, value in subtypes_dict.items()}

            key, field = list(subtype_fields.items())[0]

            if len(field) > 0:

                # find subtype field type
                field_type = None
                for f in arcpy.ListFields(layer):
                    if f.name == field:
                        field_type = f.type

                # convert field to upper case and try again if not found
                if field_type == None:
                    field = field.upper()
                    for f in arcpy.ListFields(layer):
                        if f.name.upper() == field:
                            field_type = f.type

                subtypes_table = "{0}_{1}_lut".format(layer, field)
                subtypes_table = slugify(
                    subtypes_table, separator='_', lowercase=False)
                print(" {}".format(subtypes_table))

                if not arcpy.Exists(subtypes_table):
                    # create subtypes table
                    arcpy.CreateTable_management(self.workspace, subtypes_table)
                    arcpy.AddField_management(subtypes_table, field, field_type)
                    arcpy.AddField_management(
                        subtypes_table, "Description", "String")

                    # insert records (list of values)
                    cur = arcpy.da.InsertCursor(subtypes_table, "*")
                    oid = 1
                    for code, desc in subtype_values.items():
                        # print("  {0} {1}".format(code, desc))
                        cur.insertRow([oid, code, desc])
                        oid += 1

                    del cur

                self.create_index(subtypes_table, field)
                self.create_foreign_key_constraint(
                    layer, field, subtypes_table, field)
                self.split_schemas(subtypes_table, "lookup_tables")

    # -------------------------------------------------------------------------------
    # Process relations
    # Create necessary indexes and foreign key constraints to support each relation
    #

    def process_relations(self):
        print("\nProcessing relations ...")

        self.write_it(self.f_create_indexes,
                      "\n-- Relations (tables and feature classes)")
        self.write_it(self.f_create_constraints,
                      "\n-- Relations (tables and feature classes)")

        relClassSet = self.get_relationship_classes()

        for relClass in relClassSet:
            rel = arcpy.Describe(relClass)
            if rel.isAttachmentRelationship:
                continue

            rel_origin_table = rel.originClassNames[0]
            rel_destination_table = rel.destinationClassNames[0]

            rel_primary_key = rel.originClassKeys[0][0]
            rel_foreign_key = rel.originClassKeys[1][0]

            # convert primary/foreign key to uppercase if not found
            if rel_primary_key not in [field.name for field in arcpy.ListFields(rel_origin_table)]:
                rel_primary_key = rel.originClassKeys[0][0].upper()

            if rel_foreign_key not in [field.name for field in arcpy.ListFields(rel_destination_table)]:
                rel_foreign_key = rel.originClassKeys[1][0].upper()

            print(" {}".format(rel.name))
            # print(" {0} -> {1}".format(rel_origin_table, rel_destination_table))

            self.create_index(rel_origin_table, rel_primary_key)
            self.create_foreign_key_constraint(
                rel_destination_table, rel_foreign_key, rel_origin_table, rel_primary_key)

            # prcess data errors (fk)
            str_data_errors_fk = '\\echo {0} ({1}) -> {2} ({3});'.format(
                rel_destination_table, rel_foreign_key, rel_origin_table, rel_primary_key)
            self.write_it(self.f_find_data_errors, str_data_errors_fk)

            str_data_errors = 'SELECT COUNT(*) FROM "{0}" dest WHERE NOT EXISTS (SELECT 1 FROM "{1}" orig WHERE dest."{2}" = orig."{3}");'
            str_data_errors = str_data_errors.format(
                rel_destination_table, rel_origin_table, rel_foreign_key, rel_primary_key)

            self.write_it(self.f_find_data_errors, str_data_errors)

            str_fix_errors_1 = 'INSERT INTO "{0}" ("{1}")'.format(
                rel_origin_table, rel_primary_key)
            str_fix_errors_2 = 'SELECT DISTINCT detail."{0}" \n  FROM "{1}" AS detail \n LEFT JOIN "{2}" AS master ON detail."{3}" = master."{4}" \n WHERE master.id IS NULL;\n'
            str_fix_errors_2 = str_fix_errors_2.format(
                rel_foreign_key, rel_destination_table, rel_origin_table, rel_foreign_key, rel_primary_key)

            self.write_it(self.f_fix_data_errors, str_fix_errors_1)
            self.write_it(self.f_fix_data_errors, str_fix_errors_2)

    # -------------------------------------------------------------------------------
    # Create relationship classes Set and return it to the calling routine
    #
    def get_relationship_classes(self):

        # get featureclasses outside of datasets
        fc_list = arcpy.ListFeatureClasses("*")

        # get fetatureclasses within datasets
        fds_list = arcpy.ListDatasets("*", "Feature")
        for fds in fds_list:
            fc_list += arcpy.ListFeatureClasses("*", "", fds)

        # get tables
        fc_list += arcpy.ListTables("*")

        # create relationship classes set
        relClasses = set()
        for i, fc in enumerate(fc_list):
            desc = arcpy.Describe(fc)
            for j, rel in enumerate(desc.relationshipClassNames):
                relClasses.add(rel)

        return relClasses

    # -------------------------------------------------------------------------------
    # Process Schemas
    # Prepare sql to split Tables and Feature Classes in Schemas
    #
    def process_schemas(self):
        print("\nProcessing schemas ...")

        # create extension postgis
        str_create_extension = "\nCREATE EXTENSION IF NOT EXISTS postgis;"
        self.write_it(self.f_create_schemas, str_create_extension)

        # create schemas
        for schema in self.schemas:
            if schema == 'public':
                continue

            str_drop_schema = '\nDROP SCHEMA IF EXISTS \"{0}\" CASCADE;'.format(
                schema)
            str_create_schema = 'CREATE SCHEMA \"{0}\";'.format(schema)
            self.write_it(self.f_create_schemas, str_drop_schema)
            self.write_it(self.f_create_schemas, str_create_schema)

        # split feature classes within feature datasets to schemas
        self.write_it(self.f_split_schemas, "\n-- FeatureDatasets:")
        print(" FeatureDatasets")
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
        print(" FeatureClasses")
        for schema, fcs in self.feature_classes.items():
            if schema == 'public':
                continue

            for fc in fcs:
                if arcpy.Exists(fc):
                    self.split_schemas(fc, schema)

        # split tables to schemas
        self.write_it(self.f_split_schemas, "\n-- Tables:")
        print(" Tables")
        for schema, tables in self.tables.items():
            if schema == 'public':
                continue

            for table in tables:
                if arcpy.Exists(table):
                    self.split_schemas(table, schema)

    # -------------------------------------------------------------------------------
    # Compose and write sql to alter the schema of a table
    #
    def split_schemas(self, table, schema):
        str_split_schemas = "ALTER TABLE \"{0}\" SET SCHEMA \"{1}\";".format(
            table, schema)
        self.write_it(self.f_split_schemas, str_split_schemas)

    # -------------------------------------------------------------------------------
    # Create indexes
    #
    def create_index(self, table, field):
        idx_name = "{0}_{1}_idx".format(table, field)

        if idx_name not in self.indexes:
            self.indexes.append(idx_name)
            str_index = "CREATE UNIQUE INDEX \"{0}\" ON \"{1}\" (\"{2}\"); \n".format(
                idx_name, table, field)
            self.write_it(self.f_create_indexes, str_index)

    # -------------------------------------------------------------------------------
    # Create foreign key constraints
    #
    def create_foreign_key_constraint(self, table_details, fkey, table_master, pkey):
        fkey_name = "{0}_{1}_{2}_fkey".format(
            table_details, fkey, table_master)

        if fkey_name not in self.constraints:
            self.constraints.append(fkey_name)
            str_constraint = 'ALTER TABLE "{0}" ADD CONSTRAINT "{1}" FOREIGN KEY ("{2}") REFERENCES "{3}" ("{4}") NOT VALID; \n'
            str_constraint = str_constraint.format(
                table_details, fkey_name, fkey, table_master, pkey)
            self.write_it(self.f_create_constraints, str_constraint)

    # -------------------------------------------------------------------------------
    # Write headers to sql files
    #
    def write_headers(self):
        str_message = "SET client_min_messages TO warning;"

        self.write_it(self.f_create_schemas, str_message)
        self.write_it(self.f_create_indexes, str_message)
        self.write_it(self.f_create_constraints, str_message)
        self.write_it(self.f_split_schemas, str_message)
        self.write_it(self.f_fix_data_errors, str_message)

    # -------------------------------------------------------------------------------
    # Write string to given open file
    #
    def write_it(self, out_file, string):
        out_file.write(string + "\n")

    def create_yaml(self):
        # initialize dictionaries
        schemasdict = {}
        fdsdict = {'FeatureDatasets': {}}
        fcdict = {'FeatureClasses': {}}
        tablesdict = {'Tables': {}}

        # feature datasets
        fdslist = self.get_feature_datasets()
        if fdslist != None:
            fdslist.sort()
            for fds in fdslist:
                fdsdict['FeatureDatasets'].update({fds: [fds]})

        # featureclasses in root
        fclist = self.get_feature_classes(None)
        if fclist != None:
            fclist.sort()
        fcdict['FeatureClasses'].update({'public': fclist})

        # tables
        tableslist = self.get_tables()
        if tableslist != None:
            tableslist.sort()
        tablesdict['Tables'].update({'public': tableslist})

        # schemas
        schemasdict.update({'Schemas': fdslist})

        with open(self.yamlfile_path, 'w') as outfile:
            yaml.dump(schemasdict, outfile)

        with open(self.yamlfile_path, 'a') as outfile:
            yaml.dump(fdsdict, outfile)

        with open(self.yamlfile_path, 'a') as outfile:
            yaml.dump(fcdict, outfile)

        with open(self.yamlfile_path, 'a') as outfile:
            yaml.dump(tablesdict, outfile)

    def get_feature_datasets(self):
        fdslist = arcpy.ListDatasets()
        return fdslist

    def get_feature_classes(self, fds):
        fclist = arcpy.ListFeatureClasses("*", "", fds)
        return fclist

    def get_tables(self):
        tableslist = arcpy.ListTables("*")
        return tableslist

    def cleanup(self):
        print("Cleanup temporary lookup tables...")
        lutslist = arcpy.ListTables("*_lut")
        for lut in lutslist:
            arcpy.Delete_management(lut)
