import asyncio
from sqlalchemy import text
from app.database import AsyncSessionLocal
import os

async def f():
    async with AsyncSessionLocal() as db:
        files = ['../database/migrations/003_seed.sql', '../database/migrations/004_phase2_additions.sql']
        for file_path in files:
            if not os.path.exists(file_path):
                print(f"Skipping {file_path}, not found.")
                continue
                
            print(f"Running {file_path}...")
            with open(file_path) as file:
                sql = file.read()
            
            # Split by statements
            for stmt in sql.split(';'):
                if stmt.strip():
                    try:
                        await db.execute(text(stmt.strip()))
                    except Exception as e:
                        print(f"Error on stmt in {file_path}:", e)
            
        await db.commit()
        print("Data sources seed done")

asyncio.run(f())
