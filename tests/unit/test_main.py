"""Copyright (c) 2023 Genome Research Ltd.

This source code is licensed under the MIT license found in the
LICENSE file in the root directory of this source tree.
"""

import sys
from pathlib import Path

import pytest

from softpack_core.main import main


def test_main(capsys) -> None:
    with pytest.raises(SystemExit):
        main(0)
    captured = capsys.readouterr()
    command = Path(sys.argv[0])
    assert f"{command.name} [OPTIONS] COMMAND [ARGS]" in captured.err
