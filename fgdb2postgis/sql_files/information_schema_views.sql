-- Update information_schema views to enable non admin users to view foreign key constraints
--
--  information_schema.constraint_table_usage
--  information_schema.constraint_column_usage
--
-- Give the following commands on psql prompt, copy and remove the last past of the where clause
-- and replace the original view
--
-- # \d+ information_schema.constraint_table_usage
--        ... AND pg_has_role(r.relowner, 'USAGE'::text)
-- # \d+ information_schema.constraint_column_usage
--        ... WHERE pg_has_role(x.tblowner, 'USAGE'::text)


--
-- information_schema.constraint_table_usage
--

CREATE OR REPLACE VIEW information_schema.constraint_table_usage AS
SELECT current_database()::information_schema.sql_identifier AS table_catalog,
   nr.nspname::information_schema.sql_identifier AS table_schema,
   r.relname::information_schema.sql_identifier AS table_name,
   current_database()::information_schema.sql_identifier AS constraint_catalog,
   nc.nspname::information_schema.sql_identifier AS constraint_schema,
   c.conname::information_schema.sql_identifier AS constraint_name
  FROM pg_constraint c,
   pg_namespace nc,
   pg_class r,
   pg_namespace nr
 WHERE c.connamespace = nc.oid AND r.relnamespace = nr.oid AND (c.contype = 'f'::"char" AND c.confrelid = r.oid OR (c.contype = ANY (ARRAY['p'::"char", 'u'::"char"])) AND c.conrelid = r.oid) AND r.relkind = 'r'::"char";

--
-- information_schema.constraint_column_usage
--

CREATE OR REPLACE VIEW information_schema.constraint_column_usage AS
SELECT current_database()::information_schema.sql_identifier AS table_catalog,
   x.tblschema::information_schema.sql_identifier AS table_schema,
   x.tblname::information_schema.sql_identifier AS table_name,
   x.colname::information_schema.sql_identifier AS column_name,
   current_database()::information_schema.sql_identifier AS constraint_catalog,
   x.cstrschema::information_schema.sql_identifier AS constraint_schema,
   x.cstrname::information_schema.sql_identifier AS constraint_name
  FROM ( SELECT DISTINCT nr.nspname,
           r.relname,
           r.relowner,
           a.attname,
           nc.nspname,
           c.conname
          FROM pg_namespace nr,
           pg_class r,
           pg_attribute a,
           pg_depend d,
           pg_namespace nc,
           pg_constraint c
         WHERE nr.oid = r.relnamespace AND r.oid = a.attrelid AND d.refclassid = 'pg_class'::regclass::oid AND d.refobjid = r.oid AND d.refobjsubid = a.attnum AND d.classid = 'pg_constraint'::regclass::oid AND d.objid = c.oid AND c.connamespace = nc.oid AND c.contype = 'c'::"char" AND r.relkind = 'r'::"char" AND NOT a.attisdropped
       UNION ALL
        SELECT nr.nspname,
           r.relname,
           r.relowner,
           a.attname,
           nc.nspname,
           c.conname
          FROM pg_namespace nr,
           pg_class r,
           pg_attribute a,
           pg_namespace nc,
           pg_constraint c
         WHERE nr.oid = r.relnamespace AND r.oid = a.attrelid AND nc.oid = c.connamespace AND
               CASE
                   WHEN c.contype = 'f'::"char" THEN r.oid = c.confrelid AND (a.attnum = ANY (c.confkey))
                   ELSE r.oid = c.conrelid AND (a.attnum = ANY (c.conkey))
               END AND NOT a.attisdropped AND (c.contype = ANY (ARRAY['p'::"char", 'u'::"char", 'f'::"char"])) AND r.relkind = 'r'::"char") x(tblschema, tblname, tblowner, colname, cstrschema, cstrname);
