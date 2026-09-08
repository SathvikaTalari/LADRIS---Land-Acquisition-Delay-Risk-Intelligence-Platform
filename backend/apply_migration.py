import asyncio
from sqlalchemy import text
from app.database import AsyncSessionLocal

async def f():
    async with AsyncSessionLocal() as db:
        with open('../database/migrations/005_rbac_roles.sql') as file:
            sql = file.read()
        
        # Split by statements
        for stmt in sql.split(';'):
            if stmt.strip():
                try:
                    # AsyncPG can't execute ALTER TYPE inside a transaction block easily sometimes, 
                    # but let's try. If it fails, we will use raw connection.
                    await db.execute(text(stmt.strip()))
                except Exception as e:
                    print(f"Error on stmt: {stmt.strip()}", e)
        
        await db.commit()
        print("Migration done")

asyncio.run(f())
