"""Test the extract_doc script with file-based cases."""
from os import path
import os
from typing import Sequence, Tuple

from absl.testing import flagsaver  # type: ignore
from pyfakefs import fake_filesystem_unittest  # type: ignore
from parameterized import parameterized  # type:ignore

import doc_scraper.extract_doc as extract_doc


class ExtractDocTest(fake_filesystem_unittest.TestCase):
    """Test the main script, using test_extract_doc_files/* as test cases.

    Test cases are arranged in subdirectories, one per test case.
    Each test case directory contains:

    *   config.yaml: The config to use as --config
        Additional data files in the test case directory can be added
    *   expected.json: Needs to match /result.json in the fake filesystem

    cwd is set to the test case directory (inside the fake filesystem), so
    test files can be accessed with relative paths.
    """

    def setUp(self) -> None:
        """Set up fake filesustem and test case data."""
        base_dir = path.dirname(__file__)
        self.test_dir = path.join(base_dir, 'test_extract_doc_files')
        self.setUpPyfakefs()
        self.fs.add_real_directory(self.test_dir)  # type: ignore
        return super().setUp()

    @staticmethod
    def list_test_case_dirs() -> Sequence[Tuple[str, str]]:
        """Generate all test names and paths to parametrize test."""
        base_dir = path.dirname(__file__)
        test_dir = path.join(base_dir, 'test_extract_doc_files')
        test_case_dirs = ((directory, path.join(test_dir, directory))
                          for directory in os.listdir(test_dir))
        return [
            dirs for dirs in test_case_dirs
            if path.isdir(dirs[1])
        ]

    @parameterized.expand(list_test_case_dirs())  # type:ignore
    @flagsaver.flagsaver  # type: ignore
    # pylint: disable=unused-argument
    def test_main(self, name: str, full_test_case_dir: str):
        """Test the extract_doc main function on multiple configs/data."""
        os.chdir(full_test_case_dir)
        print(os.listdir('.'))
        flagsaver.FLAGS.config_sample = False
        flagsaver.FLAGS.config = path.join(full_test_case_dir, 'config.yaml')
        flagsaver.FLAGS.mark_as_parsed()
        extract_doc.main([])

        with open('expected.json', 'r', encoding='utf8') as expected_file:
            expected = expected_file.read()
        with open('/tmp/result.json', 'r', encoding='utf8') as result_file:
            actual = result_file.read()

        self.maxDiff = None
        self.assertEqual(expected, actual)
