"""Transformations applicable to all elements."""
from typing import (Dict, Optional, Sequence, Any, Mapping, TypeVar)
import dataclasses
import re

from doc_scraper import doc_struct
from doc_scraper import help_docs
from doc_scraper import doc_transform

_V = TypeVar('_V')


@dataclasses.dataclass(kw_only=True)
class StripElementsConfig():
    """Configuration for removing unwanted attributes."""

    remove_attrs_re: Optional[Sequence[str]] = dataclasses.field(
        default=None,
        metadata={
            'help_text':
                'List for regexes. Matching keys in `attribs` are removed.',
            'help_samples': [('Remove all starting with _ or X_',
                              help_docs.RawSample('["_.*", "X_.*]'))]
        })
    remove_styles_re: Optional[Sequence[str]] = dataclasses.field(
        default=None,
        metadata={
            'help_text':
                'List for regexes. Matching keys in `styles` are removed.',
            'help_samples': [('Remove all styles with "font" in the key',
                              help_docs.RawSample('[".*font.*"]'))]
        })
    remove_style_rules_re: Optional[Sequence[str]] = dataclasses.field(
        default=None,
        metadata={
            'help_text':
                'List for regexes. Matching keys in `style_rules ' +
                'are removed from SharedData.',
            'help_samples': [('Remove all starting ".lst" or "ul."',
                              help_docs.RawSample(r'["\.lst.*", "ul\..*]'))]
        })


class StripElementsTransform(doc_transform.Transformation):
    """Transformation to remove unwanted attributes from elements.

    E.g.:

    `doc_struct.Element({'key1':'value', 'style':'...'}, ...)`
    is transformed (with default args) into
    `doc_struct.Element({'key1':'value'}, ...)`
    (as the `style` key is usually not needed)
    """

    def __init__(
        self,
        context: Optional[doc_transform.TransformationContext] = None,
        remove_attrs_re: Optional[Sequence[str]] = None,
        remove_styles_re: Optional[Sequence[str]] = None,
        remove_style_rules_re: Optional[Sequence[str]] = None,
    ) -> None:
        """Create an instance.

        Defaults for arguments are set to styles and attributes that are
        not useful for matching data.

        Args:
            context: Optional transformation context.
            remove_attrs_re: List of regular expressions matching keys in
                `attrs`. Matching entries are removed in any element type.
            remove_styles_re: List of regular expressions matching keys in
                `style`. Matching entries are removed in any element type.
            remove_styles_re: List of regular expressions matching keys in
                style_rules`. Matching entries are removed from SharedData.
        """
        super().__init__(context)
        if remove_attrs_re is None:
            remove_attrs_re = ['style']
        if remove_styles_re is None:
            remove_styles_re = [
                'padding.*', 'font-family', 'line-height', 'orphans',
                'page-break-after', 'widows', 'vertical-align', 'margin.*',
                'text-align'
            ]
        if remove_style_rules_re is None:
            remove_style_rules_re = []

        self.remove_attrs_re = [
            re.compile(regex) for regex in set(remove_attrs_re)
        ]
        self.remove_styles_re = [
            re.compile(regex) for regex in set(remove_styles_re)
        ]
        self.remove_style_rules_re = [
            re.compile(regex) for regex in set(remove_style_rules_re)
        ]

    @classmethod
    def from_config(
        cls,
        config: Optional[StripElementsConfig] = None
    ) -> 'StripElementsTransform':
        """Create an instance from the config dataclass."""
        if config is None:
            config = StripElementsConfig()
        return StripElementsTransform(
            remove_attrs_re=config.remove_attrs_re,
            remove_style_rules_re=config.remove_style_rules_re,
            remove_styles_re=config.remove_styles_re)

    def _is_included(self, dict_key: str,
                     exclude_re_list: Sequence[re.Pattern[str]]) -> bool:
        """Check if the dictionary key matches non of the excludes."""
        for regex in exclude_re_list:
            if regex.fullmatch(dict_key):
                return False
        return True

    def _transform_element_base(
            self, element: doc_struct.Element) -> doc_struct.Element:
        """Strip `attrs` and `style` in all element types."""
        new_attrs: Dict[str, Any] = dict()
        for key, value in element.attrs.items():
            if self._is_included(key, self.remove_attrs_re):
                new_attrs[key] = value

        new_style: Dict[str, str] = dict()
        for key, value in element.style.items():
            if self._is_included(key, self.remove_styles_re):
                new_style[key] = value

        return dataclasses.replace(element, attrs=new_attrs, style=new_style)

    def _transform_shared_data(
            self, shared_data: doc_struct.SharedData) -> doc_struct.SharedData:
        """Remove rules from SharedData.style_rules."""
        new_rules: Dict[str, Mapping[str, str]] = dict()
        for key, value in shared_data.style_rules.items():
            if self._is_included(key, self.remove_style_rules_re):
                new_rules[key] = value

        return super()._transform_shared_data(
            dataclasses.replace(shared_data, style_rules=new_rules))
