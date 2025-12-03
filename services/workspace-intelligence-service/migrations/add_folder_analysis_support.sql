-- Migration: Add folder-level analysis support to project_analyses table
-- Date: 2025-12-03
-- Description: Adds columns to track analysis scope (organization/folder/repository)

-- Add analysis_scope column (defaults to 'organization' for backward compatibility)
ALTER TABLE project_analyses 
ADD COLUMN IF NOT EXISTS analysis_scope VARCHAR(50) DEFAULT 'organization';

-- Add folder_id column (nullable, indexed for fast folder queries)
ALTER TABLE project_analyses 
ADD COLUMN IF NOT EXISTS folder_id VARCHAR(255);

CREATE INDEX IF NOT EXISTS idx_project_analyses_folder_id 
ON project_analyses(folder_id);

-- Add folder_path column (human-readable folder hierarchy)
ALTER TABLE project_analyses 
ADD COLUMN IF NOT EXISTS folder_path VARCHAR(500);

-- Add repositories_in_scope column (JSON array of repo names in this analysis)
ALTER TABLE project_analyses 
ADD COLUMN IF NOT EXISTS repositories_in_scope JSONB;

-- Update existing records to have 'organization' scope
UPDATE project_analyses 
SET analysis_scope = 'organization' 
WHERE analysis_scope IS NULL;

-- Add comments for documentation
COMMENT ON COLUMN project_analyses.analysis_scope IS 
'Scope of analysis: organization (all repos), folder (subset), or repository (single repo)';

COMMENT ON COLUMN project_analyses.folder_id IS 
'Stable ID of the folder being analyzed (from tree structure)';

COMMENT ON COLUMN project_analyses.folder_path IS 
'Human-readable folder path like team-a/backend or infrastructure/terraform';

COMMENT ON COLUMN project_analyses.repositories_in_scope IS 
'JSON array of repository names included in this analysis scope';

-- Verify the migration
SELECT 
    column_name, 
    data_type, 
    is_nullable,
    column_default
FROM information_schema.columns 
WHERE table_name = 'project_analyses' 
    AND column_name IN ('analysis_scope', 'folder_id', 'folder_path', 'repositories_in_scope')
ORDER BY ordinal_position;
