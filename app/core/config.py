from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str = ""
    # google oauth, the client id is checked against the id token audience
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_JWKS_URL: str = "https://www.googleapis.com/oauth2/v3/certs"
    GOOGLE_TOKEN_URL: str = "https://oauth2.googleapis.com/token"
    GOOGLE_ISSUER: str = "https://accounts.google.com"

    # the session token we sign ourselves after the google login
    SESSION_SECRET: str = ""
    SESSION_SECRET_PARAMETER: str = ""
    SESSION_TTL_DAYS: int = 30
    SESSION_ISSUER: str = "vibe-backend"

    # the s3 bucket that holds the song files
    S3_BUCKET: str = ""
    S3_REGION: str = "ap-south-1"
    MEDIA_BASE_URL: str = ""
    S3_UPLOAD_URL_EXPIRY: int = 900

    # which database the app talks to, sqlmodel or dynamodb
    DB_BACKEND: str = "sqlmodel"
    DYNAMODB_TABLE_NAME: str = "vibe"
    AWS_REGION: str = "ap-south-1"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
