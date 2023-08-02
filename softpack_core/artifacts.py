"""Copyright (c) 2023 Genome Research Ltd.

This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.
"""

import itertools
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator, Optional

import pygit2
from box import Box
from pygit2 import Signature

from .app import app
from .ldapapi import LDAP


class Artifacts:
    """Artifacts repo access class."""

    environments_root = "environments"
    environments_file = "softpack.yml"

    @dataclass
    class Object:
        """An artifact object."""

        path: Path
        obj: pygit2.Object

        @property
        def oid(self) -> pygit2.Oid:
            """Get OID of an artifact.

            Returns:
                pygit2.Oid: Artifact OID.
            """
            return self.obj.oid

        @property
        def name(self) -> str:
            """Get the name of an artifact.

            Returns:
                str: Artifact name.
            """
            return self.obj.name

        @property
        def data(self) -> list[bytes]:
            """Get data from a git object.

            Returns:
                list[bytes]: Data property from the object.
            """
            return self.obj.data

        def get(self, key: str) -> "Artifacts.Object":
            """Get attribute as an Artifact object.

            Args:
                key: Attribute name

            Returns:
                Artifacts.Object: An artifact object.
            """
            return Artifacts.Object(path=self.path, obj=self.obj[key])

        def spec(self) -> Box:
            """Get spec dictionary.

            Returns:
                Box: A boxed dictionary.
            """
            spec = self.obj[Artifacts.environments_file]
            return Box.from_yaml(spec.data)

        def __iter__(self) -> Iterator["Artifacts.Object"]:
            """A generator for returning items under an artifacts.

            Returns:
                Iterator[Artifacts.Object]: An iterator over items under an
                artifact.
            """
            for obj in iter(self.obj):
                path = self.path / obj.name
                yield Artifacts.Object(
                    path=path.relative_to(Artifacts.environments_root), obj=obj
                )

    def __init__(self) -> None:
        """Constructor."""
        self.ldap = LDAP()
        self.settings = app.settings

        path = self.settings.artifacts.path.expanduser() / ".git"
        credentials = None
        try:
            credentials = pygit2.UserPass(
                self.settings.artifacts.repo.username,
                self.settings.artifacts.repo.writer,
            )
        except Exception as e:
            print(e)

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
        """Get the user folder for a given user.

        Args:
            user: A username or None.

        Returns:
            Path: A user folder.
        """
        return self.environments_folder("users", user)

    def group_folder(self, group: Optional[str] = None) -> Path:
        """Get the group folder for a given group.

        Args:
            group: A group name or None.

        Returns:
            Path: A group folder.
        """
        return self.environments_folder("groups", group)

    def environments_folder(self, *args: Optional[str]) -> Path:
        """Get the folder under the environments folder.

        Args:
            args: Optional path

        Returns:
            Path: A folder under environments.
        """
        return Path(self.environments_root, *filter(None, list(args)))

    def iter_user(self, user: Optional[str] = None) -> list[pygit2.Tree]:
        """Iterate environments for a given user.

        Args:
            user: A username or None.

        Returns:
            list[pygit2.Tree]: List of environments
        """
        return self.iter_environments(self.user_folder(user))

    def iter_group(self, group: Optional[str] = None) -> list[pygit2.Tree]:
        """Iterate environments for a given group.

        Args:
            group: A group name or None.

        Returns:
            list[pygit2.Tree]: List of environments
        """
        return self.iter_environments(self.group_folder(group))

    def iter_environments(self, path: Path) -> list[pygit2.Tree]:
        """Iterate environments under a path.

        Args:
            path: Path to folder under environments.

        Returns:
            list[pygit2.Tree]: List of environments
        """
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
        """Return an iterator for the specified user.

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
                        map(self.group_folder, self.ldap.groups(user) or []),
                    )
                )
            else:
                folders = self.iter_user() + self.iter_group()

            return itertools.chain.from_iterable(
                map(self.environments, folders)
            )

        except KeyError:
            return iter(())

    def get(self, path: Path, name: str) -> Optional[pygit2.Tree]:
        """Return the environment at the specified name and path.

        Args:
            path: the path containing the environment folder
            name: the name of the environment folder

        Returns:
            pygit2.Tree: a pygit2.Tree or None
        """
        try:
            return self.tree(str(self.environments_folder(str(path), name)))
        except KeyError:
            return None

    def commit(
        self, repo: pygit2.Repository, tree_oid: pygit2.Oid, message: str
    ) -> pygit2.Commit:
        """Create and return a commit.

        Args:
            repo: the repository to commit to
            tree_oid: the oid of the tree object that will be committed. The
            tree this refers to will replace the entire contents of the repo.
            message: the commit message

        Returns:
            pygit2.Commit: the commit oid
        """
        ref = repo.head.name
        author = committer = Signature(
            self.settings.artifacts.repo.author,
            self.settings.artifacts.repo.email,
        )
        parents = [repo.lookup_reference(ref).target]
        return repo.create_commit(
            ref, author, committer, message, tree_oid, parents
        )

    def error_callback(self, refname: str, message: str) -> None:
        """Push update reference callback.

        Args:
            refname: the name of the reference (on the remote)
            message: rejection message from the remote. If None, the update was
            accepted
        """
        if message is not None:
            print(
                f"An error occurred during push to ref '{refname}': {message}"
            )

    def push(self, repo: pygit2.Repository) -> None:
        """Push all commits to a repository.

        Args:
            repo: the repository to push to
        """
        remote = self.repo.remotes[0]
        credentials = None
        try:
            credentials = pygit2.UserPass(
                self.settings.artifacts.repo.username,
                self.settings.artifacts.repo.writer,
            )
        except Exception as e:
            print(e)
        callbacks = pygit2.RemoteCallbacks(credentials=credentials)
        callbacks.push_update_reference = self.error_callback
        remote.push([repo.head.name], callbacks=callbacks)

    def build_tree(
        self,
        repo: pygit2.Repository,
        root_tree: pygit2.Tree,
        new_tree: pygit2.Oid,
        path: Path,
    ) -> pygit2.Oid:
        """Expand new/updated sub tree to include the entire repository.

        Args:
            repo: a bare repository
            root_tree: the tree containing the entire repository
            new_tree: the oid of the new/updated sub tree to be added to the
            repository
            path: the path from root_tree root to new_tree root
        """
        while str(path) != ".":
            try:
                sub_tree = (
                    root_tree[str(path.parent)]
                    if str(path.parent) != "."
                    else root_tree
                )
            except KeyError:
                raise KeyError(
                    f"{path.parent} does not exist in the repository"
                )
            sub_treebuilder = repo.TreeBuilder(sub_tree)
            sub_treebuilder.insert(
                path.name, new_tree, pygit2.GIT_FILEMODE_TREE
            )
            new_tree = sub_treebuilder.write()
            path = path.parent
        return new_tree

    def generate_yaml_contents(self, env):
        """Generate the softpack.yml file contents.

        Args:
            env: an Environment object
        """
        packages = [
            f"- {pkg.name}@{pkg.version}" if pkg.version else f"- {pkg.name}"
            for pkg in env.packages
        ]
        packages = "\n".join(packages)
        contents = f"description: {env.description}\npackages:\n{packages}\n"
        return contents

    def create_environment(
        self,
        env,
        commit_message: str,
        target_tree: Optional[pygit2.Tree] = None,
    ):
        """Create, commit and push a new environment folder to GitLab.

        Args:
            env: an Environment object
            commit_message: the commit message
            target_tree: pygit2.Tree object with the environment folder you
            want to update as its root
        """
        root_tree = self.repo.head.peel(pygit2.Tree)

        # Create new file
        contents = self.generate_yaml_contents(env)
        file_oid = self.repo.create_blob(contents.encode())

        # Put new file into new env folder
        if target_tree:
            new_treebuilder = self.repo.TreeBuilder(target_tree)
        else:
            new_treebuilder = self.repo.TreeBuilder()
        new_treebuilder.insert(
            self.environments_file, file_oid, pygit2.GIT_FILEMODE_BLOB
        )
        new_tree = new_treebuilder.write()

        # Expand tree to include the whole repo
        full_path = (
            Path(self.environments_root)
            / env.path
            / env.name
            / self.environments_file
        )
        full_tree = self.build_tree(
            self.repo, root_tree, new_tree, full_path.parent
        )

        new_tree = self.repo.get(full_tree)
        # Check for errors in the new tree
        diff = self.repo.diff(new_tree, root_tree)
        if len(diff) > 1:
            raise RuntimeError("Too many changes to the repo")
        elif len(diff) < 1:
            raise RuntimeError("No changes made to the environment")
        elif len(diff) == 1:
            new_file = diff[0].delta.new_file
            if new_file.path != str(full_path):
                raise RuntimeError(
                    f"Attempted to add new file added to incorrect path: \
                        {new_file.path} instead of {full_path}"
                )

        # Commit and push
        self.commit(self.repo, full_tree, commit_message)
        self.push(self.repo)

    def update_environment(
        self, new_env, current_name: str, current_path: str, commit_message: str
    ):
        """Update an existing environment folder in GitLab.

        Args:
            new_env: an updated Environment object
            current_name: the current name of the environment
            current_path: the current path of the environment
        """
        if new_env.name == current_name and new_env.path == current_path:
            # Update environment in the same location
            root_tree = self.repo.head.peel(pygit2.Tree)
            path = Path(self.environments_root) / current_path / current_name
            target_tree = root_tree[path]
            self.create_environment(
                new_env,
                commit_message,
                target_tree,
            )
        else:
            # Update environment in a new location
            raise KeyError("not matching name or path")
            # self.delete_environment()
            # self.create_environment()

    def delete_environment(self, name, path, commit_message):
        """Delete an environment folder in GitLab.
        
        Args:
            name: the name of the environment
            path: the path of the environment
        """
        # Get repository tree
        root_tree = self.repo.head.peel(pygit2.Tree)
        # Find environment in the tree
        full_path = Path(self.environments_root) / path 
        target_tree = root_tree[full_path]
        # Remove the environment
        tree_builder = self.repo.TreeBuilder(target_tree)
        tree_builder.remove(name)
        new_tree = tree_builder.write()
        full_tree = self.build_tree(self.repo, root_tree, new_tree, full_path)

        # Commit and push
        self.commit(self.repo, full_tree, commit_message)
        self.push(self.repo)
