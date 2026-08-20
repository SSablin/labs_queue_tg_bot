import asyncpg


async def init_db(pool: asyncpg.Pool) -> None:
    async with pool.acquire() as conn:
        await conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT,
                    username TEXT,
                    full_name TEXT,
                    input_name TEXT,
                    PRIMARY KEY (user_id));
        """)
