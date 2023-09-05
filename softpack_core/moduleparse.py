"""Copyright (c) 2023 Genome Research Ltd.
This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.
"""


def ToSoftpackYML(contents: bytes | str) -> bytes:
    """Converts an shpc-style module file to a softpack.yml file.
    It should have a format similar to that produced by shpc, with `module
    whatis` outputting a "Name: " line, a "Version: " line, and optionally a
    "Packages: " line to say what packages are available. `module help` output
    will be translated into the description in the softpack.yml.
    Args:
        contents (bytes): The byte content of the module file.
    Returns:
        bytes: The byte content of the softpack.yml file.
    """
    in_help = False

    name = ""
    version = ""
    packages: list[str] = []
    description = ""

    if type(contents) == str:
        contents = contents.encode()

    for line in contents.splitlines():
        line = line.lstrip()
        if in_help:
            if line == b"}":
                in_help = False
            elif line.startswith(b"puts stderr "):
                line = (
                    line.removeprefix(b"puts stderr ")
                    .decode('unicode_escape')
                    .replace("\\$", "$")
                    .removeprefix("\"")
                    .removesuffix("\"")
                )
                description += "  " + line + "\n"
        else:
            if line.startswith(b"proc ModulesHelp"):
                in_help = True
            elif line.startswith(b"module-whatis "):
                line = (
                    line.removeprefix(b"module-whatis ")
                    .decode('unicode_escape')
                    .removeprefix("\"")
                    .removesuffix("\"")
                    .lstrip()
                )

                if line.startswith("Name: "):
                    nv = line.removeprefix("Name: ").split(":")
                    name = nv[0]
                    if len(nv) > 1:
                        version = nv[1]
                elif line.startswith("Version: "):
                    version = line.removeprefix("Version: ")
                elif line.startswith("Packages: "):
                    packages = line.removeprefix("Packages: ").split(", ")

    if version != "":
        name += f"@{version}"

    packages.insert(0, name)

    package_str = "\n  - ".join(packages)

    return (
        f"description: |\n{description}packages:\n  - {package_str}\n".encode()
    )
