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


class BuilderConfig(BaseModel):
    """Builder config model."""

    host: str
    port: int


class VaultConfig(BaseModel):
    """HashiCorp vault config."""

    url: HttpUrl
    path: Path
    token: str


class ArtifactsConfig(BaseModel):
    """Artifacts config model."""

    class Repo(BaseModel):
        """Repo model."""

        url: AnyUrl
        username: Optional[str]
        author: str
        email: str
        reader: Optional[str]
        writer: Optional[str]
        branch: Optional[str]

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


class SpackConfig(BaseModel):
    """Spack config model."""

    repo: str
    bin: str
    cache: Optional[str]


class EmailConfig(BaseModel):
    """Email settings to send recipe requests to."""

    toAddr: Optional[str]
    fromAddr: Optional[str]
    smtp: Optional[str]
    localHostname: Optional[str]
