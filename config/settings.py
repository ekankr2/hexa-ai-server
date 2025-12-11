from functools import lru_cache
from pydantic_settings import BaseSettings
from pydantic import ConfigDict


class Settings(BaseSettings):
    """애플리케이션 전체 설정"""

    model_config = ConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore"  # .env의 extra 필드 무시
    )

    # MySQL URL (필수)
    MYSQL_URL: str

    # Redis URL (필수)
    REDIS_URL: str

    # OpenAI Settings (필수)
    OPENAI_API_KEY: str

    # Environment
    ENV: str = "development"  # "development" or "production"

    @property
    def is_production(self) -> bool:
        return self.ENV == "production"

    @property
    def BASE_URL(self) -> str:
        if self.is_production:
            return "https://hexa-ai-server-production.up.railway.app"
        return "http://localhost:8000"

    @property
    def FRONTEND_URL(self) -> str:
        if self.is_production:
            return "https://hexa-frontend-chi.vercel.app"
        return "http://localhost:3000"

    # Google OAuth Settings
    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: str

    @property
    def google_redirect_uri(self) -> str:
        """Google OAuth 콜백 URI (BASE_URL에서 자동 생성)"""
        return f"{self.BASE_URL}/auth/google/callback"

    @property
    def database_url(self) -> str:
        """SQLAlchemy용 URL 반환 (mysql:// -> mysql+pymysql://)"""
        if self.MYSQL_URL.startswith("mysql://"):
            return self.MYSQL_URL.replace("mysql://", "mysql+pymysql://", 1)
        return self.MYSQL_URL


@lru_cache()
def get_settings() -> Settings:
    """설정 싱글톤 반환 (캐싱)"""
    return Settings()