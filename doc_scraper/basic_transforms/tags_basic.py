"""Common classes for working with tags."""

from typing import (
    Sequence,
    Type,
    Set,
    Collection,
    cast,
)
import dataclasses

from doc_scraper import doc_struct
from doc_scraper import help_docs


@dataclasses.dataclass(kw_only=True)
class TagMatchConfig():
    """Configuration for matching by tag.

    Tags are stored in field `attrib`, by default under key "tags".
    """

    tag_key: str = dataclasses.field(
        default='tags',
        metadata={
            'help_docs':
                'The key in `attrs` under which the set of tags is stored.',
            'help_samples': [('Default', 'tags')]
        })

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

    required_tag_sets: Sequence[Sequence[str]] = dataclasses.field(
        default_factory=list,
        metadata={
            'help_text':
                'List of list of tags, all required for the ' +
                'match to happen.',
            'help_samples': [
                help_docs.RawSample(
                    '\n- ["A","B"]  # matches if A and B present.\n' +
                    '- ["C"]  # Or C alone.')
            ],
        })
    rejected_tags: Sequence[str] = dataclasses.field(
        default_factory=list,
        metadata={
            'help_text':
                'Tags that stop any match if present.',
            'help_samples': [('No Elements tagged with X will be matched.',
                              help_docs.RawSample('["X"]'))]
        })

    def _get_tags(self, element: doc_struct.Element) -> Set[str]:
        """Extract the tags (as set) from a document element."""
        tags = element.attrs.get(self.tag_key, [])
        if not isinstance(tags, Collection):
            raise ValueError(
                f'Attribute with key {self.tag_key} is no collection.')
        return set(cast(Collection[str], tags))

    def is_matching(self, element: doc_struct.Element) -> bool:
        """Check if an element matches."""
        if not isinstance(element, tuple(self.element_types)):
            return False

        tags = self._get_tags(element)

        rejected_set = set(self.rejected_tags)
        if tags & rejected_set:
            return False

        if not self.required_tag_sets:
            return True

        for accepting_tags in self.required_tag_sets:
            accepting_set = set(accepting_tags)
            if accepting_set.issubset(tags):
                return True
        return False