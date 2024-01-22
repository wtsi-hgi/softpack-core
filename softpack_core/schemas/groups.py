"""Copyright (c) 2024 Genome Research Ltd.

This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.
"""

from dataclasses import dataclass
from typing import Iterable

import strawberry

from ..ldapapi import LDAP


@strawberry.type
class Group:
    """A Strawberry model representing a single unix group."""

    name: str

    @classmethod
    def from_username(cls, username: str) -> Iterable["Group"]:
        """Get the groups the given user belongs to.

        Args:
            username: Their usernamer.

        Returns:
            Iterable: An iterator over unix group names.
        """

        groups = LDAP().groups(username)
        return (Group(name=group) for group in groups)


class GroupsSchema:
    """Group schema."""

    @dataclass
    class Query:
        """GraphQL query schema."""

        groups: list[Group] = Group.from_username  # type: ignore
