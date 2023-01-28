"""Test the pipeline sink classes."""

import dataclasses
import unittest
from typing import Type, List
import io

from pyfakefs import fake_filesystem_unittest  # type: ignore

from doc_scraper.pipeline import sinks
from doc_scraper import doc_struct


def _create_dummy_doc(tag_string: str,
                      attr_data: int = 991199) -> doc_struct.Document:
    """Create a doc with a single text run for tests."""
    return doc_struct.Document(
        attrs={'attr_data': attr_data},
        shared_data=doc_struct.SharedData(),
        content=doc_struct.DocContent(elements=[
            doc_struct.Paragraph(
                elements=[doc_struct.TextRun(text=tag_string)])
        ]))


def _get_doc_tag(doc: sinks.SinkItemType) -> str:
    """From a dummy doc, extract first text run of first paragraph."""
    if not isinstance(doc, doc_struct.Document):
        raise AssertionError('need to have document instance')
    paragraph = doc.content.elements[0]
    if not isinstance(paragraph, doc_struct.Paragraph):
        raise AssertionError('Not a paragraph')
    return paragraph.elements[0].as_plain_text()


@dataclasses.dataclass(kw_only=True)
class ConfigForTest():
    """Config to test sink builder functions."""

    attr_a: int = 0
    attr_b: str = ''
    attr_c: Type[doc_struct.Element] = doc_struct.Element


class TestSinkBuilder(unittest.TestCase):
    """Test the sink builder."""

    def setUp(self) -> None:
        """Provide a default sink builder and output capturing."""
        super().setUp()

        self.builder = sinks.SinkBuilder()

        self.output: List[sinks.SinkItemType] = []
        self.output2: List[sinks.SinkItemType] = []
        self.config: List[str] = []

    def _process_output(self, doc: sinks.SinkItemType) -> None:
        """Output function to capture into `self.output`."""
        self.output.append(doc)

    def _process_output2(self, doc: sinks.SinkItemType) -> None:
        """Output function to capture into `self.output2`."""
        self.output2.append(doc)

    def _build_output_with_config(self,
                                  config_string: str) -> sinks.OutputFunction:
        """Create output function from config."""

        def output_func(doc: sinks.SinkItemType) -> None:
            self.output.append(doc)
            self.config.append(config_string)

        return output_func

    def test_create_instance(self):
        """Test the creation of a simple sink function."""
        self.builder.register('x', lambda: self._process_output)

        func = self.builder.create_instance('x')
        func([_create_dummy_doc('a'), _create_dummy_doc('b')])

        self.assertEqual(['a', 'b'],
                         [_get_doc_tag(item) for item in self.output])

    def test_create_instance_configured(self):
        """Test creation of sink function inclduing configuration."""
        self.builder.register('x', self._build_output_with_config)

        func = self.builder.create_instance('x', 'add')
        func([_create_dummy_doc('a'), _create_dummy_doc('b')])

        self.assertEqual(['a', 'b'],
                         [_get_doc_tag(item) for item in self.output])
        self.assertEqual(['add', 'add'], self.config)

    def test_create_instance_multiplex(self):
        """Test the creation of a multiplexed sink, to both outputs."""
        self.builder.register('x', lambda: self._process_output)
        self.builder.register('y', lambda: self._process_output2)

        func = self.builder.create_multiplexed(sinks.OutputConfig(kind='x'),
                                               sinks.OutputConfig(kind='y'))
        func([_create_dummy_doc('a'), _create_dummy_doc('b')])

        self.assertEqual(['a', 'b'],
                         [_get_doc_tag(item) for item in self.output])
        self.assertEqual(['a', 'b'],
                         [_get_doc_tag(item) for item in self.output2])


# JSON template of the serialized form of a document.
JSON_OUTPUT_TEMPLATE = '''{
    "attrs": {
        "attr_data": 991199
    },
    "shared_data": {
        "type": "SharedData"
    },
    "content": {
        "elements": [
            {
                "elements": [
                    {
                        "text": "__tag__",
                        "type": "TextRun"
                    }
                ],
                "type": "Paragraph"
            }
        ],
        "type": "DocContent"
    },
    "type": "Document"
}'''


class TestFileOutput(fake_filesystem_unittest.TestCase):
    """Test the individual output classes."""

    def setUp(self) -> None:
        """Set up fake filesystem."""
        super().setUp()
        self.setUpPyfakefs()

    def test_single_output(self):
        """Test writing multiple docs to single file."""
        output_file = io.StringIO()
        stream_out = sinks.SingleFileOutput(output_file=output_file,
                                            separator='xxx')

        stream_out(_create_dummy_doc('a'))
        stream_out(_create_dummy_doc('b'))

        expected = JSON_OUTPUT_TEMPLATE.replace(
            '__tag__', 'a') + 'xxx' + JSON_OUTPUT_TEMPLATE.replace(
                '__tag__', 'b')
        self.assertMultiLineEqual(expected, output_file.getvalue())

    def test_templated_path(self):
        """Tst output to multiple files using template names."""
        templated_output = sinks.TemplatedPathOutput('/file{i}')
        templated_output(_create_dummy_doc('a'))
        templated_output(_create_dummy_doc('b'))

        self.assertEqual(JSON_OUTPUT_TEMPLATE.replace('__tag__', 'a'),
                         self.fs.get_object('/file0').contents)  # type: ignore
        self.assertEqual(JSON_OUTPUT_TEMPLATE.replace('__tag__', 'b'),
                         self.fs.get_object('/file1').contents)  # type: ignore

    def test_templated_path_with_attrs(self):
        """Tst output to multiple files based on document.attrs dict."""
        templated_output = sinks.TemplatedPathOutput('/file{attr_data}')
        templated_output(_create_dummy_doc('__tag__', 222))

        self.assertEqual(
            JSON_OUTPUT_TEMPLATE.replace('991199', '222'),
            self.fs.get_object('/file222').contents)  # type: ignore
