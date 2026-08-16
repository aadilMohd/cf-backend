from pydantic_setting import BaseSettings

class Settings(BaseSettings):
    database_url: str
    jwt_secret: str
    otp_provider_api_key: str

    class Config:
        env_file: ".env"

setting= Settings()
