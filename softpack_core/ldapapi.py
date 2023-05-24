"""Copyright (c) Wellcome Sanger Institute.

This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.
"""

import re
from typing import Iterable

import ldap
import tenacity

from .app import app


class LDAP:
    """LDAP interface."""

    def __init__(self) -> None:
        """Constructor."""
        self.settings = app.settings
        self.initialize()

    def initialize(self) -> None:
        """Initialize an LDAP client.

        Returns:
            None.
        """
        self.ldap = ldap.initialize(self.settings.ldap.server)
        self.group_regex = re.compile(self.settings.ldap.group.pattern)

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
        return group[1][self.settings.ldap.group.attr][0].decode(
            encoding='UTF-8'
        )

    @tenacity.retry(
        stop=tenacity.stop_after_attempt(3), wait=tenacity.wait_fixed(1)
    )
    def groups(self, user: str) -> list[str]:
        """Return a list of groups a user belongs to.

        Args:
            user: Username

        Returns:
            list[str]: List of groups
        """
        self.initialize()
        groups = self.ldap.search_s(
            self.settings.ldap.base,
            ldap.SCOPE_SUBTREE,
            self.settings.ldap.filter.format(user=user),
            (self.settings.ldap.group.attr,),
        )
        return sorted(self.filter_groups(map(self.parse_group, groups)))
