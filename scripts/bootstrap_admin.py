"""Create the first administrator and print its API key exactly once."""

import asyncio
import os

from sqlalchemy import select

from querysmith.auth.api_key import create_api_key
from querysmith.core.config import get_settings
from querysmith.persistence.models import ApiKey, User
from querysmith.persistence.session import create_engine, create_session_factory


async def main() -> None:
    settings = get_settings()
    name = os.environ.get("QS_BOOTSTRAP_ADMIN_NAME")
    if not name:
        raise SystemExit("QS_BOOTSTRAP_ADMIN_NAME is required")
    engine = create_engine(settings.datasource.app_database_url.get_secret_value())
    sessions = create_session_factory(engine)
    raw, record = create_api_key()
    async with sessions() as session, session.begin():
        existing = await session.scalar(select(User).where(User.name == name))
        if existing is not None:
            raise SystemExit("Admin already exists; refusing to create another bootstrap key")
        user = User(name=name)
        session.add(user)
        await session.flush()
        session.add(
            ApiKey(
                user_id=user.id,
                lookup_hash=record.lookup_hash,
                password_hash=record.password_hash,
                scopes=["query", "schema", "admin"],
            )
        )
    await engine.dispose()
    print(raw)


if __name__ == "__main__":
    asyncio.run(main())
