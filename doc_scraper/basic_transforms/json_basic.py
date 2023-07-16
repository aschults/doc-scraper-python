"""JSON query based extraction from documents."""

from typing import Mapping, Any, Sequence, Callable
import dataclasses
import logging

from doc_scraper import json_query
from doc_scraper import doc_struct


@dataclasses.dataclass(kw_only=True)
class JsonExtractionTransformConfig():
    """Extract and render a list of items from a document."""

    preamble: str = dataclasses.field(
        default='',
        metadata={
            'help_text': 'Prepended to the query, for common functions.',
            'help_samples': [
                ('def plus_1: . + 1;'),
                ('def constant: 123;'),
            ]
        })

    extract_all: str = dataclasses.field(
        metadata={
            'help_text':
                'Query to extract all items to be processed at this level.',
            'help_samples': [
                ('Match all paragraphs', '.. | select(.type? == "Paragraph")'),
                ('Match all with tag "label"', '.. | select(.tags?.label)'),
            ]
        })
    render: str = dataclasses.field(
        default='.',
        metadata={
            'help_text':
                'Applied to each extracted item before output into a list.',
            'help_samples': [('{"the_text": .text?, "tag": $nested_tag, ' +
                              '"nested": $nested_types}')],
        })

    first_item_only: bool = dataclasses.field(
        default=False,
        metadata={
            'help_text': 'Only take the first item of the result.',
            'help_samples': [('Default', False)],
        })

    filters: Sequence[str] = dataclasses.field(
        default_factory=list,
        metadata={
            'help_text':
                'Only extracted items matching all filters remain.',
            'help_samples': [([
                '.tags?.label == "some_value"',
                '.text | test("\\d+")',
            ])],
        })

    validators: Sequence[str] = dataclasses.field(
        default_factory=list,
        metadata={
            'help_text':
                'Only items matching all filters, plus warning on log.',
            'help_samples': [([
                '.type',
            ])],
        })

    nested: 'Mapping[str, JsonExtractionTransformConfig]' = dataclasses.field(
        default_factory=dict,
        metadata={
            'help_text':
                'Extract nested items and use as variables when rendering',
            'help_samples': [{
                'nested_types': {
                    'extract_all': '.elements| select(.type =="Paragraph")',
                    'render': '.tags?.label',
                },
                'nested_tag': {
                    'extract_all': '.elements|.tags?.label',
                    'render': '"_"+.+"_"'
                },
            }]
        })

    def _add_preamble(self, query: str) -> str:
        """Add the preamble to queries for convenience."""
        return f'{self.preamble}\n{query}'

    # pytype: disable=attribute-error

    def __post_init__(self):
        """Turn all query strings into query objects."""
        self._filter_progs = json_query.Filter(
            *map(self._add_preamble, self.filters))
        self._valid_progs = json_query.Filter(
            *map(self._add_preamble, self.validators))
        self._base_prog = json_query.Query(
            self._add_preamble(self.extract_all),)

    def _validate_item(self, data: Any) -> bool:
        """Find items not matching the validatiors and log them."""
        validation_fails = self._valid_progs.get_unmatched(data)
        for expr in validation_fails:
            logging.warning('Item is not valid, JSON expression %r fails: %r',
                            expr, data)
        return not bool(validation_fails)

    def _render_output(self, item: Any) -> Any:
        """Produce the desired output JSON structure."""
        nested_extracted = {
            name: nested_config.transform_items(item)
            for name, nested_config in self.nested.items()
        }
        jq_output_prog = json_query.Query(self._add_preamble(self.render),
                                          **nested_extracted)
        output = jq_output_prog.get_first(item)
        if not json_query.is_output(output):
            logging.warning('No value for expr %r on item %r', jq_output_prog,
                            item)
            output = None
        return output

    def transform_items(self, data: Any) -> Any:
        """Transform JSON or doc_struct items according to config.

        Args:
            data: doc_struct Element or JSON structure.

        Returns: JSON structure.
        """
        if isinstance(data, doc_struct.Element):
            data = doc_struct.as_dict(data)

        base_items = self._base_prog.get_all(data)
        base_items = self._filter_progs.filter(base_items)
        base_items = [item for item in base_items if self._validate_item(item)]
        base_items = [self._render_output(item) for item in base_items]
        if self.first_item_only:
            if len(base_items) > 0:
                return base_items[0]
            else:
                return None
        return base_items

    # pytype: enable=attribute-error


def build_json_extraction_transform(
        config: JsonExtractionTransformConfig) -> Callable[[Any], Any]:
    """Produce an extraction transformation."""

    def the_transform(data: Any) -> Any:
        return config.transform_items(data)

    return the_transform
