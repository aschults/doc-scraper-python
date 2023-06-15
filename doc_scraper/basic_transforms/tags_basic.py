"""Common classes for working with tags."""

from typing import (
    Optional,
    Sequence,
    Type,
    Any,
    List,
    cast,
    Dict,
    Iterable,
    Callable,
    Mapping,
    TypeVar,
)
import dataclasses
import re

from doc_scraper import doc_struct
from doc_scraper import help_docs
from doc_scraper import doc_transform


def match_for(
    *tags: str, pattern: re.Pattern[str] = re.compile('.+')
) -> Mapping[str, re.Pattern[str]]:
    """Create tag matchers from sequence."""
    return {item: pattern for item in tags}


class ElementFilterConverter(
        doc_struct.ConverterBase[Sequence[doc_struct.Element]]):
    """Convert an element tree into a squence of elements, filtered."""

    def __init__(self, filter_func: Callable[[doc_struct.Element],
                                             bool]) -> None:
        """Create an instance.

        Args:
            filter_func: Callable applied to each element. If returning
                True, the element is added to the result.
        """
        super().__init__()
        self._filter_func = filter_func

    def _flatten_list(self, *nested_elements: Any) -> Sequence[Any]:
        """Flatten a list that is nested at any depth."""
        result: List[Any] = []
        pending: List[Any] = list(nested_elements)
        while pending:
            item = pending.pop()
            if isinstance(item, (list, tuple, set)):
                pending.extend(cast(Iterable[Any], item))
            else:
                result.append(item)
        return result

    def _filter(self, element: doc_struct.Element,
                *descendents: Any) -> Sequence[doc_struct.Element]:
        """Filter matching elements.

        Args:
            element: The element currently inspected.
            descendents: The filtered out descendents of the current
                element, potentially as nested list.
        """
        result: List[Any] = []
        if self._filter_func(element):
            result.append(element)
        result.extend(self._flatten_list(*descendents))
        return result

    def _convert_element(
            self, element: doc_struct.Element) -> Sequence[doc_struct.Element]:
        """Check for elements without descendents."""
        return self._filter(element)

    def _convert_bullet_item_with_descendents(
        self, element: doc_struct.BulletItem,
        elements: Sequence[Sequence[doc_struct.Element]],
        nested: Sequence[Sequence[doc_struct.Element]]
    ) -> Sequence[doc_struct.Element]:
        return self._filter(element, *elements, *nested)

    def _convert_bullet_list_with_descendents(
        self, element: doc_struct.BulletList,
        items: Sequence[Sequence[doc_struct.Element]]
    ) -> Sequence[doc_struct.Element]:
        return self._filter(element, *items)

    def _convert_doc_content_with_descentdents(
        self, element: doc_struct.DocContent,
        elements: Sequence[Sequence[doc_struct.Element]]
    ) -> Sequence[doc_struct.Element]:
        return self._filter(element, *elements, *elements)

    def _convert_document_with_descendents(
            self, element: doc_struct.Document,
            shared_data: Sequence[doc_struct.Element],
            content: Sequence[doc_struct.Element]
    ) -> Sequence[doc_struct.Element]:
        return self._filter(element, *shared_data, *content)

    def _convert_notes_appendix_with_descendents(
        self, element: doc_struct.NotesAppendix,
        elements: Sequence[Sequence[doc_struct.Element]]
    ) -> Sequence[doc_struct.Element]:
        return self._filter(element, *elements)

    def _convert_paragraph_with_descendents(
        self, element: doc_struct.Paragraph,
        elements: Sequence[Sequence[doc_struct.Element]]
    ) -> Sequence[doc_struct.Element]:
        return self._filter(element, *elements)

    def _convert_section_with_descendents(
        self, element: doc_struct.Section,
        heading: Optional[Sequence[doc_struct.Element]],
        content: Sequence[Sequence[doc_struct.Element]]
    ) -> Sequence[doc_struct.Element]:
        if heading is None:
            heading = []
        return self._filter(element, *heading, *content)

    def _convert_table_with_descendents(
        self, element: doc_struct.Table,
        elements: Sequence[Sequence[Sequence[doc_struct.Element]]]
    ) -> Sequence[doc_struct.Element]:
        return self._filter(element, *elements)

    def _convert_text_line_with_descendents(
        self, element: doc_struct.TextLine,
        elements: Sequence[Sequence[doc_struct.Element]]
    ) -> Sequence[doc_struct.Element]:
        return self._filter(element, *elements)


# Type used to match tags.
TagMatcherType = Mapping[str, re.Pattern[str]]

# Example config for TagMatchingConifg, to be used for help_docs.
TAG_MATCH_CONFIG_EXAMPLE = """
  element_types:
  - TextRun
  - BulletItem
  required_tags_sets:
  - {"A": ".*", "C":"123"}
  - {"D": ".*"}
  rejected_tags: {'R': '.*'}
  required_style_sets:
  - backgorund-color: "#ff0000"   # Match if background is red...
    color: white                  # AND the text is white (both must match)
  - font-weight: bold             # OR if text is bold text
  exclude:
  - color: .*green.*              # Don't match if the text is any green.
  - color: blue                   # Also don't match if the text is blue.
"""

