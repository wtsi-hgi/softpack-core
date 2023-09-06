"""Copyright (c) 2023 Genome Research Ltd.

This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.
"""

from pathlib import Path

import yaml

from softpack_core.moduleparse import ToSoftpackYML


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
