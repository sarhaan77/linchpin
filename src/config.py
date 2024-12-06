import logging

import instructor
from browserbase import Browserbase
from openai import AsyncOpenAI
from pydantic_settings import BaseSettings, SettingsConfigDict
from supabase import Client, create_client


class Settings(BaseSettings):
    API_PORT: int
    RAILWAY_ENVIRONMENT_NAME: str

    BROWSERBASE_API_KEY: str
    BROWSERBASE_PROJECT_ID: str

    SUPABASE_URL: str
    SUPABASE_KEY: str
    DISCORD_TOKEN: str
    OPENAI_API_KEY: str

    @property
    def browserbase(self):
        return Browserbase(api_key=self.BROWSERBASE_API_KEY)

    @property
    def supabase_client(self) -> Client:
        return create_client(self.SUPABASE_URL, self.SUPABASE_KEY)

    @property
    def async_openai_client(self):
        return instructor.from_openai(
            client=AsyncOpenAI(api_key=self.OPENAI_API_KEY),
        )

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()


def setup_logger(name=__name__, level=logging.INFO):
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Add console handler if it doesn't exist
    if not logger.handlers:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)

        # Create formatter
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        console_handler.setFormatter(formatter)

        # Add handler to the logger
        logger.addHandler(console_handler)

    return logger
