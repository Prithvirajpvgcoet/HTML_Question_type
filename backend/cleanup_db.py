import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
from database import engine
from sqlalchemy import text

async def cleanup():
    async with engine.begin() as conn:
        await conn.execute(text('''DELETE FROM evaluation_results WHERE submission_id IN (
            SELECT id FROM submissions
            WHERE coalesce(submitted_css,'')='' AND coalesce(submitted_js,'')=''
            AND coalesce(submitted_html,'') IN ('', '<!-- Write your HTML code here -->'))'''))
        await conn.execute(text('''DELETE FROM submissions
            WHERE coalesce(submitted_css,'')='' AND coalesce(submitted_js,'')=''
            AND coalesce(submitted_html,'') IN ('', '<!-- Write your HTML code here -->')'''))
    print('Cleaned up DB')

asyncio.run(cleanup())
