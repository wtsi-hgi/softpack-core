"""Copyright (c) 2023 Genome Research Ltd.

This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.
"""

import itertools
import json
import shutil
import tempfile
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Iterable, Iterator, List, Optional, Tuple, Union, cast

import pygit2
import strawberry
import yaml
from box import Box
from fastapi import UploadFile

from softpack_core.spack import PackageBase

from .app import app
from .ldapapi import LDAP


@strawberry.type
class Package(PackageBase):
    """A Strawberry model representing a package."""

    version: Optional[str] = None

    @classmethod
    def from_name(cls, name: str) -> 'Package':
        """Makes a new Package based on the name.

        Args:
            name (str): Combined name and version string, deliniated by an '@'.

        Returns:
            Package: A Package with name set, and version set if given name had
                     a version.
        """
        parts = name.split("@", 2)

        if len(parts) == 2:
            return Package(name=parts[0], version=parts[1])

        return Package(name=name)


@strawberry.type
class Interpreters:
    """A Strawberry model representing the interpreters in an environment."""

    r: Optional[str] = None
    python: Optional[str] = None


@strawberry.enum
class State(Enum):
    """Environment states."""

    ready = 'ready'
    queued = 'queued'
    failed = 'failed'
    waiting = 'waiting'


@strawberry.enum
class Type(Enum):
    """Environment types."""

    softpack = "softpack"
    module = "module"


