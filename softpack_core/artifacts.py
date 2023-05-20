"""Copyright (c) Wellcome Sanger Institute.

This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.
"""

import itertools
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Iterator, Optional

import pygit2
from box import Box

from .app import app
from .ldapapi import LDAP


class Artifacts:
    """Artifacts repo access class."""

    environments_root = "environments"

    @dataclass
    class Object:
        path: Path
        obj: pygit2.Object

        @property
        def oid(self) -> pygit2.Oid:
            return self.obj.oid

        @property
        def name(self) -> str:
            return self.obj.name

        @property
        def data(self) -> list[bytes]:
            return self.obj.data

        def get(self, key: str) -> "Artifacts.Object":
            return Artifacts.Object(path=self.path, obj=self.obj[key])

        def spec(self) -> Box:
            spec = self.obj["softpack.yml"]
            return Box.from_yaml(spec.data)

        def __iter__(self) -> Iterator[Any]:
            for obj in iter(self.obj):
                path = self.path / obj.name
                yield Artifacts.Object(
                    path=path.relative_to(Artifacts.environments_root), obj=obj
                )

    def __init__(self) -> None:
        """Constructor."""
        self.ldap = LDAP()
        self.settings = app.settings

        path = self.settings.artifacts.path / ".git"
        credentials = pygit2.UserPass(
            self.settings.artifacts.repo.reader.username,
            self.settings.artifacts.repo.reader.password,
        )
        callbacks = pygit2.RemoteCallbacks(credentials=credentials)

        if path.is_dir():
            self.repo = pygit2.Repository(path)
        else:
            self.repo = pygit2.clone_repository(
                self.settings.artifacts.repo.url,
                path=path,
                callbacks=callbacks,
                bare=True,
            )

        self.reference = "/".join(
            [
                "refs/remotes",
                self.repo.remotes[0].name,
                self.repo.head.shorthand,
            ]
        )

    def user_folder(self, user: Optional[str] = None) -> Path:
        return self.environments_folder("users", user)

    def group_folder(self, group: Optional[str] = None) -> Path:
        return self.environments_folder("groups", group)

    def environments_folder(self, *args: Optional[str]) -> Path:
        return Path(self.environments_root, *filter(None, list(args)))

    def iter_user(self, user: Optional[str] = None) -> list[pygit2.Tree]:
        return self.iter_environments(self.user_folder(user))

    def iter_group(self, group: Optional[str] = None) -> list[pygit2.Tree]:
        return self.iter_environments(self.group_folder(group))

    def iter_environments(self, path: Path) -> list[pygit2.Tree]:
        return [path / folder.name for folder in self.tree(str(path))]

    def tree(self, path: str) -> pygit2.Tree:
        """Return a Tree object.

        Args:
            path: index into the repo

        Returns:
            Tree: A Tree object
        """
        return self.repo.lookup_reference(self.reference).peel().tree[path]

    def environments(self, path: Path) -> Iterable:
        """Return a list of environments in the repo.

        Args:
            path: a searchable path within the repo

        Returns:
            Iterator: a pygit2.Tree or an empty iterator
        """
        try:
            return self.Object(path=path, obj=self.tree(str(path)))
        except KeyError:
            return iter(())

    def iter(self, user: Optional[str] = None) -> Iterable:
        """Return am iterator for the specified user.

        Args:
            user: a username

        Returns:
            Iterator: an iterator
        """
        try:
            if user:
                folders = list(
                    itertools.chain(
                        [self.user_folder(user)],
                        map(self.group_folder, self.ldap.groups(user)),
                    )
                )
            else:
                folders = self.iter_user() + self.iter_group()

            return itertools.chain.from_iterable(
                map(self.environments, folders)
            )

        except KeyError:
            return iter(())
