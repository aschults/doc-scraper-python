"""Tests for the classes to provide help texts."""
# pylint: disable=protected-access

import unittest
from typing import Optional, Any, Sequence
import re
import dataclasses
from parameterized import parameterized  # type:ignore

from doc_scraper import help_docs


@dataclasses.dataclass()
class SampleConfig():
    """classdocstring."""

    a_field: int = dataclasses.field(
        metadata={
            'help_text': 'thehelptext',
            'help_samples': [('text1', 111), (222), ('value3')]
        })


@dataclasses.dataclass()
class SampleConfig2():
    """Used to handle default samples."""

    a_f: int = dataclasses.field(metadata={
        'help_text': 'thehelptext',
    })

    b_f: int = dataclasses.field(
        default=222,
        metadata={
            'help_text': 'thehelptext',
        },
    )

    c_f: int = dataclasses.field(
        default_factory=lambda: 222,
        metadata={
            'help_text': 'thehelptext',
        },
    )

    d_f: Sequence[int] = dataclasses.field(
        default_factory=list,
        metadata={
            'help_text': 'thehelptext',
        },
    )


class SampleSToString():
    """Sample class with specifit string conversion."""

    def __init__(self, text: str) -> None:
        """Create an instance."""
        self.text = text

    def __str__(self) -> str:
        """Convert to string."""
        return f"_{self.text}_"


class TextConvertibleTest(unittest.TestCase):
    """Test the TextConvertible class."""

    @parameterized.expand([  # type:ignore
        (
            'Simple string',
            'xxx',
            '',
            'thekey: "xxx"',
        ),
        (
            'Simple None',
            None,
            '',
            'thekey:',
        ),
        (
            'Simple regex',
            SampleSToString('abc'),
            '',
            'thekey: _abc_',
        ),
        (
            'Simple regex with docstring',
            SampleSToString('abc'),
            'docstring',
            'thekey: _abc_  # docstring',
        ),
        (
            'Array of int',
            [1, 2, 3],
            '',
            'thekey:\n-   1\n-   2\n-   3',
        ),
        (
            'Array of int with docstring',
            [1, 2, 3],
            'docstring',
            'thekey:  # docstring\n-   1\n-   2\n-   3',
        ),
        (
            'Recursive resolution in lists',
            [1, help_docs.RawSample('<<>>')],
            '',
            'thekey:\n-   1\n-   <<>>',
        ),
        (
            'List of dict',
            [{
                'a': 'b',
                'c': 'd'
            }, {
                'e': 'f'
            }],
            '',
            'thekey:\n-   a: "b"\n    c: "d"\n-   e: "f"',
        ),
        (
            'Dict of dict',
            {
                'a': 'b',
                'x': {
                    'c': 'd',
                    'e': 'f'
                }
            },
            '',
            'thekey:\n    a: "b"\n    x:\n        c: "d"\n        e: "f"',
        ),
        (
            'Class based',
            help_docs.ClassBasedSample(SampleConfig),
            '',
            'thekey:\n    # thehelptext\n    a_field: 111  # text1\n' +
            '        # a_field: 222\n' + '        # a_field: "value3"',
        ),
    ])
    # pylint: disable=unused-argument
    def test_dict_values_as_yaml(self, summary: str, data: Any, text: str,
                                 expected: str):
        """Test dict key-value conversions for different values."""
        convertible = help_docs.TextConvertible()
        result = convertible._dict_value_as_yaml(  # type: ignore
            'thekey', text=text, value=data)
        self.assertEqual(expected, result)

    def test_default_samples(self):
        """Test generation of default samples."""
        result = help_docs.ConfigHelp.from_config_class(
            SampleConfig2).as_yaml()
        expected = ('# thehelptext\n' + 'a_f: ...\n' + '# thehelptext\n' +
                    'b_f: 222  # Default\n' + '# thehelptext\n' +
                    'c_f: 222  # Default\n' + '# thehelptext\n' +
                    'd_f:  # Default\n')

        self.assertEqual(expected, result)


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
            [help_docs.ConfigFieldHelp('a', str, 'c', [('', '')])])

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
                [help_docs.ConfigFieldHelp('a', str, 'c', [('', '')])]))

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
        spc = '    '
        expected = f'''
        # thetext
        -   kind: thename
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
        spc8 = '        '
        expected = f'''
        #
        # sometext
        #
        # Load from various sources (some are aware of command line arg)
        sources:
            # thetext
            -   kind: thename
                text2config:
        {spc8}
        {spc4}

        # Steps executed in order to modify the documents
        transformations:
            # thetext
            -   kind: thename
                text2config:
        {spc8}
        {spc4}

        # Places to write down the result
        outputs:
            # thetext
            -   kind: thename
                text2config:
        {spc8}
        {spc4}'''
        self.assert_equal_without_indent(expected, doc.as_yaml())


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
