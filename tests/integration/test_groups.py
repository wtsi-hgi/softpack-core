"""Copyright (c) 2024 Genome Research Ltd.

This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.
"""

import getpass

from softpack_core.schemas.groups import Group


def test_groups() -> None:
    username = getpass.getuser()
    groups = list(Group.from_username(username))
    print(groups)
    assert len(groups)
    assert groups[0].name

    groups = list(Group.from_username("foo"))
    assert not len(groups)

    # mocked version with better test?...
