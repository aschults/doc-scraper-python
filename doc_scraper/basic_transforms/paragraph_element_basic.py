"""Some transformations for paragraph elements and text runs."""

from typing import (Optional, List)
import dataclasses
import re

from doc_scraper import doc_struct
from doc_scraper import doc_transform
from doc_scraper import help_docs
from doc_scraper.doc_transform import TransformationContext
from doc_scraper.basic_transforms import tags_basic


@dataclasses.dataclass(kw_only=True)
class RegexReplaceRule():
    """Single regex with substitution."""

    regex: re.Pattern[str] = dataclasses.field(
        metadata={
            'help_text': 'The Python regex to match.',
            'help_sampes': [('All spaces (including newline)', r'\s+')]
        })

    substitute: str = dataclasses.field(
        metadata={
            'help_text': 'The replacement text.',
            'help_sampes': [('Replace with one space', ' ')]
        })

    operation: str = dataclasses.field(
        default='',
        metadata={
            'help_text': 'Additional operation to apply.',
            'help_sampes': [('Make all lower case', 'lower')]
        })


REGEX_CONFIG_EXAMPLE = """
- regex: "\\s+"
  replacement: "_"
  # Replace consequtive spaces with single underscore.
"""


@dataclasses.dataclass(kw_only=True)
class RegexReplacerConfig():
    """Configuration for modifying text by regular expression."""

    match: tags_basic.TagMatchConfig = dataclasses.field(
        default_factory=tags_basic.TagMatchConfig,
        metadata={
            'help_text':
                'Constraints required for the substitution to happen.',
            'help_sampes': [
                help_docs.RawSample('xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx')
            ]
        })
    substitutions: List[RegexReplaceRule] = dataclasses.field(
        metadata={
            'help_text': 'List of regex-based replacements.',
            'help_sampes': [help_docs.RawSample(REGEX_CONFIG_EXAMPLE)]
        })

    def transform_text(self, text: str) -> str:
        for substitution in self.substitutions:
            if not substitution.operation:
                text = substitution.regex.sub(substitution.substitute, text)
            elif substitution.operation == 'lower':
                text = substitution.regex.sub(
                    lambda m: m.expand(substitution.substitute).lower(), text)
            elif substitution.operation == 'upper':
                text = substitution.regex.sub(
                    lambda m: m.expand(substitution.substitute).upper(), text)
            else:
                raise ValueError(
                    f'Unknown substitution operation {substitution.operation}')
        return text


class TextTransformBase(doc_transform.Transformation):
    """Transform texts based on list of functions."""

    def __init__(self,
                 context: Optional[TransformationContext] = None) -> None:
        super().__init__(context)

    def _process_text_string(self, text: Optional[str]) -> str:
        raise NotImplementedError('Needs override.')

    def _is_matching(self, element: doc_struct.Element) -> bool:
        raise NotImplementedError('Needs override.')

    def _transform_chip(self, chip: doc_struct.Chip) -> doc_struct.Chip:
        chip = super()._transform_chip(chip)
        if self._is_matching(chip):
            chip = dataclasses.replace(chip,
                                       text=self._process_text_string(
                                           chip.text))
        return chip

    def _transform_text_run(
            self, text_run: doc_struct.TextRun) -> doc_struct.TextRun:
        text_run = super()._transform_text_run(text_run)
        if self._is_matching(text_run):
            text_run = dataclasses.replace(text_run,
                                           text=self._process_text_string(
                                               text_run.text))
        return text_run

    def _transform_link(self, link: doc_struct.Link) -> doc_struct.Link:
        link = super()._transform_link(link)
        if self._is_matching(link):
            link = dataclasses.replace(link,
                                       text=self._process_text_string(
                                           link.text))
        return link

    def _transform_reference(
            self, ref: doc_struct.Reference) -> doc_struct.Reference:
        ref = super()._transform_reference(ref)
        if self._is_matching(ref):
            ref = dataclasses.replace(ref,
                                      text=self._process_text_string(ref.text))
        return ref

    def _transform_reference_target(
            self,
            ref: doc_struct.ReferenceTarget) -> doc_struct.ReferenceTarget:
        ref = super()._transform_reference_target(ref)
        if self._is_matching(ref):
            ref = dataclasses.replace(ref,
                                      text=self._process_text_string(ref.text))
        return ref


class RegexReplacerTransform(TextTransformBase):

    def __init__(self,
                 config: RegexReplacerConfig,
                 context: Optional[TransformationContext] = None) -> None:
        super().__init__(context)
        self.config = config

    def _process_text_string(self, text: Optional[str]) -> str:
        if text is None:
            return ''
        return self.config.transform_text(text)

    def _is_matching(self, element: doc_struct.Element) -> bool:
        return self.config.match.is_matching(element)