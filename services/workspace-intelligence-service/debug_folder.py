import asyncio
from database.config import DatabaseManager
from database.models import ProjectAnalysis
from sqlalchemy import select

async def check():
    db = DatabaseManager()
    async with db.get_session() as s:
        stmt = select(ProjectAnalysis).where(
            ProjectAnalysis.analysis_scope == 'folder'
        ).order_by(ProjectAnalysis.created_at.desc()).limit(1)
        r = await s.execute(stmt)
        a = r.scalar_one_or_none()
        
        if not a:
            print('No folder analysis found')
            return
            
        print('=== FOLDER ANALYSIS ===')
        print(f'Overall Maturity: {a.overall_maturity_score}')
        print(f'Analysis ID: {a.id}')
        print(f'Project: {a.project_name}')
        
        # Show analysis_data structure
        print('\n=== ANALYSIS_DATA KEYS ===')
        if a.analysis_data:
            print('Keys:', list(a.analysis_data.keys()))
            
            # Show maturity structure if exists
            maturity = a.analysis_data.get('maturity', {})
            if isinstance(maturity, dict):
                print('\n=== MATURITY STRUCTURE ===')
                print('Maturity keys:', list(maturity.keys()))
                print('Domain scores:', maturity.get('domain_scores', {}))

asyncio.run(check())
