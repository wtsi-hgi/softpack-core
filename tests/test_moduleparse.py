"""Copyright (c) 2023 Genome Research Ltd.

This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.
"""

from pathlib import Path
import pytest
from softpack_core.moduleparse import ToSoftpackYML


def test_tosoftpack() -> None:
    test_files_dir = Path(Path(__file__).parent, "files")

    with open(Path(test_files_dir, "ldsc.module"), "rb") as fh:
        module_data = fh.read()

    with open(Path(test_files_dir, "ldsc.yml"), "rb") as fh:
        expected_yml = fh.read()

    yml = ToSoftpackYML(module_data)

    assert yml == expected_yml
