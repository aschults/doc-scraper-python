"""Test the extract_doc script with file-based cases."""
from os import path
import os

from absl.testing import flagsaver  # type: ignore
from pyfakefs import fake_filesystem_unittest  # type: ignore

import extract_doc


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

    @flagsaver.flagsaver  # type: ignore
    def test_simple(self):
        """Test a simple strip elements pipeline."""
        base_dir = path.dirname(__file__)
        test_dir = path.join(base_dir, 'test_extract_doc_files')

        for test_case_dir in os.listdir(test_dir):
            full_test_case_dir = path.join(test_dir, test_case_dir)
            if not path.isdir(full_test_case_dir):
                continue

            os.chdir(full_test_case_dir)
            print(os.listdir('.'))
            flagsaver.FLAGS.config_sample = False
            flagsaver.FLAGS.config = path.join(full_test_case_dir,
                                               'config.yaml')
            flagsaver.FLAGS.mark_as_parsed()
            extract_doc.main([])

            with open('expected.json', 'r', encoding='utf8') as expected_file:
                expected = expected_file.read()
            with open('/result.json', 'r', encoding='utf8') as result_file:
                actual = result_file.read()

            self.assertEqual(expected, actual)
