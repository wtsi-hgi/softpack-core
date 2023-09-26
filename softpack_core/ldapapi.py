"""Copyright (c) 2023 Genome Research Ltd.

This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.
"""

import re
from typing import Any, Callable, Iterable, cast

import ldap
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
            self.ldap = ldap.initialize(self.settings.server)
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
                retry = 0
                while retry < self.settings.retries:
                    try:
                        retry += 1
                        return fn(self, *args, **kwargs)
                    except ldap.SERVER_DOWN:
                        self.initialize()
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
            groups = self.ldap.search_s(
                self.settings.base,
                ldap.SCOPE_SUBTREE,
                self.settings.filter.format(user=user),
                (self.settings.group.attr,),
            )
            return sorted(self.filter_groups(map(self.parse_group, groups)))
        except AttributeError as e:
            print(f"{__file__}: AttributeError: {e}")
            return []
        except ldap.SERVER_DOWN as e:
            print(f"{__file__}: AttributeError: {e}")
            return []
