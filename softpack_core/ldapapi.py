"""Copyright (c) 2023 Genome Research Ltd.

This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.
"""

import re
from typing import Any, Callable, Iterable, cast

from ldap3 import (
    AUTO_BIND_NO_TLS,
    SUBTREE,
    Connection,
)
from ldap3.core.exceptions import LDAPException
from ldap3.utils.conv import escape_filter_chars
from typing_extensions import Self

from .app import app
from .config.models import LDAPConfig


class LDAP:
    """LDAP interface."""

    def __init__(self) -> None:
        """Constructor."""
        if app.settings.ldap is not None:
            self.settings = cast(LDAPConfig, app.settings.ldap)
            self.initialize()

    def initialize(self) -> None:
        """Initialize an LDAP client.

        Returns:
            None.
        """
        try:
            self.ldap = Connection(
                self.settings.server, auto_bind=AUTO_BIND_NO_TLS
            )
            self.group_regex = re.compile(self.settings.group.pattern)
        except AttributeError as e:
            print(f"{__file__}: AttributeError: {e}")

    def filter_groups(self, groups: Iterable) -> list[str]:
        """Filter groups by exclusion pattern.

        Args:
            groups: List of groups to filter.

        Returns:
            list[str]: Filtered list of groups
        """
        return list(filter(self.group_regex.match, groups))

    def parse_group(self, group: tuple[str, dict[str, list[bytes]]]) -> str:
        """Parse and decode a group name from search results.

        Args:
            group: Group entry to parse

        Returns:
            str: Parsed and decoded group name
        """
        return group[1][self.settings.group.attr][0].decode(encoding='UTF-8')

    def reconnect(fn: Callable[..., Any]) -> Any:  # type: ignore
        """Reconnect decorator for attempting multiple retries on failure.

        Args:
            fn: Function to wrap in the decorator.

        Returns:
            Any:  Return value from the decorated function.
        """

        def wrapped_function(self: Self, *args: Any, **kwargs: Any) -> Any:
            try:
                # Attempt up to self.settings.retries times
                retries = getattr(self.settings, "retries", 1) or 1
                for _ in range(retries):
                    try:
                        return fn(self, *args, **kwargs)
                    except LDAPException:
                        # Reinitialize connection and retry
                        self.initialize()
                        continue
                # All retries failed
                return None
            except AttributeError as e:
                print(f"{__file__}: AttributeError: {e}")

        return wrapped_function

    @reconnect
    def groups(self, user: str) -> list[str]:
        """Return a list of groups a user belongs to.

        Args:
            user: Username

        Returns:
            list[str]: List of groups
        """
        try:
            # Escape any special chars in the username before inserting into filter
            safe_user = escape_filter_chars(user)
            # Build filter and ensure RFC4515 form by wrapping in parentheses if missing.
            search_filter = self.settings.filter.format(user=safe_user)
            if not (search_filter.startswith("(") and search_filter.endswith(")")):
                search_filter = f"({search_filter})"
            self.ldap.search(
                search_base=self.settings.base,
                search_scope=SUBTREE,
                search_filter=search_filter,
                attributes=(self.settings.group.attr,),
            )
            # Convert ldap3 entries to tuples compatible with parse_group
            groups = [
                (
                    entry.entry_dn,
                    {
                        self.settings.group.attr: [
                            getattr(entry, self.settings.group.attr)[
                                0
                            ].encode()
                        ]
                    },
                )
                for entry in self.ldap.entries
            ]

            return sorted(self.filter_groups(map(self.parse_group, groups)))
        except AttributeError as e:
            print(f"{__file__}: AttributeError: {e}")
            return []
        except LDAPException as e:
            print(f"{__file__}: LDAPException: {e}")
            return []
