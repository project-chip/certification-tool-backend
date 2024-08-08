import sys
from pathlib import Path

from test_collections.matter.sdk_tests.support.python_testing.models.python_test_parser import (
    parse_python_script,
)

path: Path = Path(sys.argv[1])
print(path)
parse_python_script(path)
