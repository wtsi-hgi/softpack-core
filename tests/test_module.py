"""Copyright (c) 2023 Genome Research Ltd.

This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.
"""

from pathlib import Path
import pygit2

from softpack_core.module import GenerateEnvReadme, ToSoftpackYML


def pytest_generate_tests(metafunc):
    if "module_input" not in metafunc.fixturenames:
        return

    metafunc.parametrize(
        "module_input",
        list((Path(__file__).parent / "files" / "modules").glob("*.mod")),
    )


def test_tosoftpack(module_input: Path) -> None:
    output = str(module_input).removesuffix(".mod") + ".yml"

    with open(module_input, "rb") as fh:
        module_data = fh.read()

    yml = ToSoftpackYML(module_input.name.removesuffix(".mod"), module_data)

    with open(output, "rb") as fh:
        expected_yml = fh.read()
        assert yml == expected_yml


def test_generate_env_readme() -> None:
    test_files_dir = Path(__file__).parent / "files" / "modules"

    readme_data = GenerateEnvReadme("HGI/common/some_environment")

    with open(test_files_dir / "shpc.readme", "rb") as fh:
        expected_readme_data = fh.read()

    assert readme_data == expected_readme_data
