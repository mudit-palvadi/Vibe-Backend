from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str
    # the old supabase project, only used by the keepalive and the migration scripts
    SUPABASE_URL: str
    CLOUDINARY_CLOUD_NAME: str
    CLOUDINARY_API_KEY: str
    CLOUDINARY_API_SECRET: str

    # google oauth, the client id is checked against the id token audience
    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_JWKS_URL: str = "https://www.googleapis.com/oauth2/v3/certs"
    GOOGLE_TOKEN_URL: str = "https://oauth2.googleapis.com/token"
    GOOGLE_ISSUER: str = "https://accounts.google.com"

    # the session token we sign ourselves after the google login
    SESSION_SECRET: str = Field(min_length=32)
    SESSION_TTL_DAYS: int = 30
    SESSION_ISSUER: str = "vibe-backend"

    # the s3 bucket that holds the song files
    S3_BUCKET: str = ""
    S3_REGION: str = "ap-south-1"
    MEDIA_BASE_URL: str = ""
    S3_UPLOAD_URL_EXPIRY: int = 900

    # the old cloudinary upload endpoint, it is turned off when the client
    # uses the s3 upload
    LEGACY_UPLOAD_ENABLED: bool = True

    # only needed by the one off scripts that read the old supabase data
    SUPABASE_SERVICE_ROLE_KEY: str = ""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
