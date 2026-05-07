import asyncio
from database.config import DatabaseManager
from database.models import ProjectAnalysis
from sqlalchemy import select

async def check():
    db = DatabaseManager()
    async with db.get_session() as s:
        stmt = select(ProjectAnalysis).where(
            ProjectAnalysis.analysis_scope == 'unified'
        ).order_by(ProjectAnalysis.created_at.desc()).limit(1)
        r = await s.execute(stmt)
        a = r.scalar_one_or_none()
        
        if not a:
            print('No unified analysis found')
            return
            
        print('=== UNIFIED ANALYSIS ===')
        print(f'Overall Maturity: {a.overall_maturity_score}')
        print(f'Analysis ID: {a.id}')
        print('\n=== PROJECT_ANALYSES STRUCTURE ===')
        
        pa = a.analysis_data.get('project_analyses', []) if a.analysis_data else []
        print(f'Number of projects: {len(pa)}')
        
        for idx, project in enumerate(pa):
            print(f'\n--- Project {idx + 1}: {project.get("project_name", "Unknown")} ---')
            print(f'Maturity Score: {project.get("maturity", "N/A")}')
            print(f'Repositories: {len(project.get("repositories", []))}')
            print(f'Findings Count: {project.get("findings_count", 0)}')
            
            # Show maturity structure
            maturity = project.get('maturity', {})
            if isinstance(maturity, dict):
                print('Maturity keys:', list(maturity.keys()))
                print('Maturity values:', {k: v for k, v in maturity.items() if 'score' in str(k).lower() or 'level' in str(k).lower()})

asyncio.run(check())
