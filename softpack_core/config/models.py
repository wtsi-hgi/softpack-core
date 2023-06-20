"""Copyright (c) 2023 Genome Research Ltd.

This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.
"""

from pathlib import Path
from typing import Optional

from pydantic import AnyHttpUrl, AnyUrl, BaseModel, HttpUrl


class ServerConfig(BaseModel):
    """Server config model."""

    class HeaderConfig(BaseModel):
        """Header config."""

        origins: list[AnyHttpUrl]

    header: HeaderConfig
    host: str
    port: int


class VaultConfig(BaseModel):
    """HashiCorp vault config."""

    url: HttpUrl
    path: Path
    token: str


class Credentials(BaseModel):
    """Credentials model."""

    username: str
    password: str


class ArtifactsConfig(BaseModel):
    """Artifacts config model."""

    class Repo(BaseModel):
        """Repo model."""

        url: AnyUrl
        reader: Optional[Credentials]
        writer: Optional[Credentials]

    path: Path
    repo: Repo


class LDAPConfig(BaseModel):
    """LDAP config model."""

    class GroupConfig(BaseModel):
        """LDAP group config."""

        attr: str
        pattern: str

    server: AnyUrl
    retries: int = 3
    base: str
    filter: str
    group: GroupConfig
