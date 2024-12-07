import instructor
from browserbase import Browserbase
from openai import AsyncOpenAI
from pydantic_settings import BaseSettings, SettingsConfigDict
from supabase import Client, create_client


class Settings(BaseSettings):
    PORT: int
    RAILWAY_ENVIRONMENT_NAME: str

    BROWSERBASE_API_KEY: str
    BROWSERBASE_PROJECT_ID: str

    SUPABASE_URL: str
    SUPABASE_KEY: str
    DISCORD_TOKEN: str
    OPENAI_API_KEY: str
    JINA_API_KEY: str

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
