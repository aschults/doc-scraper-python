#/bin/bash
set -x -e
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
flake8 . --count --max-complexity=10 --max-line-length=80 --statistics
pytype . -P . -j 4 --strict-primitive-comparisons --strict-import --precise-return --strict-parameter-checks
pytest-3
python3 -m build