REQUIRED_STYLE_SET_EXAMPLE = """
  - {font-size: 20pt, font-weight: bold}
  - color: red
"""

# All types that contain a text attribute.
TEXT_ELEMENT_TYPES = (
    doc_struct.Chip,
    doc_struct.TextRun,
    doc_struct.Link,
    doc_struct.Reference,
    doc_struct.ReferenceTarget,
)
# All element types that have a url attribute.
URL_ELEMENT_TYPES = (
    doc_struct.Link,
    doc_struct.Reference,
)


@dataclasses.dataclass(kw_only=True)
class ElementExpressionMatchConfig():
    """Match expressions (Python format) of elements."""

    expr: str = dataclasses.field(
        metadata={
            'help_docs':
                'The expression (format interpolated) to match',
            'help_samples': [
                ('Element text, followed by url from element(e)',
                 '{e.text}--{e.url}'),
                ('Grab value of tag "tag1"', '{e.tags[tag1]}'),
            ]
        })

    regex_match: re.Pattern[str] = dataclasses.field(metadata={
        'help_docs': 'The regex against which to match the expression',
    })

    ignore_key_errors: bool = dataclasses.field(
        default=False,
        metadata={
            'help_docs':
                'If set to true, KeyErrors are ignored and considered ' +
                'non-matching',
        })

    def is_matching(self, element: doc_struct.Element) -> bool:
        """Check if an element matches."""
        try:
            expanded = self.expr.format(e=element)
        except KeyError as exc:
            if self.ignore_key_errors:
                return False
            raise exc

        if not self.regex_match.match(expanded):
            return False
        return True


@dataclasses.dataclass(kw_only=True)
class TagMatchConfig():
    """Configuration for matching by tag."""

    def __post_init__(self):
        """Add the text converter in post init."""
        self._text_converter = doc_struct.RawTextConverter()

    element_types: Sequence[Type[doc_struct.Element]] = dataclasses.field(
        default_factory=lambda: [doc_struct.Element],
        metadata={
            'help_docs':
                'The element types to be tagged',
            'help_samples': [
                ('Any paragraph element, e.g. TextRun',
                 help_docs.RawSample('\n- ParagraphElement')),
                ('Specifically only Chips and BulletItems',
                 help_docs.RawSample('["Chips", "BulletItem"]')),
            ]
        })

    required_tag_sets: Sequence[TagMatcherType] = dataclasses.field(
        default_factory=list,
        metadata={
            'help_text':
                'List of list of tags, all required for the ' +
                'match to happen.',
            'help_samples': [
                help_docs.RawSample(
                    '\n- ["A":".*","B":""]  # matches if A and B present.\n' +
                    '- ["C":".*"]  # Or C alone.')
            ],
        })
    rejected_tags: TagMatcherType = dataclasses.field(
        default_factory=dict,
        metadata={
            'help_text':
                'Tags that stop any match if present.',
            'help_samples': [('No Elements tagged with X will be matched.',
                              help_docs.RawSample('["X"]'))]
        })

    required_style_sets: Sequence[Mapping[
        str, re.Pattern[str]]] = dataclasses.field(
            default_factory=list,
            metadata={
                'help_text':
                    'Styles required for the tag to match. All need to match.',
                'help_samples': [
                    help_docs.RawSample(REQUIRED_STYLE_SET_EXAMPLE)
                ]
            })

    rejected_styles: Mapping[str, re.Pattern[str]] = dataclasses.field(
        default_factory=dict,
        metadata={
            'help_text':
                'Styles that prevent matching. Only one needs to match.',
            'help_samples': [help_docs.RawSample('\n  font-weight: 400')]
        })

    skip_style_quotes: bool = dataclasses.field(
        default=True,
        metadata={
            'help_text': 'If set to True, quotes in style values are removed.'
        })

    aggregated_text_regex: Optional[re.Pattern[str]] = dataclasses.field(
        default=None,
        metadata={
            'help_text':
                'The Python regex to match with element\'s ' +
                'text representation.',
            'help_sampes': [r'some text\s+in doc']
        })

    element_expressions: Sequence[
        ElementExpressionMatchConfig] = dataclasses.field(
            default_factory=list,
            metadata={
                'help_text': 'List of expressions to interpolate and match.',
            })

    def _is_text_matching(self, element: doc_struct.Element) -> bool:
        """Check if an element matches."""
        if self.element_expressions:
            for item in self.element_expressions:
                if not item.is_matching(element):
                    return False

        if self.aggregated_text_regex:
            if not self.aggregated_text_regex.match(
                    self._text_converter.convert(element)):
                return False

        return True

    def _match_all(self, tags: Mapping[str, str],
                   match: TagMatcherType) -> bool:
        """Return true if all of the tags match."""
        for k, v in match.items():
            if k not in tags:
                return False
            if not v.match(tags[k]):
                return False
        return True

    def _match_any(self, tags: Mapping[str, str],
                   match: TagMatcherType) -> bool:
        """Return true if any of the tags match."""
        for k, v in match.items():
            if k not in tags:
                continue
            if v.match(tags[k]):
                return True
        return False

    def _cleanup_style(self, value: str) -> str:
        """Clean up the style value to make it comparable."""
        if self.skip_style_quotes:
            return value.strip()
        return value.strip("'\" ")

    def _is_required_rejected_matching(
        self,
        tags: Mapping[str, str],
        required_sets: Sequence[TagMatcherType],
        rejected_matchers: TagMatcherType,
    ) -> bool:
        """Match styles or tags based on required/rejected semantics."""
        if self._match_any(tags, rejected_matchers):
            return False

        if not required_sets:
            return True

        for style_matcher in required_sets:
            if self._match_all(tags, style_matcher):
                return True

        return False

    def is_matching(self, element: doc_struct.Element) -> bool:
        """Check if an element matches."""
        if not isinstance(element, tuple(self.element_types)):
            return False

        if not self._is_required_rejected_matching(
                element.tags, self.required_tag_sets, self.rejected_tags):
            return False

        style = {k: self._cleanup_style(v) for k, v in element.style.items()}
        if not self._is_required_rejected_matching(
                style, self.required_style_sets, self.rejected_styles):
            return False

        if not self._is_text_matching(element):
            return False

        return True

    def match_descendents(
            self,
            *elements: doc_struct.Element) -> Sequence[doc_struct.Element]:
        """Search through the element and descendents and match this config."""
        filter_converter = ElementFilterConverter(self.is_matching)
        result: List[doc_struct.Element] = []
        for element in elements:
            result.extend(filter_converter.convert(element))

        return result


