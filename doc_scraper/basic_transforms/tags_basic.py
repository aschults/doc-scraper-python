"""Common classes for working with tags."""

from typing import (
    Optional,
    Sequence,
    Type,
    Any,
    List,
    cast,
    Iterable,
    Callable,
    Mapping,
)
import dataclasses
import re

from doc_scraper import doc_struct
from doc_scraper import help_docs
from doc_scraper.doc_struct import Element


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

    def _convert_element(self, element: Element) -> Sequence[Element]:
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


TagMatcherType = Mapping[str, re.Pattern[str]]

TAG_MATCH_CONFIG_EXAMPLE = """
  element_types:
  - TextRun
  - BulletItem
  required_tags_sets:
  - {"A": ".*", "C":"123"}
  - {"D": ".*"}
  rejected_tags: {'R': '.*'}
"""


@dataclasses.dataclass(kw_only=True)
class TagMatchConfig():
    """Configuration for matching by tag."""

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

    def _match_all(self, tags: Mapping[str, str],
                   match: TagMatcherType) -> bool:
        for k, v in match.items():
            if k not in tags:
                return False
            if not v.match(tags[k]):
                return False
        return True

    def _match_any(self, tags: Mapping[str, str],
                   match: TagMatcherType) -> bool:
        for k, v in match.items():
            if k not in tags:
                continue
            if v.match(tags[k]):
                return True
        return False

    def is_matching(self, element: doc_struct.Element) -> bool:
        """Check if an element matches."""
        if not isinstance(element, tuple(self.element_types)):
            return False

        if self._match_any(element.tags, self.rejected_tags):
            return False

        if not self.required_tag_sets:
            return True

        for accepting_tags in self.required_tag_sets:
            if self._match_all(element.tags, accepting_tags):
                return True
        return False

    def match_descendents(
            self,
            *elements: doc_struct.Element) -> Sequence[doc_struct.Element]:
        """Search through the element and descendents and match this config."""
        filter_converter = ElementFilterConverter(self.is_matching)
        result: List[doc_struct.Element] = []
        for element in elements:
            result.extend(filter_converter.convert(element))

        return result
