import asyncpg


async def get_user(pool: asyncpg.Pool, user_id: int) -> str | None:
    async with pool.acquire() as conn:
        return await conn.fetchval(
            """
            SELECT input_name 
            FROM users
            WHERE user_id = $1
            """,
            user_id,
        )