# Type parameter to match any element type in update_tags.
_T = TypeVar('_T', bound=doc_struct.Element)

# Sample YAML for Tag update config.
DOC_HELP_TAG_UPDATE_CONFIG_SAMPLE = """
  add: { "tagX": "valX", "tagY": "valY" }
  remove: [ "*" ]
"""


@dataclasses.dataclass(kw_only=True)
class TagUpdateConfig():
    """Configuration for updating tags."""

    add: Mapping[str, str] = dataclasses.field(
        default_factory=dict,
        metadata={
            'help_text':
                'A list of tags to add.',
            'help_sampes': [
                help_docs.RawSample('{"tag1": "val1", "tag2": "val2"}')
            ]
        })

    remove: Sequence[str] = dataclasses.field(
        default_factory=list,
        metadata={
            'help_text':
                'A list of tags to remove. Use "*" to clear all.',
            'help_sampes': [
                help_docs.RawSample('["tag3", "tag4"]'),
                ('Clear tags before adding', help_docs.RawSample('["*"]'))
            ]
        })

    def update_tags(self, element: _T) -> _T:
        """Update the passed element with the speficied tags."""
        if '*' in self.remove:
            new_tags: Dict[str, str] = {}
        else:
            new_tags = {
                k: v for k, v in element.tags.items() if k not in self.remove
            }

        new_tags.update(self.add)
        return dataclasses.replace(element, tags=new_tags)


@dataclasses.dataclass(kw_only=True)
class TaggingConfig():
    """Configuration for matching and tagging elements."""

    match_element: TagMatchConfig = dataclasses.field(
        metadata={
            'help_text':
                'Criteria to match elements for tagging.',
            'help_samples': [('',
                              help_docs.RawSample(TAG_MATCH_CONFIG_EXAMPLE))]
        })

    tags: TagUpdateConfig = dataclasses.field(
        metadata={
            'help_text':
                'Updates for tags',
            'help_samples':
                [help_docs.RawSample(DOC_HELP_TAG_UPDATE_CONFIG_SAMPLE)]
        })


class TaggingTransform(doc_transform.Transformation):
    """Tag objects based on matched criteria."""

    def __init__(
            self,
            config: TaggingConfig,
            context: Optional[doc_transform.TransformationContext] = None):
        """Construct an instance.

        Args:
            context: Optional, customized context.
            config: Criteria to match elements.
        """
        super().__init__(context)
        self.config = config

    def _transform_element_base(
            self, element: doc_struct.Element) -> doc_struct.Element:
        """Transform (tag) all elements."""
        if self.config.match_element.is_matching(element):
            element = self.config.tags.update_tags(element)

        return super()._transform_element_base(element)

    @classmethod
    def from_config(cls, config: TaggingConfig) -> 'TaggingTransform':
        """Create an instance from config class."""
        return TaggingTransform(config=config)
