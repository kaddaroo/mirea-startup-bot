import asyncio
import os
from urllib.parse import urlsplit
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("DATABASE_URL not set in .env")
    raise SystemExit(1)

parsed_url = urlsplit(DATABASE_URL)
safe_url = f"{parsed_url.scheme}://{parsed_url.hostname}:{parsed_url.port or 3306}{parsed_url.path}"

async def main():
    print("Using DATABASE_URL:", safe_url)
    engine = create_async_engine(DATABASE_URL, echo=False)
    try:
        async with engine.begin() as conn:
            res = await conn.execute(text("SELECT VERSION()"))
            version = await res.scalar_one_or_none()
            print("Connected. MySQL version:", version)
    except Exception as e:
        print("Connection failed:", repr(e))
    finally:
        await engine.dispose()

if __name__ == '__main__':
    asyncio.run(main())
