"""Copyright (c) 2024 Genome Research Ltd.

This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.
"""

import getpass

import os

import ldap

from softpack_core.schemas.groups import Group


def test_groups(mocker) -> None:
    username = os.environ.get("LDAP_USER", getpass.getuser())
    groups = list(Group.from_username(username))
    assert len(groups)
    assert groups[0].name

    groups = list(Group.from_username("foo"))
    assert not len(groups)

    def search_s(*args):
        return [
            ("cn=testteam,ou=group,dc=foo", {"cn": [b"testteam"]}),
            ("cn=otherteam,ou=group,dc=foo", {"cn": [b"otherteam"]}),
        ]

    mocker.patch.object(
        ldap.ldapobject.SimpleLDAPObject, "search_s", new=search_s
    )

    groups = list(Group.from_username("foo"))
    group_names = {group.name for group in groups}
    assert group_names == {"testteam", "otherteam"}
