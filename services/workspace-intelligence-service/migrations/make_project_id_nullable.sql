-- Migration: Make project_id nullable for unified analyses
-- This allows ProjectAnalysis records to be created without a project_id
-- for organization-wide unified workspace analyses

ALTER TABLE project_analyses 
ALTER COLUMN project_id DROP NOT NULL;
