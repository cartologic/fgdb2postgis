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
			--config OGR_TRUNCATE YES \
			--config PG_USE_COPY YES \
			{3}'.format(self.conn_string, filegdb.a_srs, self.t_srs, filegdb.workspace)

        system(cmd)

    def update_views(self):
        print("\nUpdating database views ...")
        sql_files = [
            'information_schema_views.sql',
            'foreign_key_constraints_vw.sql'
        ]

        for sql_file in sql_files:
            sql_file = path.join(path.abspath(
                path.dirname(__file__)), 'sql_files/{}'.format(sql_file))
            self.execute_sql(sql_file)

    def create_schemas(self, filegdb):
        print("\nCreating schemas ...")

        sql_files = ['create_schemas.sql']
        for sql_file in sql_files:
            sql_file = path.join(filegdb.sqlfolder_path, sql_file)
            self.execute_sql(sql_file)

    def apply_sql(self, filegdb):
        print("\nApplying sql scripts ...")
        sql_files = [
            'fix_data_errors.sql',
            'create_indexes.sql',
            'create_constraints.sql',
            'split_schemas.sql'
        ]

        for sql_file in sql_files:
            sql_file = path.join(filegdb.sqlfolder_path, sql_file)
            self.execute_sql(sql_file)

    def execute_sql(self, sql_file):
        cursor = self.conn.cursor()

        if path.exists(sql_file):
            # print(" {}".format(sql_file))
            with open(sql_file, "r") as sql:
                code = sql.read()
                cursor.execute(code)
        else:
            print(" Unable to locate sql file:")
            print(sql_file)

        cursor.close()
        self.conn.commit()
