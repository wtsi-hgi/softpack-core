"""Copyright (c) 2023 Genome Research Ltd.

This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.
"""

from pathlib import Path

import yaml

from softpack_core.moduleparse import ToSoftpackYML


def pytest_generate_tests(metafunc):
    if "module_spec" not in metafunc.fixturenames:
        return

    with open(Path(__file__).parent / "data/specs/modules/tests.yml") as f:
        yml = yaml.safe_load(f)

    metafunc.parametrize(
        "module_spec",
        yml["tests"],
    )


def test_tosoftpack(module_spec) -> None:
    path = module_spec["path"]
    output = module_spec.get("output")
    fail_message = module_spec.get("fail")

    with open(Path(Path(__file__).parent, path), "rb") as fh:
        module_data = fh.read()

    try:
        yml = ToSoftpackYML(module_data)
    except any as e:
        assert e.message == fail_message
        return

    with open(Path(Path(__file__).parent, output), "rb") as fh:
        expected_yml = fh.read()
        assert yml == expected_yml
