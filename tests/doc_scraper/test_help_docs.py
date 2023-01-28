"""Tests for the classes to provide help texts."""
# pylint: disable=protected-access

import unittest
from typing import Optional
import re
import dataclasses

from doc_scraper import help_docs


class AsYamlTest(unittest.TestCase):
    """Test conversion to YAML."""

    def _strip_indent(self,
                      expected: str,
                      strip_prefix: Optional[str] = None) -> str:
        """Remove leading spaces from each line."""
        expected_list = expected.split('\n')
        if re.match(r'^\s*$', expected_list[0]):
            expected_list = expected_list[1:]

        if strip_prefix is None:
            match = re.match(r'^(\s+)', expected_list[0])
            if match:
                strip_prefix = match.group(1)

        if strip_prefix is None:
            strip_prefix = ''
        return '\n'.join(
            (line.removeprefix(strip_prefix) for line in expected_list))

    def assert_equal_without_indent(self, expected: str, actual: str):
        """Compare two strings, removing indenttion from first one."""
        self.assertEqual(self._strip_indent(expected), actual)

    def test_text_convertible_prefix_lines(self):
        """Test the prefix_text_lines function."""
        conv = help_docs.TextConvertible()
        self.assertEqual(
            'x_line1\nx_  line2\nx_line3',
            conv._prefix_text_lines(  # type: ignore
                'line1\n  line2\nline3',
                'x_',
            ))
        self.assertEqual(
            'x_line1',
            conv._prefix_text_lines(  # type: ignore
                'line1',
                'x_',
            ))
        self.assertEqual(
            'x_',
            conv._prefix_text_lines(  # type: ignore
                '',
                'x_',
            ))

    def test_text_convertible_values_as_yaml(self):
        """Test the values_as_yaml function."""
        conv = help_docs.TextConvertible()

        self.assertEqual(
            '"string"',
            conv._values_as_yaml('string'),  # type: ignore
        )
        self.assertEqual(
            'string',
            conv._values_as_yaml(  # type: ignore
                help_docs.RawSample('string')),
        )
        self.assertEqual(
            '123.4',
            conv._values_as_yaml(123.4),  # type: ignore
        )

    def test_config_field_as_yaml(self):
        """Test converting the config field class to YAML."""
        doc = help_docs.ConfigFieldHelp(
            'thename',
            str,
            'helptext',
            [('case1', 1234), ('case2', 'stringarg')],
        )
        expected = '''
        # helptext
        thename: 1234  # case1
            # thename: "stringarg"  # case2'''
        self.assert_equal_without_indent(expected, doc.as_yaml())

    def test_config_as_yaml(self):
        """Test converting the config class to YAML."""
        doc = help_docs.ConfigHelp(
            'thename', 'thetext',
            [help_docs.ConfigFieldHelp('a', str, 'c', [])])

        expected = '''
        # c
        a:'''
        self.assert_equal_without_indent(expected, doc.as_yaml())

    def test_builder_kind_as_yaml(self):
        """Test converting the builder kind class to YAML."""
        doc = help_docs.BuilderKindHelp(
            'thename', 'thetext',
            help_docs.ConfigHelp(
                'name2', 'text2',
                [help_docs.ConfigFieldHelp('a', str, 'c', [])]))

        expected = '''
        kind: thename
        # text2
        config:
          # c
          a:
        '''
        self.assert_equal_without_indent(expected, doc.as_yaml())

    def test_builder_as_yaml(self):
        """Test converting the builder class to YAML."""
        doc = help_docs.BuilderHelp([
            help_docs.BuilderKindHelp(
                'thename', 'thetext',
                help_docs.ConfigHelp('name2', 'text2', [
                    help_docs.ConfigFieldHelp('a', str, 'c', [('txt', 'VAL')])
                ]))
        ])
        spc = '  '
        expected = f'''
        # thetext
        - kind: thename
          # text2
          config:
            # c
            a: "VAL"  # txt
        {spc}
        '''
        self.assert_equal_without_indent(expected, doc.as_yaml())

    def test_pipeline_as_yaml(self):
        """Test converting the pipeline class to YAML."""
        builder_help = help_docs.BuilderHelp([
            help_docs.BuilderKindHelp(
                'thename', 'thetext',
                help_docs.ConfigHelp('name2', 'text2', []))
        ])

        doc = help_docs.PipelineHelp('sometext', builder_help, builder_help,
                                     builder_help)
        spc4 = '    '
        spc6 = '      '
        expected = f'''
        #
        # sometext
        #
        # Load from various sources (some are aware of command line arg)
        sources:
            # thetext
            - kind: thename
              text2config:
        {spc6}
        {spc4}

        # Steps executed in order to modify the documents
        transformations:
            # thetext
            - kind: thename
              text2config:
        {spc6}
        {spc4}

        # Places to write down the result
        sinks:
            # thetext
            - kind: thename
              text2config:
        {spc6}
        {spc4}'''
        self.assert_equal_without_indent(expected, doc.as_yaml())


@dataclasses.dataclass()
class SampleConfig():
    """classdocstring."""

    a_field: int = dataclasses.field(
        metadata={
            'help_text': 'thehelptext',
            'help_samples': [('text1', 111), (222), ('value3')]
        })


class TestCreation(unittest.TestCase):
    """Test help doc classes creation."""

    def test_from_dataclasses_field(self):
        """Create config field from dataclass.Field."""
        field = dataclasses.fields(SampleConfig)[0]
        self.assertEqual(
            help_docs.ConfigFieldHelp('a_field',
                                      int, 'thehelptext', [('text1', 111),
                                                           ('', 222),
                                                           ('', 'value3')]),
            help_docs.ConfigFieldHelp.from_dataclasses_field(field))

    def test_config_from_config_class(self):
        """Create config class."""
        self.assertEqual(
            help_docs.ConfigHelp('SampleConfig', 'classdocstring.', [
                help_docs.ConfigFieldHelp('a_field', int, 'thehelptext',
                                          [('text1', 111), ('', 222),
                                           ('', 'value3')]),
            ]),
            help_docs.ConfigHelp.from_config_class(SampleConfig),
        )

    def test_builder_kind_from_config_class(self):
        """Test creating builder kind help doc."""
        self.assertEqual(
            help_docs.BuilderKindHelp(
                'something', 'kindtext',
                help_docs.ConfigHelp('SampleConfig', 'classdocstring.', [
                    help_docs.ConfigFieldHelp('a_field', int, 'thehelptext',
                                              [('text1', 111), ('', 222),
                                               ('', 'value3')]),
                ])),
            help_docs.BuilderKindHelp.from_config_class(
                'something', 'kindtext', SampleConfig),
        )
