"""Some basic transformations for paragraphs, including bullet lists."""
from typing import (Optional, List, Sequence, Callable, Type)
import dataclasses
import re

from doc_scraper import doc_struct
from doc_scraper import doc_transform
from doc_scraper import help_docs
from doc_scraper.basic_transforms import tags_basic
from doc_scraper.basic_transforms import tags_relation


def _break_single_text_run(
        text_run: doc_struct.TextRun) -> Sequence[doc_struct.TextRun]:
    """Break a text run down by preserving line, preserving newline."""
    return [
        dataclasses.replace(text_run, text=item)
        for item in re.split(r'(\n)', text_run.text)
        if item
    ]


def _break_text(
    elements: Sequence[doc_struct.ParagraphElement]
) -> List[doc_struct.ParagraphElement]:
    r"""Break the instance apart around '\n' text items.

    Inserts `doc_struct.TextLine` items to structure a
    paragraph into lines.

    Makes a copy with same attributes for each line.
    """
    new_elements: List[doc_struct.ParagraphElement] = []
    for element in elements:
        if isinstance(element, doc_struct.TextLine):
            new_elements.extend(element.elements)
        elif isinstance(element, doc_struct.TextRun):
            new_elements.extend(_break_single_text_run(element))
        else:
            new_elements.append(element)

    result: List[List[doc_struct.ParagraphElement]] = [[]]

    for element in new_elements:
        result[-1].append(element)
        if isinstance(element, doc_struct.TextRun) and element.text == '\n':
            result.append([])

    return [
        doc_struct.TextLine(elements=line_elements)
        for line_elements in result
        if line_elements
    ]


def style_try_merge(
    first: doc_struct.ParagraphElement, second: doc_struct.ParagraphElement
) -> Optional[doc_struct.ParagraphElement]:
    """Check if two elements are suitable for merge and perform merge if so."""
    if not isinstance(first, doc_struct.TextRun):
        return None
    if not isinstance(second, doc_struct.TextRun):
        return None
    if first.style != second.style:
        return None
    return dataclasses.replace(first, text=first.text + second.text)


class ParagraphLineBreakTransformation(doc_transform.Transformation):
    r"""Transform a document, rearranging paragraphs by line.

    Introduces `doc_struct.TextLine` into the paragraph's elements
    to group elements belonging to the same line within the paragraph.

    E.g.:
    `Paragraph(elements=TextRun(text='line1\nline2')`)
    is transformed intos
    ```
    Paragraph(elements=[
        TextLine(elements=[
            TextRun(text='line1'),
            TextRun(text='\n')
        ]),
        TextLine(elements=[TextRun(text='line2')]
    ])
    ```
    """

    def _transform_paragraph_elements(
        self, element_list: Sequence[doc_struct.ParagraphElement]
    ) -> Sequence[doc_struct.ParagraphElement]:
        """Apply the transform to the list of elements in a paragraph."""
        element_list = _break_text(element_list)
        return super()._transform_paragraph_elements(element_list)

    def __init__(
            self,
            context: Optional[doc_transform.TransformationContext] = None
    ) -> None:
        """Construct an instance."""
        super().__init__(context)


TryMergeFunctionType = Callable[
    [doc_struct.ParagraphElement, doc_struct.ParagraphElement],
    Optional[doc_struct.ParagraphElement]]


class TextMergeParagraphTransformation(doc_transform.Transformation):
    """Merge subsequent paragraph elements if they match.

    E.g.
    `TextRun(text='part1 '), TextRun(text='part2')`
    if both elements match, may be merged into
    `TextRun(text='part1 part2')`
    """

    def __init__(
            self,
            context: Optional[doc_transform.TransformationContext] = None,
            try_merge_func: TryMergeFunctionType = style_try_merge) -> None:
        """Construct an instance.

        Args:
            context: Optional transformation context
            try_merge_func: Callable/function that takes two paragraph
                elements and either merges them (returning the merged one) or
                None if they are not mergeable.
        """
        super().__init__(context)
        self.try_merge_func = try_merge_func

    def _transform_paragraph_elements(
        self, element_list: Sequence[doc_struct.ParagraphElement]
    ) -> Sequence[doc_struct.ParagraphElement]:
        """Build list of paragraph elements, merged where matching."""
        if not element_list:
            return []

        result: List[doc_struct.ParagraphElement] = []
        last_element = element_list[0]
        for element in element_list[1:]:
            merged_element = self.try_merge_func(last_element, element)
            if merged_element is None:
                result.append(last_element)
                last_element = element
            else:
                last_element = merged_element

        result.append(last_element)
        return super()._transform_paragraph_elements(result)


