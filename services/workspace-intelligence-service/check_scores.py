import asyncio
from database.config import DatabaseManager
from database.models import ProjectAnalysis
from sqlalchemy import select

async def check():
    db = DatabaseManager()
    async with db.get_session() as s:
        stmt = select(ProjectAnalysis).where(
            ProjectAnalysis.id == '162f422e-b811-4b01-b981-6b6cdbc7a620'
        )
        r = await s.execute(stmt)
        a = r.scalar_one_or_none()
        
        if not a:
            print('Analysis not found')
            return
            
        print('=== FOLDER ANALYSIS SCORES ===')
        print(f'Overall Maturity: {a.overall_maturity_score}')
        print(f'Implementation Score: {a.implementation_score}')
        print(f'Build/Deployment Score: {a.build_deployment_score}')
        print(f'Maturity Level: {a.maturity_level}')
        print(f'Scope: {a.analysis_scope}')
        print(f'Project: {a.project_name}')

asyncio.run(check())
