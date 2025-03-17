##
# postgis.py
#
# Description: Use ogr2ogr to convert file geodatabase to postgis
#              Apply number of sql scripts to create indexes and foreign key constraints
# Author: George Ioannou
# Copyright: Cartologic 2017-2020
#
##
import sys
from os import path, system
import os
import psycopg2
from psycopg2 import sql

class PostGIS:
    def __init__(self, database, host='localhost', port='5432', user='postgres', password='postgres'):
        self.database = database
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.conn = None
        self.cursor = None

    def info(self):
        print("\nPostGIS Info:")
        print(" Database: {0}".format(self.database))
        print(" Host: {0}".format(self.host))
        print(" Port: {0}".format(self.port))
        print(" User: {0}".format(self.user))

    def connect(self):
        try:
            self.conn = psycopg2.connect(
                database=self.database,
                user=self.user,
                password=self.password,
                host=self.host,
                port=self.port
            )
            self.cursor = self.conn.cursor()
            print("Connected to PostgreSQL database!")
            return True
        except Exception as e:
            print(f"Error connecting to PostgreSQL database: {str(e)}")
            return False

    def disconnect(self):
        if self.conn:
            if self.cursor:
                self.cursor.close()
            self.conn.close()
            print("Disconnected from PostgreSQL database")

    def execute_sql(self, sql):
        try:
            self.cursor.execute(sql)
            self.conn.commit()
            return True
        except Exception as e:
            self.conn.rollback()
            print(f"Error executing SQL: {str(e)}")
            return False

    def load_database(self, filegdb):
        print("\nLoading database ...")

        # Create the database if it doesn't exist
        self.create_database()

        # First, create all the schemas
        self.create_schemas_in_db(filegdb)

        # Use ogr2ogr to load the data
        ogr_cmd = 'ogr2ogr -f "PostgreSQL" ' + \
                  'PG:"host={0} port={1} user={2} password={3} dbname={4}" '.format(
                      self.host, self.port, self.user, self.password, self.database) + \
                  '{0} '.format(filegdb.workspace_path) + \
                  '-overwrite ' + \
                  '-t_srs {0} '.format(filegdb.t_srs) + \
                  '-lco GEOMETRY_NAME=geom ' + \
                  '-lco FID=id ' + \
                  '-lco PRECISION=NO ' + \
                  '-skipfailures ' + \
                  '--config PG_USE_COPY YES ' + \
                  '--config OGR_TRUNCATE YES ' + \
                  '--config PGCLIENTENCODING UTF8 ' + \
                  '--config PG_CLIENT_ENCODING UTF8 ' + \
                  '--config CPL_MAX_ERROR_REPORTS 5 ' + \
                  '--config OGR_ENABLE_PARTIAL_REPROJECTION YES'

        print(f"Running ogr2ogr command: {ogr_cmd}")
        os.system(ogr_cmd)
        
        # After loading, move tables to their respective schemas
        self.move_tables_to_schemas(filegdb)

    def create_schemas_in_db(self, filegdb):
        """Create all schemas defined in the YAML file directly in the database"""
        print("\nCreating schemas in database...")
        
        # Connect to the database
        if not self.connect():
            return
            
        try:
            # Create each schema
            for schema in filegdb.schemas:
                if schema == 'public':
                    continue  # public schema already exists
                    
                try:
                    sql = f'CREATE SCHEMA IF NOT EXISTS "{schema}";'
                    self.execute_sql(sql)
                    print(f"  Created schema: {schema}")
                except Exception as e:
                    print(f"  Error creating schema {schema}: {str(e)}")
        finally:
            self.disconnect()

    def move_tables_to_schemas(self, filegdb):
        """Move tables from public schema to their respective schemas"""
        print("\nMoving tables to their respective schemas...")
        
        # Connect to the database
        if not self.connect():
            return
            
        try:
            # Get list of all tables in the public schema
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_type = 'BASE TABLE'
            """)
            public_tables = [row[0] for row in cursor.fetchall()]
            
            # Get list of all tables with geometry columns (feature classes)
            try:
                cursor.execute("""
                    SELECT f_table_name 
                    FROM public.geometry_columns 
                    WHERE f_table_schema = 'public'
                """)
                geometry_tables = [row[0] for row in cursor.fetchall()]
            except Exception as e:
                print(f"Warning: Could not get geometry tables: {str(e)}")
                geometry_tables = []
            
            # First, move all lookup tables to the lookup_tables schema
            print("  Moving lookup tables to lookup_tables schema...")
            for table in list(public_tables):  # Create a copy of the list to avoid modification during iteration
                if "_lut" in table.lower():
                    try:
                        sql = f'ALTER TABLE IF EXISTS public."{table}" SET SCHEMA "lookup_tables";'
                        self.execute_sql(sql)
                        print(f"  Moved lookup table {table} to schema lookup_tables")
                        if table in public_tables:
                            public_tables.remove(table)  # Remove from the list since it's been moved
                    except Exception as e:
                        print(f"  Error moving lookup table {table} to schema lookup_tables: {str(e)}")
            
            # Process feature datasets
            print("  Moving tables based on feature datasets...")
            for schema, datasets in filegdb.feature_datasets.items():
                if schema == 'public':
                    continue
                
                # For each dataset, try to match tables by name
                for dataset in datasets:
                    dataset_name = dataset.lower()
                    for table in list(public_tables):  # Create a copy to avoid modification during iteration
                        table_lower = table.lower()
                        # If table name contains dataset name or dataset name contains table name, move it to the schema
                        if dataset_name in table_lower or table_lower in dataset_name:
                            try:
                                sql = f'ALTER TABLE IF EXISTS public."{table}" SET SCHEMA "{schema}";'
                                self.execute_sql(sql)
                                print(f"  Moved table {table} to schema {schema} (dataset match)")
                                if table in public_tables:
                                    public_tables.remove(table)  # Remove from the list since it's been moved
                            except Exception as e:
                                print(f"  Error moving table {table} to schema {schema}: {str(e)}")
            
            # Process feature classes defined in the YAML
            print("  Moving tables based on feature classes in YAML...")
            for schema, feature_classes in filegdb.feature_classes.items():
                if schema == 'public':
                    continue
                
                for fc in feature_classes:
                    fc_name = fc.lower()
                    for table in list(public_tables):
                        table_lower = table.lower()
                        if fc_name == table_lower or fc_name in table_lower or table_lower in fc_name:
                            try:
                                sql = f'ALTER TABLE IF EXISTS public."{table}" SET SCHEMA "{schema}";'
                                self.execute_sql(sql)
                                print(f"  Moved table {table} to schema {schema} (feature class match)")
                                if table in public_tables:
                                    public_tables.remove(table)
                            except Exception as e:
                                print(f"  Error moving table {table} to schema {schema}: {str(e)}")
            
            # Process tables defined in the YAML
            print("  Moving tables based on tables in YAML...")
            for schema, tables in filegdb.tables.items():
                if schema == 'public':
                    continue
                
                for yaml_table in tables:
                    yaml_table_name = yaml_table.lower()
                    for table in list(public_tables):
                        table_lower = table.lower()
                        if yaml_table_name == table_lower or yaml_table_name in table_lower or table_lower in yaml_table_name:
                            try:
                                sql = f'ALTER TABLE IF EXISTS public."{table}" SET SCHEMA "{schema}";'
                                self.execute_sql(sql)
                                print(f"  Moved table {table} to schema {schema} (table match)")
                                if table in public_tables:
                                    public_tables.remove(table)
                            except Exception as e:
                                print(f"  Error moving table {table} to schema {schema}: {str(e)}")
            
            # For tables that weren't moved and have geometry columns, try to find a matching schema
            print("  Finding best schema matches for remaining geometry tables...")
            for table in geometry_tables:
                if table in public_tables:  # Table is still in public schema
                    # Try to match with a schema
                    best_match = None
                    best_match_score = 0
                    
                    for schema in filegdb.schemas:
                        if schema == 'public' or schema == 'lookup_tables':
                            continue
                            
                        # Calculate a simple matching score
                        schema_lower = schema.lower()
                        table_lower = table.lower()
                        
                        # Check if schema name is part of table name or vice versa
                        if schema_lower in table_lower:
                            score = len(schema_lower)
                            if score > best_match_score:
                                best_match_score = score
                                best_match = schema
                        elif table_lower in schema_lower:
                            score = len(table_lower)
                            if score > best_match_score:
                                best_match_score = score
                                best_match = schema
                    
                    if best_match:
                        try:
                            sql = f'ALTER TABLE IF EXISTS public."{table}" SET SCHEMA "{best_match}";'
                            self.execute_sql(sql)
                            print(f"  Moved table {table} to schema {best_match} (best match)")
                            if table in public_tables:
                                public_tables.remove(table)  # Remove from the list since it's been moved
                        except Exception as e:
                            print(f"  Error moving table {table} to schema {best_match}: {str(e)}")
            
            # Move subtype tables to lookup_tables schema
            print("  Moving subtype tables to lookup_tables schema...")
            for table in list(public_tables):  # Create a copy to avoid modification during iteration
                if "_sub" in table.lower():
                    try:
                        sql = f'ALTER TABLE IF EXISTS public."{table}" SET SCHEMA "lookup_tables";'
                        self.execute_sql(sql)
                        print(f"  Moved subtype table {table} to schema lookup_tables")
                        if table in public_tables:
                            public_tables.remove(table)  # Remove from the list since it's been moved
                    except Exception as e:
                        print(f"  Error moving subtype table {table} to schema lookup_tables: {str(e)}")
                    
            # Report on tables that couldn't be moved
            if public_tables:
                print("\n  The following tables remain in the public schema:")
                for table in public_tables:
                    print(f"    - {table}")
                    
        except Exception as e:
            print(f"Error in move_tables_to_schemas: {str(e)}")
        finally:
            self.disconnect()

    def process_database(self, filegdb):
        print("\nProcessing database ...")
        
        # Create the database if it doesn't exist
        self.create_database()
        
        # First, create all the schemas
        self.create_schemas_in_db(filegdb)
        
        # Connect to the database
        if not self.connect():
            return
            
        try:
            # Apply SQL scripts in the correct order
            print("\nApplying SQL scripts ...")
            
            # First, execute split_schemas.sql to move tables to their respective schemas
            split_schemas_file = path.join(filegdb.sqlfolder_path, "split_schemas.sql")
            if os.path.exists(split_schemas_file):
                print(f"  Executing split_schemas.sql: {split_schemas_file}")
                with open(split_schemas_file, 'r', encoding="utf-8") as f:
                    sql = f.read()
                    if sql.strip():
                        # Execute each statement separately
                        statements = sql.split(';')
                        for statement in statements:
                            if statement.strip():
                                try:
                                    self.execute_sql(statement + ';')
                                except Exception as e:
                                    print(f"  Error executing statement: {str(e)}")
                        print("  Successfully executed split_schemas.sql")
                    else:
                        print("  SQL file is empty: " + split_schemas_file)
            else:
                print("  SQL file not found: " + split_schemas_file)
            
            # Then execute the other SQL files
            create_indexes_file = path.join(filegdb.sqlfolder_path, "create_indexes.sql")
            if os.path.exists(create_indexes_file):
                self.execute_sql_file(create_indexes_file)
            
            create_constraints_file = path.join(filegdb.sqlfolder_path, "create_constraints.sql")
            if os.path.exists(create_constraints_file):
                self.execute_sql_file(create_constraints_file)
            
            # Update views
            print("\nUpdating views ...")
            create_views_file = path.join(filegdb.sqlfolder_path, "create_views.sql")
            if os.path.exists(create_views_file):
                self.execute_sql_file(create_views_file)
            
        finally:
            self.disconnect()

    def create_database(self):
        # Connect to postgres database to create the target database if it doesn't exist
        conn = None
        try:
            conn = psycopg2.connect(
                database="postgres",
                user=self.user,
                password=self.password,
                host=self.host,
                port=self.port
            )
            conn.autocommit = True
            cursor = conn.cursor()
            
            # Check if database exists
            cursor.execute(f"SELECT 1 FROM pg_database WHERE datname = '{self.database}'")
            exists = cursor.fetchone()
            
            if not exists:
                print(f"Creating database {self.database}...")
                cursor.execute(f"CREATE DATABASE {self.database}")
                print(f"Database {self.database} created successfully")
                
                # Connect to the new database to create the PostGIS extension
                conn.close()
                conn = psycopg2.connect(
                    database=self.database,
                    user=self.user,
                    password=self.password,
                    host=self.host,
                    port=self.port
                )
                conn.autocommit = True
                cursor = conn.cursor()
                
                try:
                    cursor.execute("CREATE EXTENSION IF NOT EXISTS postgis")
                    print("PostGIS extension created successfully")
                except Exception as e:
                    print(f"Error creating PostGIS extension: {str(e)}")
                    print("You may need to install PostGIS in your database manually")
            else:
                print(f"Database {self.database} already exists")
                
                # Check if PostGIS extension exists
                try:
                    conn.close()
                    conn = psycopg2.connect(
                        database=self.database,
                        user=self.user,
                        password=self.password,
                        host=self.host,
                        port=self.port
                    )
                    conn.autocommit = True
                    cursor = conn.cursor()
                    
                    cursor.execute("SELECT 1 FROM pg_extension WHERE extname = 'postgis'")
                    postgis_exists = cursor.fetchone()
                    
                    if not postgis_exists:
                        cursor.execute("CREATE EXTENSION IF NOT EXISTS postgis")
                        print("PostGIS extension created successfully")
                except Exception as e:
                    print(f"Error checking/creating PostGIS extension: {str(e)}")
                
        except Exception as e:
            print(f"Error creating database: {str(e)}")
            print("Make sure the PostgreSQL server is running and accessible")
            print("You may need to create the database manually")
        finally:
            if conn:
                conn.close()

    def create_schemas(self, filegdb):
        print("\nCreating schemas ...")
        
        # Execute the create_schemas.sql file
        self.execute_sql_file(os.path.join(filegdb.sqlfolder_path, "create_schemas.sql"))

    def apply_sql(self, filegdb):
        print("\nApplying SQL scripts ...")
        
        # Execute the split_schemas.sql file
        self.execute_sql_file(os.path.join(filegdb.sqlfolder_path, "split_schemas.sql"))
        
        # Execute the create_indexes.sql file
        self.execute_sql_file(os.path.join(filegdb.sqlfolder_path, "create_indexes.sql"))
        
        # Execute the create_constraints.sql file
        self.execute_sql_file(os.path.join(filegdb.sqlfolder_path, "create_constraints.sql"))

    def update_views(self, filegdb=None):
        print("\nUpdating views ...")
        
        if filegdb and os.path.exists(os.path.join(filegdb.sqlfolder_path, "create_views.sql")):
            # Execute the create_views.sql file
            self.execute_sql_file(os.path.join(filegdb.sqlfolder_path, "create_views.sql"))

    def execute_sql_file(self, sql_file):
        if not os.path.exists(sql_file):
            print(f"SQL file not found: {sql_file}")
            return False
            
        try:
            print(f"  Executing SQL file: {sql_file}")
            with open(sql_file, 'r', encoding="utf-8") as f:
                sql = f.read()
                if not sql.strip():
                    print(f"  SQL file is empty: {sql_file}")
                    return True  # Return success for empty files
                
                # Execute each statement separately
                statements = sql.split(';')
                success = True
                for statement in statements:
                    if statement.strip():
                        try:
                            result = self.execute_sql(statement + ';')
                            if not result:
                                success = False
                        except Exception as e:
                            print(f"  Error executing statement: {str(e)}")
                            success = False
                
                return success
        except Exception as e:
            print(f"Error executing SQL file {sql_file}: {str(e)}")
            return False