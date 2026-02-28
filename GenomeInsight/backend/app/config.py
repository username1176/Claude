import os
from pathlib import Path


class Config:
    """Base configuration — shared across all environments.

    Secrets use ``os.environ.get`` so the module can be imported without
    env vars set (Testing/Development override them).  ProductionConfig
    validates that required vars are present.
    """

    BASE_DIR = Path(__file__).resolve().parent.parent

    # Flask
    SECRET_KEY = os.environ.get("SECRET_KEY", "")

    # Database
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        f"sqlite:///{BASE_DIR / 'data' / 'db' / 'genomeinsight.db'}",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # JWT
    JWT_PRIVATE_KEY_PATH = os.environ.get(
        "JWT_PRIVATE_KEY_PATH", str(BASE_DIR / "secrets" / "jwt_private.pem")
    )
    JWT_PUBLIC_KEY_PATH = os.environ.get(
        "JWT_PUBLIC_KEY_PATH", str(BASE_DIR / "secrets" / "jwt_public.pem")
    )
    JWT_ALGORITHM = "HS256"
    JWT_ACCESS_TOKEN_EXPIRES_SECONDS = 900  # 15 minutes
    JWT_REFRESH_TOKEN_EXPIRES_SECONDS = 604800  # 7 days

    # Encryption
    MASTER_ENCRYPTION_KEY = os.environ.get("MASTER_ENCRYPTION_KEY", "")

    # File uploads
    UPLOAD_DIR = Path(
        os.environ.get("UPLOAD_DIR", str(BASE_DIR / "data" / "files"))
    )
    MAX_VCF_SIZE_BYTES = int(os.environ.get("MAX_VCF_SIZE_MB", "500")) * 1024 * 1024
    MAX_BLOOD_FILE_SIZE_BYTES = (
        int(os.environ.get("MAX_BLOOD_FILE_SIZE_MB", "20")) * 1024 * 1024
    )

    # Celery
    CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/1")
    CELERY_RESULT_BACKEND = os.environ.get(
        "CELERY_RESULT_BACKEND", "redis://localhost:6379/2"
    )

    # Redis cache
    REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

    # Microbiome upload limit
    MAX_MICROBIOME_FILE_SIZE_BYTES = (
        int(os.environ.get("MAX_MICROBIOME_FILE_SIZE_MB", "200")) * 1024 * 1024
    )
    NMDC_API_BASE = os.environ.get("NMDC_API_BASE", "https://api.microbiomedata.org")

    # External APIs
    NCBI_API_KEY = os.environ.get("NCBI_API_KEY", "")
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

    # Wearable APIs (Terra / ROOK)
    TERRA_API_KEY = os.environ.get("TERRA_API_KEY", "")
    TERRA_DEV_ID = os.environ.get("TERRA_DEV_ID", "")
    TERRA_REDIRECT_URI = os.environ.get("TERRA_REDIRECT_URI", "")

    # Rate limiting
    RATELIMIT_STORAGE_URI = os.environ.get("REDIS_URL", "redis://localhost:6379/0")


class DevelopmentConfig(Config):
    DEBUG = True
    # In development, allow weaker secrets for convenience
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")
    MASTER_ENCRYPTION_KEY = os.environ.get(
        "MASTER_ENCRYPTION_KEY",
        "dev-master-key-00000000000000000000000000000000",
    )
    # Use in-memory rate limit storage when Redis isn't available
    RATELIMIT_STORAGE_URI = os.environ.get("REDIS_URL", "memory://")


class TestingConfig(Config):
    TESTING = True
    SECRET_KEY = "test-secret-key-that-is-at-least-32-bytes-long"
    MASTER_ENCRYPTION_KEY = "test-master-key-0000000000000000000000000000000"
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    RATELIMIT_STORAGE_URI = "memory://"


class ProductionConfig(Config):
    """Production requires all secrets via env vars — no defaults."""

    SECRET_KEY = os.environ.get("SECRET_KEY", "")
    MASTER_ENCRYPTION_KEY = os.environ.get("MASTER_ENCRYPTION_KEY", "")

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)

    @classmethod
    def validate(cls):
        missing = []
        if not cls.SECRET_KEY:
            missing.append("SECRET_KEY")
        if not cls.MASTER_ENCRYPTION_KEY:
            missing.append("MASTER_ENCRYPTION_KEY")
        if missing:
            raise RuntimeError(
                f"Production config missing required env vars: {', '.join(missing)}"
            )


config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}
