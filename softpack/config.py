from pathlib import Path
from typing import Any, Tuple

import yaml
from pydantic import AnyHttpUrl, BaseModel, BaseSettings
from pydantic.env_settings import SettingsSourceCallable


class ServerConfig(BaseModel):
    """Server config model."""

    class HeaderConfig(BaseModel):
        """Header config."""

        origins: list[AnyHttpUrl]

    header: HeaderConfig
    host: str
    port: int


class Settings(BaseSettings):
    """Package settings."""

    server: ServerConfig
    
    class Config:
        """Configuration loader."""

        config_dir = "conf"
        config_file = "config.yaml"

        @classmethod
        def file_settings(
            cls, path: Path, settings: BaseSettings
        ) -> dict[str, Any]:
            """Load settings from file.

            Args:
                path: Config file path.
                settings: Base settings object.

            Returns:
                dict[str, Any]: A dictionary of settings.
            """

            if not path.is_file():
                return settings.dict()
            with open(path) as f:
                return yaml.safe_load(f)
            
        @classmethod
        def defaults(cls, settings: BaseSettings) -> dict[str, Any]:
            """Load defaults from config file.

            Args:
                settings: BaseSettings model.

            Returns:
               dict[str, Any]: Settings loaded from default config file.

            """

            package_dir = Path(__file__).parent.absolute()
            path = package_dir / cls.config_dir / cls.config_file
            return cls.file_settings(path, settings)
        
        @classmethod
        def overrides(cls, settings: BaseSettings) -> dict[str, Any]:
            """Load overrides from config file in the current directory.

            Args:
                settings: BaseSettings model.

            Returns:
                dict[str, Any]: Settings loaded from deployment-specific
                config file.

            """
            path = Path.home() / ".softpack/core" / cls.config_file
            return cls.file_settings(path, settings)

        @classmethod
        def customise_sources(
            cls,
            init_settings: SettingsSourceCallable,
            env_settings: SettingsSourceCallable,
            file_secret_settings: SettingsSourceCallable,
        ) -> Tuple[SettingsSourceCallable, ...]:
            """Override the default setting load behavior.

            Args:
                init_settings: initial settings
                env_settings: settings from environment
                file_secret_settings: settings from secrets file

            Returns:
                A tuple of settings sources

            """
            return cls.overrides, cls.defaults, init_settings
