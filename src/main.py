import asyncio
import logging
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import TelegramObject, Update
from aiogram.types.base import UNSET
from prometheus_client import Summary, start_wsgi_server
from pydantic import SecretStr
from pydantic_settings import SettingsConfigDict, BaseSettings

from cmd_router import router

REQUEST_TIME = Summary(
    "request_processing_seconds", "Time spent processing request", ["event_type"]
)


class UpdatesDumperMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: Update,
        data: Dict[str, Any],
    ) -> Any:
        labeled_time = REQUEST_TIME.labels(event_type=event.event_type)
        with labeled_time.time():
            json_event = event.model_dump_json(exclude_unset=True)
            res = await handler(event, data)
            logging.info(json_event)
            return res


class Settings(BaseSettings):
    BOT_TOKEN: SecretStr

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s: "
        "%(filename)s: "
        "%(levelname)s: "
        "%(funcName)s(): "
        "%(lineno)d:\t"
        "%(message)s",
    )

    settings = Settings()

    bot = Bot(token=settings.BOT_TOKEN.get_secret_value())
    storage = MemoryStorage()
    dispatcher = Dispatcher(storage=storage)
    dispatcher.update.outer_middleware(UpdatesDumperMiddleware())
    dispatcher.include_router(router)
    await dispatcher.start_polling(bot, allowed_updates=UNSET)


if __name__ == "__main__":
    start_wsgi_server(9876)
    asyncio.run(main())
