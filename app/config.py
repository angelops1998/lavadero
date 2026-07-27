from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    database_url: str
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 480
    https_only: bool = False

    # Negocio
    negocio_nombre: str = "Lavandería"
    codigo_pais: str = "591"
    base_url: str = "http://localhost:8000"
    # Días que un pedido puede estar "listo" antes de alertar que no lo retiran.
    dias_alerta_retiro: int = 3
    # Días desde que está listo para considerar que la ropa quedó abandonada.
    dias_abandono: int = 30
    # Ancho del papel de la impresora térmica, en mm (58 y 80 son los estándares).
    ticket_ancho_mm: int = 58

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    try:
        settings = Settings()
    except Exception:
        raise SystemExit(
            "\n[ERROR] No se pudo cargar la configuración.\n"
            "Asegurate de que existe el archivo .env con DATABASE_URL y SECRET_KEY.\n"
        )
    if not settings.secret_key:
        raise SystemExit(
            "\n[ERROR] SECRET_KEY está vacío en el .env.\n"
            "Generá una clave con: python -c \"import secrets; print(secrets.token_hex(64))\"\n"
        )
    return settings