DEFAULT_MERGE_ELEMENTS: Sequence[Type[doc_struct.Element]] = [
    doc_struct.TextRun
]


@dataclasses.dataclass(kw_only=True)
class TagMergeConfig():
    """Configuration for merging paragraph elements by tag."""

    merge_as_text_run: bool = dataclasses.field(
        default=False,
        metadata={
            'help_docs':
                'If the element resulting of a merge always is a text run.',
            'help_samples': [('Default', False)]
        })

    match_element: tags_basic.TagMatchConfig = dataclasses.field(
        default_factory=tags_basic.TagMatchConfig,
        metadata={
            'help_docs':
                'Criteria to allow merge of subsequent tags.',
            'help_samples': [
                help_docs.ClassBasedSample(tags_basic.TagMatchConfig),
            ]
        })


class TagMergePolicy():
    """Policy to use when merging paragraph elements by tag.

    Instances are callable and thus can directly be passed as
    try_merge_func in TextMergeParagraphTransformation
    """

    def __init__(self, config: TagMergeConfig) -> None:
        """Create an instance."""
        self.config = config
        self._text_converter = doc_struct.RawTextConverter()

    def _is_matching(self, first: doc_struct.ParagraphElement,
                     second: doc_struct.ParagraphElement) -> bool:
        """Check if two paragraph elements match."""
        if isinstance(first,
                      (doc_struct.Chip, doc_struct.Link)) and isinstance(
                          second, (doc_struct.Chip, doc_struct.Link)):
            # Sort out non-matching links.
            if first.url != second.url:
                return False

        if not self.config.match_element.is_matching(first):
            return False
        if not self.config.match_element.is_matching(second):
            return False
        return True

    def _create_merged(
            self, first: doc_struct.ParagraphElement,
            second: doc_struct.ParagraphElement
    ) -> doc_struct.ParagraphElement:
        """Merge two elements, assuming they match."""
        first_text = self._text_converter.convert(first) or ''
        second_text = self._text_converter.convert(second) or ''
        merged_text = first_text + second_text

        if self.config.merge_as_text_run:
            return doc_struct.TextRun(attrs=first.attrs,
                                      style=first.style,
                                      tags=first.tags,
                                      text=merged_text)
        elif isinstance(first, doc_struct.TextLine):
            if isinstance(second, doc_struct.TextLine):
                new_elements = list(first.elements) + list(second.elements)
            else:
                new_elements = list(first.elements) + [second]
            return dataclasses.replace(first, elements=new_elements)
        elif isinstance(first,
                        (doc_struct.Chip, doc_struct.Link)) and isinstance(
                            second, (doc_struct.Chip, doc_struct.Link)):
            return dataclasses.replace(first, text=first.text + second.text)
        else:
            return doc_struct.TextRun(attrs=first.attrs,
                                      style=first.style,
                                      text=merged_text)

    def __call__(
        self, first: doc_struct.ParagraphElement,
        second: doc_struct.ParagraphElement
    ) -> Optional[doc_struct.ParagraphElement]:
        """Perform the try and merge, making the object callable."""
        if not self._is_matching(first, second):
            return None

        return self._create_merged(first, second)


def build_tag_merge_transform(
        config: TagMergeConfig) -> doc_transform.TransformationFunction:
    """Build a Tag-based merge transformation based on config."""
    return TextMergeParagraphTransformation(
        try_merge_func=TagMergePolicy(config))


