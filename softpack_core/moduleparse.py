"""Copyright (c) 2023 Genome Research Ltd.

This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.
"""


def ToSoftpackYML(contents: bytes) -> bytes:
    mode = 0

    name = ""
    version = ""
    packages: list[str] = []
    description = ""

    for line in contents.splitlines():
        line = line.lstrip()
        match mode:
            case 0:
                if line.startswith(b"proc ModulesHelp"):
                    mode = 1
                elif line.startswith(b"module-whatis "):
                    line = line.removeprefix(
                        b"module-whatis ").decode('unicode_escape').removeprefix("\"").removesuffix("\"").lstrip()
                    print(line)
                    if line.startswith("Name: "):
                        nv = line.removeprefix("Name: ").split(":")
                        name = nv[0]
                        if len(nv) > 1:
                            version = nv[1]
                    elif line.startswith("Version: "):
                        version = line.removeprefix("Version: ")
                    elif line.startswith("Packages: "):
                        packages = line.removeprefix("Packages: ").split(", ")
            case 1:
                if line == b"}":
                    mode = 0
                elif line.startswith(b"puts stderr "):
                    line = line.removeprefix(b"puts stderr ").decode(
                        'unicode_escape').replace("\\$", "$").removeprefix("\"").removesuffix("\"")
                    description += "  " + line + "\n"

    if version != "":
        name += f"@{version}"

    packages.insert(0, name)

    package_str = "\n  - ".join(packages)

    return f"description: |\n{description}packages:\n  - {package_str}\n".encode()
