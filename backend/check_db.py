import asyncio
from sqlalchemy import text
from app.database import AsyncSessionLocal

async def f():
    async with AsyncSessionLocal() as db:
        res = await db.execute(text('SELECT COUNT(*) FROM data_sources'))
        print('Data Sources count:', res.scalar())

asyncio.run(f())
