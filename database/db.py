import asyncpg


async def upsert_user(
    pool: asyncpg.Pool,
    user_id: int,
    username: str | None,
    full_name: str,
    input_name: str,
) -> None:
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO users
            (user_id, username, full_name, input_name)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (user_id)
            DO UPDATE SET
                username = EXCLUDED.username,
                full_name = EXCLUDED.full_name,
                input_name = EXCLUDED.input_name
            """,
            user_id,
            username,
            full_name,
            input_name,
        )
