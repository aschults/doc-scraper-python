"""Transformations applicable to all elements."""
from typing import (Dict, Optional, Sequence, Any, Mapping, TypeVar)
import dataclasses

from doc_scraper import doc_struct
from doc_scraper import doc_transform
from doc_scraper.basic_transforms import tags_basic
from doc_scraper.basic_transforms import tags_relation

_V = TypeVar('_V')


@dataclasses.dataclass(kw_only=True)
class StripElementsConfig():
    """Configuration for removing unwanted attributes."""

    remove_attrs_re: Optional[Sequence[
        tags_basic.StringMatcher]] = dataclasses.field(
            default=None,
            metadata={
                'help_text':
                    'List for regexes. Matching keys in ' +
                    '`attribs` are removed.',
                'help_samples': [('Remove all starting with _ or X_',
                                  ['_.*', 'X_.*'])]
            })
    remove_styles_re: Optional[Sequence[
        tags_basic.StringMatcher]] = dataclasses.field(
            default=None,
            metadata={
                'help_text':
                    'List for regexes. Matching keys in `styles` are removed.',
                'help_samples': [('Remove all styles with "font" in the key',
                                  ['.*font.*'])]
            })
    remove_style_rules_re: Optional[Sequence[
        tags_basic.StringMatcher]] = dataclasses.field(
            default=None,
            metadata={
                'help_text':
                    'List for regexes. Matching keys in `style_rules ' +
                    'are removed from SharedData.',
                'help_samples': [('Remove all starting ".lst" or "ul."',
                                  [r'\.lst.*', r'ul\..*'])]
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
        remove_attrs_re: Optional[Sequence[tags_basic.StringMatcher]] = None,
        remove_styles_re: Optional[Sequence[tags_basic.StringMatcher]] = None,
        remove_style_rules_re: Optional[Sequence[
            tags_basic.StringMatcher]] = None,
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
            remove_style_rules_re: List of regular expressions matching
                style keys to remove.
        """
        super().__init__(context)
        if remove_attrs_re is None:
            remove_attrs_re = [tags_basic.StringMatcher('style')]
        if remove_styles_re is None:
            remove_styles_re = [
                tags_basic.StringMatcher(style)
                for style in ('padding.*', 'font-family', 'line-height',
                              'orphans', 'page-break-after', 'widows',
                              'vertical-align', 'margin.*', 'text-align')
            ]
        if remove_style_rules_re is None:
            remove_style_rules_re = []

        self.remove_attrs_re = remove_attrs_re
        self.remove_styles_re = remove_styles_re
        self.remove_style_rules_re = remove_style_rules_re

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

    def _is_included(
            self, dict_key: str,
            exclude_re_list: Sequence[tags_basic.StringMatcher]) -> bool:
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


class DropElementsConfig(tags_relation.RelationalMatchingConfig):
    """Select elements to be dropped from the document."""


class DropElementsTransform(doc_transform.Transformation):
    """Transformation to remove unwanted elements, except for table cells."""

    def __init__(
            self,
            config: DropElementsConfig,
            context: Optional[doc_transform.TransformationContext] = None
    ) -> None:
        """Create an instance."""
        super().__init__(context)
        self.config = config

    def _transform_doc_content_element(
        self, element_number: int, element: doc_struct.StructuralElement
    ) -> Optional[doc_struct.StructuralElement]:
        if self.config.is_matching(element, self.context.path_objects):
            return None
        return super()._transform_doc_content_element(element_number, element)

    def _transform_bullet_list_item(
            self, item_number: int,
            item: doc_struct.BulletItem) -> Optional[doc_struct.BulletItem]:
        if self.config.is_matching(item, self.context.path_objects):
            return None
        return super()._transform_bullet_list_item(item_number, item)

    def _transform_nested_bullet_item(
            self, item_number: int,
            item: doc_struct.BulletItem) -> Optional[doc_struct.BulletItem]:
        if self.config.is_matching(item, self.context.path_objects):
            return None
        return super()._transform_nested_bullet_item(item_number, item)

    def _transform_paragraph_elements_item(
        self, location: int, element: doc_struct.ParagraphElement
    ) -> Optional[doc_struct.ParagraphElement]:
        if self.config.is_matching(element, self.context.path_objects):
            return None
        return super()._transform_paragraph_elements_item(location, element)

    def _transform_section_content_item(
        self, index: int, item: doc_struct.StructuralElement
    ) -> Optional[doc_struct.StructuralElement]:
        if self.config.is_matching(item, self.context.path_objects):
            return None
        return super()._transform_section_content_item(index, item)

    def _transform_text_line_elements_item(
        self, index: int, item: doc_struct.ParagraphElement
    ) -> Optional[doc_struct.ParagraphElement]:
        if self.config.is_matching(item, self.context.path_objects):
            return None
        return super()._transform_text_line_elements_item(index, item)

    def _transform_note_item(
            self, index: int,
            paragraph: doc_struct.Paragraph) -> Optional[doc_struct.Paragraph]:
        if self.config.is_matching(paragraph, self.context.path_objects):
            return None
        return super()._transform_note_item(index, paragraph)
