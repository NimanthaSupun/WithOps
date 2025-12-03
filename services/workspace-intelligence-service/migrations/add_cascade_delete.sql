-- Add CASCADE delete to repository_findings foreign key constraint
-- This will automatically delete related findings when an analysis is deleted

-- First, drop the existing foreign key constraint
ALTER TABLE repository_findings 
DROP CONSTRAINT IF EXISTS repository_findings_analysis_id_fkey;

-- Recreate the foreign key constraint with CASCADE delete
ALTER TABLE repository_findings 
ADD CONSTRAINT repository_findings_analysis_id_fkey 
FOREIGN KEY (analysis_id) 
REFERENCES project_analyses(id) 
ON DELETE CASCADE;

-- Verify the constraint was created
SELECT 
    tc.constraint_name, 
    tc.table_name, 
    kcu.column_name,
    rc.delete_rule
FROM information_schema.table_constraints AS tc 
JOIN information_schema.key_column_usage AS kcu
    ON tc.constraint_name = kcu.constraint_name
    AND tc.table_schema = kcu.table_schema
JOIN information_schema.referential_constraints AS rc
    ON tc.constraint_name = rc.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY' 
    AND tc.table_name = 'repository_findings'
    AND kcu.column_name = 'analysis_id';
