"""Visitor implementation for document transformation."""
from typing import Optional, List, Dict, Set, Iterable
from typing import Type
import dataclasses

from doc_scraper import doc_struct
from doc_scraper import help_docs
from doc_scraper import doc_transform


@dataclasses.dataclass(kw_only=True)
class MatchRule():
    """Base class for style matching rules."""

    # pylint: disable=unused-argument
    def get_tags(self, element: doc_struct.Element) -> Set[str]:
        """Determine the tags of a document element.

        Return:
            Set containing the tags to be added.
        """
        return set()


@dataclasses.dataclass(kw_only=True)
class SimpleStyleMatchRule(MatchRule):
    """Implementation of MatchRule that matches entire style value strings."""

    tag: str = dataclasses.field(
        default='tags',
        metadata={'help_text': 'Attribute in `attrs` to write the tags into.'})

    element_types: Iterable[Type[doc_struct.Element]] = dataclasses.field(
        default_factory=lambda: [doc_struct.Element],
        metadata={
            'help_text':
                'Element types (ncluding subclasses) in scope for tagging',
            'help_samples': [('Default', help_docs.RawSample('["Element"]'))]
        })

    include: Dict[str, str] = dataclasses.field(
        default_factory=dict,
        metadata={
            'help_text':
                'Styles required for the tag to match. All need to match.',
            'help_samples': [
                help_docs.RawSample('\n  font-size: 20pt\n  color: red')
            ]
        })

    exclude: Dict[str, str] = dataclasses.field(
        default_factory=dict,
        metadata={
            'help_text':
                'Styles that prevent matching. Only one needs to match.',
            'help_samples': [help_docs.RawSample('\n  font-weight: 400')]
        })

    skip_quotes: bool = dataclasses.field(
        default=True,
        metadata={
            'help_text': 'If set to True, quotes in style values are removed.'
        })

    def _cleanup_style(self, value: Optional[str]) -> Optional[str]:
        """Clean up the style value to make it comparable."""
        if value is None:
            return None
        if self.skip_quotes:
            return value.strip()
        return value.strip("'\" ")

    def get_tags(self, element: doc_struct.Element) -> Set[str]:
        """Check if the rule matches.

        Args:
            element: Element to match tags for.

        Returns:
            The tag if it matched.
        """
        if not isinstance(element, tuple(self.element_types)):
            return set()

        style = element.style

        for style_key, style_value in self.exclude.items():
            style_v = self._cleanup_style(style.get(style_key, None))
            if style_value == style_v:
                return set()

        for style_key, style_value in self.include.items():
            style_v = self._cleanup_style(style.get(style_key, None))
            if style_value != style_v:
                return set()

        return set([self.tag])


@dataclasses.dataclass(kw_only=True)
class StyleMatcher:
    """Class to match multiple rules, returning the all matching tags."""

    rules: List[MatchRule] = dataclasses.field(
        default_factory=list,
        metadata={
            'help_text': 'List of rules. Tags of all matching rules are added.'
        })

    def add(self, rule: MatchRule) -> None:
        """Add a rule to the matcher."""
        self.rules.append(rule)

    def get_tags(self, element: doc_struct.Element) -> Set[str]:
        """Match rules in supplied order, returning the first match."""
        result: Set[str] = set()
        for rule in self.rules:
            result.update(rule.get_tags(element))
        return result


# Sample text for help_docs. Note: The above metadata is only for commenting,
# and currently not used when generating the help docs.
_MATCHER_RAW_SAMPLE = help_docs.RawSample('''
# List of rules. Each is matched independently
rules:
- tag: 'highlighted'  # The name of the tag to add
  # List of styles. All must match for the tag to get applied.
  include:
  - backgorund-color: "#ff0000"   # Match if background is red...
  - font-weight: bold             # And only match bold text (both must match)
  # List of styles that will prevent matching. Only one needs to match.
  exclude:
  - color: green                  # Don't match if the text is green.
  - color: blue                   # Also don't match if the text is blue.
''')


@dataclasses.dataclass(kw_only=True)
class TaggingConfig():
    """Configuration for matching and tagging elements."""

    tag_key: str = dataclasses.field(
        default='tags',
        metadata={
            'help_text':
                'The key inside the `attrs` attribute to use for tagging.',
            'help_sampes': [('Default', 'tags')]
        })

    matcher: StyleMatcher = dataclasses.field(
        metadata={
            'help_text': 'Rules to perform the matching and tagging.',
            'help_samples': [('', _MATCHER_RAW_SAMPLE)]
        })


class TaggingTransform(doc_transform.Transformation):
    """Tag objects based on matched criteria."""

    def __init__(self,
                 context: Optional[doc_transform.TransformationContext] = None,
                 tag_key: str = 'tags',
                 matcher: Optional[StyleMatcher] = None):
        """Construct an instance.

        Args:
            context: Optional, customized context.
            tag_key: The key to add to the attribs dict. Default: tags
            matcher: Construct using pre-existing matcher.
        """
        super().__init__(context)
        self.matcher = matcher or StyleMatcher()
        self.tag_key = tag_key

    def add_rule(self, rule: MatchRule) -> None:
        """Add a rule to the matcher."""
        self.matcher.add(rule)

    def _transform_element_base(
            self, element: doc_struct.Element) -> doc_struct.Element:
        """Transform (tag) all elements."""
        tags = self.matcher.get_tags(element)
        new_attrs = dict(element.attrs)
        if tags:
            new_attrs[self.tag_key] = tags
        else:
            if self.tag_key in new_attrs:
                del new_attrs[self.tag_key]

        element = dataclasses.replace(element, attrs=new_attrs)
        return super()._transform_element_base(element)

    @classmethod
    def from_config(cls, config: TaggingConfig) -> 'TaggingTransform':
        """Create an instance from config class."""
        return TaggingTransform(tag_key=config.tag_key, matcher=config.matcher)