class Artifacts:
    """Artifacts repo access class."""

    recipes_root = "recipes"
    environments_root = "environments"
    environments_file = "softpack.yml"
    builder_out = "builder.out"
    module_file = "module"
    readme_file = "README.md"
    meta_file = "meta.yml"
    spack_file = "spack.lock"
    built_by_softpack_file = ".built_by_softpack"
    built_by_softpack = Type.softpack.value
    generated_from_module_file = ".generated_from_module"
    generated_from_module = Type.module.value
    users_folder_name = "users"
    groups_folder_name = "groups"
    credentials_callback = None

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
            """Get dictionary of the softpack.yml file contents.

            Also includes the contents of any README.md file.

            Returns:
                Box: A boxed dictionary.
            """
            info = Box.from_yaml(self.obj[Artifacts.environments_file].data)

            if Artifacts.readme_file in self.obj:
                info["readme"] = self.obj[Artifacts.readme_file].data.decode()

            if Artifacts.generated_from_module_file in self.obj:
                info["type"] = Artifacts.generated_from_module
            else:
                info["type"] = Artifacts.built_by_softpack

            info.packages = list(
                map(lambda p: Package.from_name(p), info.packages)
            )

            if Artifacts.module_file in self.obj:
                info["state"] = State.ready
            elif Artifacts.builder_out in self.obj:
                info["state"] = State.failed
            elif any(pkg.name.startswith("*") for pkg in info.packages):
                info["state"] = State.waiting
            else:
                info["state"] = State.queued

            metadata = self.metadata()

            info["tags"] = getattr(metadata, "tags", [])
            info["hidden"] = getattr(metadata, "hidden", False)
            info["force_hidden"] = getattr(metadata, "force_hidden", False)
            info["created"] = getattr(metadata, "created", 0)
            info["username"] = getattr(metadata, "username", None)
            info["failure_reason"] = getattr(metadata, "failure_reason", None)

            info["interpreters"] = Interpreters()

            if Artifacts.spack_file in self.obj:
                hasR = False
                hasPython = False

                for pkg in cast(list[Package], info["packages"]):
                    if pkg.name == "r":
                        hasR = True

                    if pkg.name == "python":
                        hasPython = True

                    if hasR and hasPython:
                        break

                if not hasR or not hasPython:
                    data = json.loads(self.obj[Artifacts.spack_file].data)

                    for hash in data.get("concrete_specs", {}):
                        spec = data["concrete_specs"][hash]

                        if not hasR and spec.get("name", "") == "r":
                            hasR = True
                            info["interpreters"].r = spec.get("version", "")

                        if not hasPython and spec.get("name", "") == "python":
                            hasPython = True
                            info["interpreters"].python = spec.get(
                                "version", ""
                            )

                        if hasR and hasPython:
                            break

            return info

        def metadata(self) -> Box:
            """Returns the metadata for an Environment.

            Should contain keys:
                - tags: list[string]
                - hidden: boolean
                - force_hidden: boolean
            """
            meta = Box()
            if Artifacts.meta_file in self.obj:
                meta = Box.from_yaml(self.obj[Artifacts.meta_file].data)

            return meta

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

        credentials = None
        try:
            credentials = pygit2.UserPass(
                self.settings.artifacts.repo.username,
                self.settings.artifacts.repo.writer,
            )
        except Exception as e:
            print(e)

        self.credentials_callback = pygit2.RemoteCallbacks(
            credentials=credentials
        )

    @dataclass
    class RecipeObject:
        """The Recipe object represents the data for a requested recipe."""

        name: str
        version: str
        description: str
        url: str
        username: str

    @property
    def signature(self) -> pygit2.Signature:
        """Get current pygit2 commit signature: author/committer/timestamp."""
        # creating one of these implicitly looks up the current time.
        return pygit2.Signature(
            self.settings.artifacts.repo.author,
            self.settings.artifacts.repo.email,
        )

    def clone_repo(self, branch: Optional[str] = None) -> None:
        """Clone the specified branch (default main) to path in settings."""
        if branch is None:
            branch = self.settings.artifacts.repo.branch

        if branch is None:
            branch = "main"

        path = self.settings.artifacts.path.expanduser() / ".git"
        if path.is_dir():
            shutil.rmtree(path)

        self.repo = pygit2.clone_repository(
            self.settings.artifacts.repo.url,
            path=path,
            callbacks=self.credentials_callback,
            bare=True,
            checkout_branch=branch,
        )

        self.reference = "/".join(
            [
                "refs/remotes",
                self.repo.remotes[0].name,
                self.repo.head.shorthand,
            ]
        )

    def create_remote_branch(self, branch: str) -> None:
        """Create a branch in remote if it doesn't exist yet."""
        temp_dir = tempfile.TemporaryDirectory()

        repo = pygit2.clone_repository(
            self.settings.artifacts.repo.url,
            path=temp_dir.name,
            callbacks=self.credentials_callback,
            bare=True,
        )

        try:
            repo.branches['origin/' + branch]
        except KeyError:
            commit = repo.revparse_single('HEAD')
            repo.create_branch(branch, commit)

            remote = repo.remotes[0]
            remote.push(
                [f'refs/heads/{branch}'], callbacks=self.credentials_callback
            )

    def user_folder(self, user: Optional[str] = None) -> Path:
        """Get the user folder for a given user.

        Args:
            user: A username or None.

        Returns:
            Path: A user folder.
        """
        return self.environments_folder(self.users_folder_name, user)

    def group_folder(self, group: Optional[str] = None) -> Path:
        """Get the group folder for a given group.

        Args:
            group: A group name or None.

        Returns:
            Path: A group folder.
        """
        return self.environments_folder(self.groups_folder_name, group)

    def environments_folder(self, *args: Optional[str]) -> Path:
        """Get the folder under the environments folder.

        Args:
            args: Optional path

        Returns:
            Path: A folder under environments.
        """
        return Path(self.environments_root, *filter(None, list(args)))

    def iter_users(self) -> list[pygit2.Tree]:
        """Iterate environments for all users.

        Returns:
            list[pygit2.Tree]: List of environments
        """
        return self.iter_environments(
            self.environments_folder(self.users_folder_name)
        )

    def iter_groups(self) -> list[pygit2.Tree]:
        """Iterate environments for all groups.

        Returns:
            list[pygit2.Tree]: List of environments
        """
        return self.iter_environments(
            self.environments_folder(self.groups_folder_name)
        )

    def iter_environments(self, path: Path) -> list[pygit2.Tree]:
        """Iterate environments under a path.

        Args:
            path: Path to folder under environments.

        Returns:
            list[pygit2.Tree]: List of environments
        """
        try:
            return [path / folder.name for folder in self.tree(str(path))]
        except KeyError:
            return list(())

    def tree(self, path: str) -> pygit2.Tree:
        """Return a Tree object.

        Args:
            path: index into the repo

        Returns:
            Tree: A Tree object
        """
        return self.repo.lookup_reference(self.reference).peel().tree[path]

    def environments(self, path: Path) -> Iterable:
        """Return a list of environments in the repo under the given path.

        Args:
            path: a searchable path within the repo

        Returns:
            Iterator: a pygit2.Tree or an empty iterator
        """
        try:
            return self.Object(path=path, obj=self.tree(str(path)))
        except KeyError:
            return iter(())

    def iter(self) -> Iterable:
        """Return an iterator over all environments.

        Returns:
            Iterator: an iterator
        """
        folders = self.iter_users() + self.iter_groups()

        return itertools.chain.from_iterable(map(self.environments, folders))

    def get(self, path: Path, name: str) -> Optional[Object]:
        """Return the environment at the specified name and path.

        Args:
            path: the path containing the environment folder
            name: the name of the environment folder

        Returns:
            Object: an Object or None
        """
        try:
            return self.Object(
                Path(path, name),
                self.tree(str(self.environments_folder(str(path), name))),
            )
        except KeyError:
            return None

    def create_recipe_request(self, recipe: RecipeObject) -> pygit2.Oid:
        """Create a recipe request.

        Args:
            recipe: the recipe to be created.
        """
        return self.commit_and_push(
            self.create_file(
                Path(self.recipes_root),
                recipe.name + "-" + recipe.version,
                yaml.dump(recipe),
                True,
            ),
            "add recipe request",
        )

    def get_recipe_request(
        self, name: str, version: str
    ) -> Optional[RecipeObject]:
        """Get the details of a requested recipe.

        Args:
            name: the name of the recipe.
            version: the version of the recipe.
        """
        try:
            recipeData = self.tree(self.recipes_root)[name + "-" + version]
        except Exception:
            return None

        if not recipeData:
            return None

        return cast(Artifacts.RecipeObject, Box.from_yaml(recipeData.data))

    def remove_recipe_request(self, name: str, version: str) -> pygit2.Oid:
        """Remove a recipe request.

        Args:
            name: the name of the recipe.
            version: the version of the recipe.
        """
        try:
            recipeData = self.tree(self.recipes_root)[name + "-" + version]
        except Exception:
            raise FileNotFoundError("recipe request does not exist")

        if not recipeData:
            raise FileNotFoundError("recipe request does not exist")

        return self.commit_and_push(
            self.remove(Path(self.recipes_root), name + "-" + version),
            "removed recipe request",
        )

    def iter_recipe_requests(self) -> Iterable[RecipeObject]:
        """Iterate over recipe requests."""
        try:
            tree = self.tree(self.recipes_root)
        except Exception:
            return []

        for recipe in tree:
            yield cast(Artifacts.RecipeObject, Box.from_yaml(recipe.data))

    def commit_and_push(
        self, tree_oid: pygit2.Oid, message: str
    ) -> pygit2.Oid:
        """Commit and push current changes to the remote repository.

        Args:
            tree_oid: the oid of the tree object that will be committed. The
            tree this refers to will replace the entire contents of the repo.
            message: the commit message

        Returns:
            pygit2.Oid: the ID of the new commit
        """
        ref = self.repo.head.name
        parents = [self.repo.lookup_reference(ref).target]
        oid = self.repo.create_commit(
            ref, self.signature, self.signature, message, tree_oid, parents
        )
        remote = self.repo.remotes[0]
        remote.push([self.repo.head.name], callbacks=self.credentials_callback)
        return oid

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
                sub_treebuilder = repo.TreeBuilder(
                    root_tree[str(path.parent)]
                    if str(path.parent) != "."
                    else root_tree
                )
            except KeyError:
                sub_treebuilder = repo.TreeBuilder()

            sub_treebuilder.insert(
                path.name, new_tree, pygit2.GIT_FILEMODE_TREE
            )
            new_tree = sub_treebuilder.write()
            path = path.parent
        return new_tree

    def create_file(
        self,
        folder_path: Path,
        file_name: str,
        contents: str,
        new_folder: bool = False,
        overwrite: bool = False,
    ) -> pygit2.Oid:
        """Create one or more file in the artifacts repo.

        Args:
            folder_path: the path to the folder the file will be placed in
            file_name: the name of the file
            contents: the contents of the file
            new_folder: if True, create the file's parent folder as well
            overwrite: if True, overwrite the file at the specified path

        Returns:
            the OID of the new tree structure of the repository
        """
        return self.create_files(
            folder_path, [(file_name, contents)], new_folder, overwrite
        )

    def create_files(
        self,
        full_path: Path,
        files: List[Tuple[str, Union[str, UploadFile]]],
        new_folder: bool = False,
        overwrite: bool = False,
    ) -> pygit2.Oid:
        """Create one or more files in the artifacts repo.

        Args:
            folder_path: the path to the folder the files will be placed
            files: Array of tuples, containing file name and contents.
            file_name: the name of the file
            contents: the contents of the file
            new_folder: if True, create the file's parent folder as well
            overwrite: if True, overwrite the file at the specified path

        Returns:
            the OID of the new tree structure of the repository
        """
        for file_name, _ in files:
            try:
                tree = self.tree(str(full_path))
            except Exception:
                continue

            if not overwrite and tree and file_name in tree:
                raise FileExistsError("File already exists")

        root_tree = self.repo.head.peel(pygit2.Tree)

        if new_folder and (full_path not in root_tree or overwrite):
            new_treebuilder = self.repo.TreeBuilder()
        else:
            folder = root_tree[full_path]
            new_treebuilder = self.repo.TreeBuilder(folder)

        for file_name, contents in files:
            if isinstance(contents, str):
                file_oid = self.repo.create_blob(contents)
            else:
                file_oid = self.repo.create_blob_fromiobase(contents.file)
            new_treebuilder.insert(
                file_name, file_oid, pygit2.GIT_FILEMODE_BLOB
            )

        new_tree = new_treebuilder.write()

        # Expand to include the whole repo
        full_tree = self.build_tree(self.repo, root_tree, new_tree, full_path)

        # Check for errors in the new tree
        new_tree = self.repo.get(full_tree)
        diff = self.repo.diff(new_tree, root_tree)
        if len(diff) > len(files):
            raise RuntimeError("Too many changes to the repo")
        elif len(diff) < 1:
            raise RuntimeError("No changes made to the environment")

        return full_tree

    def delete_environment(
        self,
        name: str,
        path: str,
    ) -> pygit2.Oid:
        """Delete an environment folder in GitLab.

        Args:
            name: the name of the environment
            path: the path of the environment

        Returns:
            the OID of the new tree structure of the repository
        """
        if len(Path(path).parts) != 2:
            raise ValueError("Not a valid environment path")

        return self.remove(Path(self.environments_root, path), name)

    def remove(self, full_path: Path, name: str) -> pygit2.Oid:
        """Remove a target from the artefacts repo.

        Args:
            full_path: the parent directory to remove from
            name: the file/directory to remove from the parent
        """
        # Get repository tree
        root_tree = self.repo.head.peel(pygit2.Tree)
        # Find environment in the tree
        target_tree = root_tree[full_path]
        # Remove the environment
        tree_builder = self.repo.TreeBuilder(target_tree)
        tree_builder.remove(name)
        new_tree = tree_builder.write()

        return self.build_tree(self.repo, root_tree, new_tree, full_path)


artifacts = Artifacts()