TEXT_CONTAINER_TYPES = (doc_struct.TextRun, doc_struct.Link,
                        doc_struct.Reference, doc_struct.Chip)


@dataclasses.dataclass(kw_only=True)
class TextSplitConfig(tags_relation.RelationalMatchingConfig):
    """Split a text-based element by regex groups."""

    text_regex: tags_basic.StringMatcher = dataclasses.field(
        metadata={
            'help_docs':
                'Regex to match iteratively. Each group produces ' +
                'a split element',
            'help_samples': [('An element for each Unix path segment',
                              '([^/])(?:/|$)')]
        })

    allow_no_matches: bool = dataclasses.field(
        default=False,
        metadata={
            'help_docs':
                'If set to true, elements that don\'t match the regex are ' +
                'dropped.',
            'help_samples': [('Default', False)]
        })

    element_tags: Sequence[tags_basic.TagUpdateConfig] = dataclasses.field(
        default_factory=list,
        metadata={
            'help_docs':
                'Add tags to the split elements, for each regex group.',
            'help_samples': [('Tag first two split elements', [{
                'add': {
                    'first': 'x'
                }
            }, {
                'add': {
                    'second': 'x'
                }
            }])]
        })

    all_tags: Optional[tags_basic.TagUpdateConfig] = dataclasses.field(
        default=None,
        metadata={
            'help_docs':
                'Add tags to all split elements.',
            'help_samples': [('Tag every split elements', {
                'add': {
                    'split_element': 'x'
                }
            })]
        })

    def split_element(
        self, element: doc_struct.ParagraphElement,
        path: Sequence[doc_struct.Element]
    ) -> Optional[Sequence[doc_struct.ParagraphElement]]:
        """Split the element or return None if not matching."""
        if not self.is_matching(element, path):
            return None

        if not isinstance(element, TEXT_CONTAINER_TYPES):
            return None

        matches = self.text_regex.findall(element.text)
        if not self.allow_no_matches:
            if len(matches) == 0:
                return None
        matches = [item for match in matches for item in match]

        result: Sequence[doc_struct.ParagraphElement] = []
        for index, group in enumerate(matches):
            new_element = dataclasses.replace(element, text=group)
            if self.all_tags:
                new_element = self.all_tags.update_tags(new_element)
            if index < len(self.element_tags):
                tag_updater = self.element_tags[index]
                new_element = tag_updater.update_tags(new_element)
            result.append(new_element)

        return result


class TextSplitTransformation(doc_transform.Transformation):
    r"""Split a paragraph element with text into multiple copies.

    E.g.
    `TextRun(text='Prefix: content')` split by regex `^(.*)\s*:\s*(.*)$`
    will result in `TextRun(text='Prefix'), TextRun(text='content')`
    """

    def __init__(
        self,
        config: TextSplitConfig,
        context: Optional[doc_transform.TransformationContext] = None,
    ) -> None:
        """Construct an instance."""
        super().__init__(context)
        self.config = config

    def _process_paragraph_elements(
        self, element_list: Sequence[doc_struct.ParagraphElement]
    ) -> Sequence[doc_struct.ParagraphElement]:
        """Split a paragraph element with text apart by regex groups."""
        if not element_list:
            return []

        result: List[doc_struct.ParagraphElement] = []
        for element in element_list:
            new_elements = self.config.split_element(element,
                                                     self.context.path_objects)
            if new_elements is None:
                result.append(element)
            else:
                result.extend(new_elements)
        return result

    def _transform_paragraph_elements(
        self, element_list: Sequence[doc_struct.ParagraphElement]
    ) -> Sequence[doc_struct.ParagraphElement]:
        """Build list of paragraph elements, merged where matching."""
        return super()._transform_paragraph_elements(
            self._process_paragraph_elements(element_list))

    def _transform_text_line_elements(
        self, element_list: Sequence[doc_struct.ParagraphElement]
    ) -> Sequence[doc_struct.ParagraphElement]:
        return super()._transform_text_line_elements(
            self._process_paragraph_elements(element_list))
