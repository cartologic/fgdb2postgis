--
-- foreign_key_constraints_vw.sql
--
-- Create a simple view for business tables’ relationships
--

CREATE OR REPLACE VIEW foreign_key_constraints_vw AS
SELECT
     tc.table_schema,
     tc.table_name,
     kcu.column_name,
     ctu.table_schema f_table_schema,
     ctu.table_name f_table_name,
     ccu.column_name f_column_name,
     tc.constraint_name,
     tc.constraint_type
FROM
     information_schema.table_constraints tc,
     information_schema.key_column_usage kcu,
     information_schema.constraint_table_usage ctu,
     information_schema.constraint_column_usage ccu
WHERE
      tc.constraint_type = 'FOREIGN KEY'
  AND tc.constraint_name = kcu.constraint_name
  AND tc.constraint_name = ctu.constraint_name
  AND tc.constraint_name = ccu.constraint_name
ORDER BY
      tc.constraint_name;
