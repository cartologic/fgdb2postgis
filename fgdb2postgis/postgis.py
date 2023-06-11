##
# postgis.py
#
# Description: Use ogr2ogr to conevert file geodatabase to postgis
#              Apply number of sql scripts to create indexes and foreign key constraints
# Author: George Ioannou
# Copyright: Cartologic 2017-2020
#
##
import sys
from os import path, system

import psycopg2
from psycopg2 import sql

class PostGIS:
    def __init__(self, host, port, user, password, dbname, t_srs):
        self.dbname = dbname
        self.t_srs = t_srs
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.conn = None
        self.conn_string = (
            "dbname={0} host={1} port={2} user={3} password={4}".format(
                self.dbname, self.host, self.port, self.user, self.password)
        )

    def info(self):
        print('\nPostGIS Info:')
        print(' Database: {0} ({1})'.format(self.dbname, self.t_srs))
        print(' Host: {}'.format(self.host))
        print(' Port: {}'.format(self.port))
        print(' User: {}'.format(self.user))
        print(' Password: {}'.format(self.password))

    def connect(self):
        try:
            self.conn = psycopg2.connect(self.conn_string)
            print('\nConnect to database ...')
        except psycopg2.Error as err:
            print(str(err))
            print('\nUnable to connect to database {} ...'.format(self.dbname))
            sys.exit(1)

    def disconnect(self):
        if self.conn:
            self.conn.commit()
            self.conn.close()

        print("\nDisconnect from database ...")

    def load_database(self, filegdb):

        print("\nLoading database tables ...")

        cmd = 'ogr2ogr -f "PostgreSQL" "PG:{0}" \
			-progress \
			-append \
			-a_srs {1} \
			-t_srs {2} \
			-lco fid=id \
			-lco launder=no \
			-lco geometry_name=geom \
                        -overwrite \
                        -nlt PROMOTE_TO_MULTI \
                        -nlt CONVERT_TO_LINEAR  \
			--config OGR_TRUNCATE YES \
			--config PG_USE_COPY YES \
			{3}'.format(self.conn_string, filegdb.a_srs, self.t_srs, filegdb.workspace)
        
        try:
            system(cmd)
        except Exception as error:
            print("An error occurred:", type(error).__name__, "–", error)

    def update_views(self):
        print("\nUpdating database views ...")
        sql_files = [
            'information_schema_views.sql',
            'foreign_key_constraints_vw.sql'
        ]

        for sql_file in sql_files:
            sql_file = path.join(path.abspath(
                path.dirname(__file__)), 'sql_files/{}'.format(sql_file))
            self.execute_sql_file(sql_file)

    def create_schemas(self, filegdb):
        print("\nCreating schemas ...")

        sql_files = ['create_schemas.sql']
        for sql_file in sql_files:
            sql_file = path.join(filegdb.sqlfolder_path, sql_file)
            self.execute_sql_file(sql_file)

    def apply_sql(self, filegdb):
        print("\nApplying sql scripts ...")
        sql_files = [
            'fix_data_errors.sql',
            'create_indexes.sql',
            'create_constraints.sql',
            'split_schemas.sql',
            'create_views.sql'
        ]

        for sql_file in sql_files:
            sql_file = path.join(filegdb.sqlfolder_path, sql_file)
            print(" {}".format(sql_file))
            self.execute_sql_file(sql_file)

    def execute_sql_file(self, sql_file):
        with open(sql_file, 'r', encoding="utf-8") as f:
            sql_statements = f.read()

        cursor = self.conn.cursor()
        statements = sql_statements.split(';')

        # Remove any empty statements
        statements = [stmt.strip() for stmt in statements if stmt.strip()]

        # Execute each SQL statement
        for statement in statements:
            sql_line = sql.SQL(statement)
            try:
                cursor.execute(sql_line)
            except psycopg2.Error as e:
                print("Exception:", str(e))
                self.conn.rollback()  # Rollback the transaction

        cursor.close()
        self.conn.commit()