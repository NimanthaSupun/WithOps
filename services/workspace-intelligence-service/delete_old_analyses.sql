-- SQL Script to manually delete old analyses from the database
-- CASCADE delete is now enabled - deleting an analysis automatically deletes:
--   - All repository_findings records
--   - All maturity_scores records

-- ============================================================
-- OPTION 1: Delete a specific analysis by ID
-- ============================================================
-- Replace 'YOUR_ANALYSIS_ID_HERE' with the actual analysis ID
-- CASCADE will automatically delete related findings and maturity scores
-- DELETE FROM project_analyses WHERE id = 'YOUR_ANALYSIS_ID_HERE';

-- ============================================================
-- OPTION 2: View all analyses for an organization
-- ============================================================
-- Replace 'YOUR_ORG_NAME' with your organization name
SELECT 
    pa.id,
    pa.project_name,
    pa.organization_name,
    pa.created_at,
    pa.status,
    pa.overall_maturity_score,
    pa.total_repositories,
    (pa.critical_findings + pa.high_findings + pa.medium_findings + pa.low_findings) as total_findings,
    COUNT(DISTINCT rf.id) as findings_in_table,
    COUNT(DISTINCT ms.id) as maturity_scores_count
FROM project_analyses pa
LEFT JOIN repository_findings rf ON rf.analysis_id = pa.id
LEFT JOIN maturity_scores ms ON ms.analysis_id = pa.id
WHERE pa.organization_name = 'YOUR_ORG_NAME'
GROUP BY pa.id, pa.project_name, pa.organization_name, pa.created_at, pa.status, 
         pa.overall_maturity_score, pa.total_repositories, pa.critical_findings, 
         pa.high_findings, pa.medium_findings, pa.low_findings
ORDER BY pa.created_at DESC;

-- ============================================================
-- OPTION 3: Delete analyses older than a specific date
-- ============================================================
-- Replace the date with your cutoff date
-- CASCADE will automatically delete related findings and maturity scores
-- DELETE FROM project_analyses 
-- WHERE organization_name = 'YOUR_ORG_NAME' 
-- AND created_at < '2025-12-01 00:00:00';

-- ============================================================
-- OPTION 4: Delete all analyses except the most recent N
-- ============================================================
-- This keeps the latest 5 analyses and deletes the rest
-- CASCADE will automatically delete related findings and maturity scores
-- DELETE FROM project_analyses 
-- WHERE organization_name = 'YOUR_ORG_NAME'
-- AND id NOT IN (
--     SELECT id FROM project_analyses 
--     WHERE organization_name = 'YOUR_ORG_NAME'
--     ORDER BY created_at DESC 
--     LIMIT 5
-- );

-- ============================================================
-- OPTION 5: Count total analyses per organization
-- ============================================================
SELECT 
    pa.organization_name,
    COUNT(DISTINCT pa.id) as total_analyses,
    COUNT(DISTINCT rf.id) as total_findings,
    COUNT(DISTINCT ms.id) as total_maturity_scores,
    MIN(pa.created_at) as oldest_analysis,
    MAX(pa.created_at) as newest_analysis
FROM project_analyses pa
LEFT JOIN repository_findings rf ON rf.analysis_id = pa.id
LEFT JOIN maturity_scores ms ON ms.analysis_id = pa.id
GROUP BY pa.organization_name
ORDER BY total_analyses DESC;

-- ============================================================
-- OPTION 6: Clear all data for a specific organization
-- ============================================================
-- ⚠️ WARNING: This deletes ALL analyses for an organization!
-- CASCADE will automatically delete all related findings and maturity scores
-- Uncomment to use (replace YOUR_ORG_NAME):
-- DELETE FROM project_analyses WHERE organization_name = 'YOUR_ORG_NAME';
