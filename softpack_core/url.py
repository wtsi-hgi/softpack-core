"""Copyright (c) 2023 Genome Research Ltd.

This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.
"""

from typing import Optional
from urllib.parse import urlparse, urlunparse


class URL:
    """URL building and parsing class."""

    def __init__(
        self,
        url: Optional[str] = None,
        scheme: Optional[str] = None,
        netloc: Optional[str] = None,
        path: Optional[str] = None,
        params: Optional[str] = None,
        query: Optional[str] = None,
        fragment: Optional[str] = None,
    ):
        """Constructor.

        Args:
            url: URL
            scheme: Scheme part of the URL.
            netloc: Netloc part of the URL.
            path: Path part of the URL.
            params: Params part of the URL.
            query: Query part of the URL.
            fragment: Fragment part of the URL.
        """
        parts = urlparse(url or "")

        def select(value: Optional[str], default: str) -> str:
            return value if value is not None else default

        self.scheme = select(scheme, parts.scheme)
        self.netloc = select(netloc, parts.netloc)
        self.path = select(path, parts.path)
        self.params = select(params, parts.params)
        self.query = select(query, parts.query)
        self.fragment = select(fragment, parts.fragment)

    def urn(self) -> str:
        """Return a Uniform Resource Name (without the protocol).

        Returns:
            str: URN as a string
        """
        urn = URL(str(self), scheme="")
        return str(urn).lstrip("/")

    def unparse(self) -> str:
        """Build a url from its parts.

        Returns:
            str: URL as a string.
        """
        return urlunparse(
            (
                self.scheme,
                self.netloc,
                self.path,
                self.params,
                self.query,
                self.fragment,
            )
        )

    def __str__(self) -> str:
        """String representation of a URL.

        Returns:
            str: URL as a string.
        """
        return str(self.unparse())

    def __repr__(self) -> str:
        """String representation of a URL.

        Returns:
            str: URL as a string.
        """
        return str(self.unparse())
