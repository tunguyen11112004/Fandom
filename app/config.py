from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Fan Hub Plus"
    api_prefix: str = "/api/be/v1"
    secret_key: str = "change-me-to-a-long-random-string"
    access_token_minutes: int = 30
    refresh_token_days: int = 7
    email_verify_hours: int = 24
    password_reset_minutes: int = 30
    database_url: str = "mysql+pymysql://root@127.0.0.1:3306/fanhubplus"
    frontend_origin: str = "http://127.0.0.1:5000"
    public_base_url: str = "http://127.0.0.1:5000"
    email_backend: str = "console"
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "noreply@fanhubplus.com"
    seed_admin_email: str = "admin@fanhubplus.com"
    seed_admin_password: str = "Admin123!"
    seed_admin_name: str = "Fan Hub Admin"


settings = Settings()
