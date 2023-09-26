"""Copyright (c) 2023 Genome Research Ltd.

This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.
"""

import re
from pathlib import Path
from string import Template
from typing import Union, cast


def ToSoftpackYML(name: str, contents: Union[bytes, str]) -> bytes:
    """Converts an shpc-style module file to a softpack.yml file.

    It should have a format similar to that produced by shpc, with `module
    whatis` outputting a "Name: " line, a "Version: " line, and optionally a
    "Packages: " line to say what packages are available. Each package should
    be separated by a comma.

    `module help` output will be translated into the description in the
    softpack.yml.

    Args:
        contents (bytes): The byte content of the module file.

    Returns:
        bytes: The byte content of the softpack.yml file.
    """
    in_help = False

    version = ""
    packages: list[str] = []
    description = ""

    contents_bytes: bytes

    if type(contents) == str:
        contents_bytes = contents.encode()
    else:
        contents_bytes = cast(bytes, contents)

    for line in contents_bytes.splitlines():
        line = line.lstrip()
        if in_help:
            if line == b"}":
                in_help = False
            elif line.startswith(b"puts stderr "):
                line_str = (
                    line.removeprefix(b"puts stderr")
                    .lstrip()
                    .decode('unicode_escape')
                    .replace("\\$", "$")
                    .removeprefix("\"")
                    .removesuffix("\"")
                )
                description += "  " + line_str + "\n"
        else:
            if line.startswith(b"proc ModulesHelp"):
                in_help = True
            elif line.startswith(b"module-whatis "):
                line_str = (
                    line.removeprefix(b"module-whatis")
                    .lstrip()
                    .decode('unicode_escape')
                    .removeprefix("\"")
                    .removesuffix("\"")
                    .lstrip()
                )

                if line_str.startswith("Name:"):
                    nv = line_str.removeprefix("Name:")
                    if nv != "":
                        name_value = list(
                            map(lambda x: x.strip().split()[0], nv.split(":"))
                        )

                        if name_value[0] is not None:
                            name = name_value[0]

                        if len(name_value) > 1 and name_value[1] != "":
                            version = name_value[1].strip()
                elif line_str.startswith("Version:"):
                    ver = line_str.removeprefix("Version:")
                    if ver != "":
                        vers = ver.split()[0]
                        if vers is not None and vers != "":
                            version = vers
                elif line_str.startswith("Packages:"):
                    packages = list(
                        filter(
                            None,
                            map(
                                lambda x: x.strip(),
                                re.split(
                                    r'[,\s]+',
                                    line_str.removeprefix("Packages:"),
                                ),
                            ),
                        )
                    )

    if version != "":
        name += f"@{version}"

    packages.insert(0, name)

    package_str = "\n  - ".join(packages)

    return (
        f"description: |\n{description}packages:\n  - {package_str}\n".encode()
    )


def GenerateEnvReadme(module_path: str) -> bytes:
    """Generates a simple README file for the environment.

    Args:
        module_path (str): The module path as used by the module command.

    Returns:
        bytes: The byte content of the README.md file.
    """
    with open(Path(__file__).parent / "templates" / "readme.tmpl", "r") as fh:
        tmpl = Template(fh.read())

    return tmpl.substitute({"module_path": module_path}).encode()
