##
# filegdb.py
#
# Description: Read file geodatabase, create tables for subtypes and domains
#              Prepare sql scripts for indexes and foreign key constraints
# Author: George Ioannou
# Copyright: Cartologic 2017-2020
#
##
import sys
import os
from os import path
import yaml
import arcpy
from slugify import Slugify

import ruamel.yaml
from ruamel.yaml import YAML


slugify = Slugify(translate=None)


class YAMLObject(YAML):
    def __init__(self):
        YAML.__init__(self)
        self.allow_unicode = True
        self.encoding = 'utf-8'

yaml = YAMLObject()


class FileGDB:
    def __init__(self, workspace, t_srs):
        self.workspace = workspace
        self.t_srs = t_srs
        self.workspace_path = ""
        self.sqlfolder_path = ""
        self.yamlfile_path = ""
        self.schemas = []
        self.feature_datasets = {}
        self.feature_classes = {}
        self.tables = {}
        self.indexes = []
        self.constraints = []
        self.views = []
        self.domain_tables = []  # Track created domain tables
        self.subtype_tables = []  # Track created subtype tables
        self.init_paths()
        self.setenv()
        self.parse_yaml()

    # -------------------------------------------------------------------------------
    # Initialize file geodatabase environment
    #
    def init_paths(self):
        # workspace path
        workspace_path = path.join(os.getcwd(), self.workspace)
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
        print(" Workspace: {0} ({1})".format(self.workspace_path, self.t_srs))
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
        if not path.exists(self.yamlfile_path):
            print("\nCreating default YAML file ...")
            self.create_yaml()
            print(f"Created default YAML file at {self.yamlfile_path}")

        try:
            with open(self.yamlfile_path, 'r', encoding="utf-8") as stream:
                yaml_dict = {}
                yaml_loader = YAML(typ='safe')
                data_map = yaml_loader.load(stream)
                
                for key_type, value_items in data_map.items():
                    if key_type == "Schemas":
                        self.schemas = value_items
                    elif key_type == "FeatureDatasets":
                        self.feature_datasets = value_items
                    elif key_type == "FeatureClasses":
                        self.feature_classes = value_items
                    elif key_type == "Tables":
                        self.tables = value_items

                # lookup_tables is a default schema and it will host subtypes, domains
                if 'lookup_tables' not in self.schemas:
                    self.schemas.append('lookup_tables')
                
                if 'public' not in self.schemas:
                    self.schemas.append('public')
                
        except Exception as e:
            print(f"Error parsing YAML file: {str(e)}")
            print("Using default schema settings")
            self.schemas = ['public', 'lookup_tables']
            self.feature_datasets = {}
            self.feature_classes = {'public': []}
            self.tables = {'public': []}

    # -------------------------------------------------------------------------------
    # Open sql files
    #
    def open_files(self):
        print("\nInitializing sql files ...")

        if not path.exists(self.sqlfolder_path):
            os.mkdir(self.sqlfolder_path)

        self.f_create_schemas = open(
            path.join(self.sqlfolder_path, "create_schemas.sql"), "w", encoding='utf-8')
        self.f_split_schemas = open(
            path.join(self.sqlfolder_path, "split_schemas.sql"), "w", encoding='utf-8')
        self.f_create_indexes = open(
            path.join(self.sqlfolder_path, "create_indexes.sql"), "w", encoding='utf-8')
        self.f_create_constraints = open(
            path.join(self.sqlfolder_path, "create_constraints.sql"), "w", encoding='utf-8')
        self.f_create_views = open(
            path.join(self.sqlfolder_path, "create_views.sql"), "w", encoding='utf-8')
        self.f_find_data_errors = open(
            path.join(self.sqlfolder_path, "find_data_errors.sql"), "w", encoding='utf-8')
        self.f_fix_data_errors = open(
            path.join(self.sqlfolder_path, "fix_data_errors.sql"), "w", encoding='utf-8')

    # -------------------------------------------------------------------------------
    # close sql files
    #
    def close_files(self):
        print("\nClosing sql files ...")
        self.f_create_schemas.close()
        self.f_split_schemas.close()
        self.f_create_indexes.close()
        self.f_create_constraints.close()
        self.f_create_views.close()
        self.f_find_data_errors.close()
        self.f_fix_data_errors.close()

    # -------------------------------------------------------------------------------
    # Process domains
    # Convert domains to tables
    #
    def process_domains(self):
        print("\nProcessing domains ...")

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

        if not arcpy.Exists(domain_table):
            try:
                arcpy.DomainToTable_management(
                    self.workspace, domain.name, domain_table, domain_field, domain_field_desc)
                print(f"  Created domain table: {domain_table}")
                self.domain_tables.append(domain_table)
            except Exception as e:
                print(f"  Error creating domain table {domain_table}: {str(e)}")
                return

        # create index
        self.create_index(domain_table, domain_field)
        self.split_schemas(domain_table, "lookup_tables")

    # -------------------------------------------------------------------------------
    # Create constraints referencing domains
    #
    def create_constraints_referencing_domains(self, layer):
        try:
            fields = arcpy.ListFields(layer)
            for field in fields:
                if field.domain:
                    domain_name = slugify(field.domain, separator='_', lowercase=False)
                    domain_table = "{}_lut".format(domain_name)
                    if arcpy.Exists(domain_table):
                        self.create_foreign_key_constraint(
                            layer, field.name, domain_table, "Code")
        except Exception as e:
            print(f"  Error creating constraints for {layer}: {str(e)}")

    # -------------------------------------------------------------------------------
    # Process subtypes
    # Convert subtypes to tables
    #

    def process_subtypes(self):
        print("\nProcessing subtypes ...")

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
        except Exception as e:
            print(f"{layer}: Error listing subtypes - {str(e)}")
            return

        if subtypes_dict:                
            subtype_fields = {key: value['SubtypeField']
                            for key, value in subtypes_dict.items()}
            subtype_values = {key: value['Name']
                            for key, value in subtypes_dict.items()}

            if not subtype_fields:
                return
                
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
                            
                if field_type is None:
                    print(f"  Could not determine field type for subtype field {field} in {layer}")
                    return

                subtypes_table = "{0}_{1}_sub".format(layer, field)
                subtypes_table = slugify(
                    subtypes_table, separator='_', lowercase=False)

                if not arcpy.Exists(subtypes_table):
                    try:
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
                        print(f"  Created subtype table: {subtypes_table}")
                        self.subtype_tables.append(subtypes_table)
                    except Exception as e:
                        print(f"  Error creating subtype table {subtypes_table}: {str(e)}")
                        return

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

        relClassSet = self.get_relationship_classes()

        for relClass in relClassSet:
            try:
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

                self.create_index(rel_origin_table, rel_primary_key)
                self.create_foreign_key_constraint(
                    rel_destination_table, rel_foreign_key, rel_origin_table, rel_primary_key)

                # process data errors (fk)
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
            except Exception as e:
                print(f"  Error processing relationship {relClass}: {str(e)}")

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
            try:
                for j, rel in enumerate(desc.relationshipClassNames):
                    relClasses.add(rel)
            except Exception as e:
                print(f"  Error getting relationship classes for {fc}: {str(e)}")

        return relClasses

    # -------------------------------------------------------------------------------
    # Process Schemas
    # Prepare sql to split Tables and Feature Classes in Schemas
    #
    def process_schemas(self):
        print("\nProcessing schemas ...")

        # create schemas
        self.write_it(self.f_create_schemas, "-- Create schemas\n")
        for schema in self.schemas:
            if schema == 'public':
                continue
            str_schema = 'CREATE SCHEMA IF NOT EXISTS "{0}";\n'.format(schema)
            self.write_it(self.f_create_schemas, str_schema)

        # split feature datasets to schemas
        self.write_it(self.f_split_schemas, "-- Split feature datasets to schemas\n")
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
        self.write_it(self.f_split_schemas, "\n-- Split standalone feature classes to schemas\n")
        print(" FeatureClasses")
        for schema, fcs in self.feature_classes.items():
            if schema == 'public':
                continue

            for fc in fcs:
                if arcpy.Exists(fc):
                    self.split_schemas(fc, schema)

        # split tables to schemas
        self.write_it(self.f_split_schemas, "\n-- Split tables to schemas\n")
        print(" Tables")
        for schema, tables in self.tables.items():
            if schema == 'public':
                continue

            for table in tables:
                if arcpy.Exists(table):
                    self.split_schemas(table, schema)
                    
        # Move lookup tables to lookup_tables schema
        self.write_it(self.f_split_schemas, "\n-- Move lookup tables to lookup_tables schema\n")
        str_lookup_tables = """
DO $$
DECLARE
    t_name text;
BEGIN
    FOR t_name IN 
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_type = 'BASE TABLE'
        AND (table_name LIKE '%\_lut%' OR table_name LIKE '%\_sub%')
    LOOP
        EXECUTE format('ALTER TABLE IF EXISTS public."%s" SET SCHEMA "lookup_tables";', t_name);
    END LOOP;
END $$;
"""
        self.write_it(self.f_split_schemas, str_lookup_tables)

    # -------------------------------------------------------------------------------
    # Create YAML file with schema mappings
    #
    def create_yaml(self):
        """Create YAML file with schema mappings"""
        print("\nCreating default YAML file ...")
        
        # Initialize data structure
        data_map = {}
        data_map["Schemas"] = []
        data_map["FeatureDatasets"] = {}
        data_map["FeatureClasses"] = {}
        data_map["Tables"] = {}
        
        # Add lookup_tables schema for domains and subtypes
        data_map["Schemas"].append("lookup_tables")
        
        # Process feature datasets
        fds_list = arcpy.ListDatasets("*", "Feature")
        fds_list.sort()
        
        for fds in fds_list:
            # Add feature dataset as schema
            schema_name = slugify(fds, separator='_', lowercase=False)
            if schema_name not in data_map["Schemas"]:
                data_map["Schemas"].append(schema_name)
            
            # Add feature dataset to FeatureDatasets
            data_map["FeatureDatasets"][schema_name] = [fds]
            
            # Add feature classes in this dataset to FeatureClasses
            fc_list = arcpy.ListFeatureClasses("*", "", fds)
            fc_list.sort()
            
            if schema_name not in data_map["FeatureClasses"]:
                data_map["FeatureClasses"][schema_name] = []
                
            for fc in fc_list:
                data_map["FeatureClasses"][schema_name].append(fc)
        
        # Process standalone feature classes
        fc_list = arcpy.ListFeatureClasses("*", "")
        fc_list.sort()
        
        if "public" not in data_map["Schemas"]:
            data_map["Schemas"].append("public")
            
        if "public" not in data_map["FeatureClasses"]:
            data_map["FeatureClasses"]["public"] = []
            
        for fc in fc_list:
            data_map["FeatureClasses"]["public"].append(fc)
        
        # Process tables
        tables_list = arcpy.ListTables()
        tables_list.sort()
        
        if "public" not in data_map["Tables"]:
            data_map["Tables"]["public"] = []
            
        # Check for lookup tables and add them to lookup_tables schema
        if "lookup_tables" not in data_map["Tables"]:
            data_map["Tables"]["lookup_tables"] = []
            
        for table in tables_list:
            if "_lut" in table.lower() or "_sub" in table.lower():
                # This is a lookup table, add to lookup_tables schema
                data_map["Tables"]["lookup_tables"].append(table)
            else:
                # Regular table, add to public schema
                data_map["Tables"]["public"].append(table)
        
        # Write to YAML file
        try:
            with open(self.yamlfile_path, 'w', encoding="utf-8") as stream:
                yaml.dump(data_map, stream)
                print(f"Created default YAML file at {self.yamlfile_path}")
        except Exception as e:
            print(f"Error creating YAML file: {str(e)}")

    # -------------------------------------------------------------------------------
    # Get feature datasets
    #
    def get_feature_datasets(self):
        fdslist = arcpy.ListDatasets()
        return fdslist

    # -------------------------------------------------------------------------------
    # Get feature classes
    #
    def get_feature_classes(self, fds):
        fclist = arcpy.ListFeatureClasses("*", "", fds)
        return fclist

    # -------------------------------------------------------------------------------
    # Get tables
    #
    def get_tables(self):
        tableslist = arcpy.ListTables("*")
        return tableslist

    # -------------------------------------------------------------------------------
    # Execute SQL file directly
    #
    def execute_sql_file(self, sql_file):
        print(f"  Executing SQL file: {sql_file}")
        with open(sql_file, 'r', encoding="utf-8") as f:
            sql_content = f.read()
            print(f"  SQL file content length: {len(sql_content)} characters")

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
        fkey_name = "{0}_{1}".format(table_details[0:30], table_master[0:30])

        if fkey_name not in self.constraints:
            self.constraints.append(fkey_name)
            str_constraint = 'ALTER TABLE "{0}" ADD CONSTRAINT "{1}" FOREIGN KEY ("{2}") REFERENCES "{3}" ("{4}") NOT VALID; \n'
            str_constraint = str_constraint.format(table_details, fkey_name, fkey, table_master, pkey)
            self.write_it(self.f_create_constraints, str_constraint)

    # -------------------------------------------------------------------------------
    # Split schemas
    #
    def split_schemas(self, table, schema):
        str_split_schemas = "ALTER TABLE \"{0}\" SET SCHEMA \"{1}\";\n".format(
            table, schema)
        self.write_it(self.f_split_schemas, str_split_schemas)

    # -------------------------------------------------------------------------------
    # Write string to given open file
    #
    def write_it(self, out_file, string):
        out_file.write(string)

    # -------------------------------------------------------------------------------
    # Cleanup temporary files and tables
    #
    def cleanup(self):
        print("\nCleanup temporary lookup tables...")
        try:
            lutslist = arcpy.ListTables("*_lut")
            for lut in lutslist:
                if lut in self.domain_tables or lut in self.subtype_tables:
                    print(f"  Keeping lookup table: {lut}")
                    continue
                print(f"  Deleting temporary table: {lut}")
                arcpy.Delete_management(lut)
        except Exception as e:
            print(f"  Error during cleanup: {str(e)}")
