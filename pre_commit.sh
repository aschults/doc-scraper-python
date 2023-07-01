#/bin/bash
set -x -e
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
flake8 . --count --max-complexity=10 --max-line-length=80 --statistics
pycodestyle . || true
pydocstyle --convention=google || true
pytype . -P . -j 4 --strict-primitive-comparisons --strict-import --precise-return --strict-parameter-checks
pytest-3 --cov=doc_scraper/
PYTHONPATH=. python3 doc_scraper/extract_doc.py --config_sample > docs/full_sample_config.yaml
# TODO: Make DocDownloader access credentials late.
# PYTHONPATH=. python3 doc_scraper/extract_doc.py --config=docs/sample_config.yaml --test_config
#PYTHONPATH=. python3 doc_scraper/extract_doc.py --config=docs/full_sample_config.yaml --test_config
python3 -m build
