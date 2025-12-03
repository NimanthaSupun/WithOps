-- Migration: Add analysis_data column to project_analyses table
-- This column will store the complete project analysis including repositories and findings

-- Add the analysis_data column if it doesn't exist
ALTER TABLE project_analyses 
ADD COLUMN IF NOT EXISTS analysis_data JSONB;

-- Add a comment to document the column
COMMENT ON COLUMN project_analyses.analysis_data IS 'Complete project analysis data including repositories, findings, and all metrics';
