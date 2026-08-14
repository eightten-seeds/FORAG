import logging.config


def configure_logging(level: str = "INFO") -> None:
    """Configure a small console logger shared by the application."""

    normalized_level = level.upper()
    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
                }
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "default",
                    "level": normalized_level,
                }
            },
            "root": {"handlers": ["console"], "level": normalized_level},
        }
    )
