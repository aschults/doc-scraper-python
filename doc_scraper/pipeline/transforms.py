"""Classes and functions to allow building pipelines of transformations."""

import logging
from typing import Any, Callable

from doc_scraper import doc_transform as transform_base

from doc_scraper.basic_transforms import bullets_basic
from doc_scraper.basic_transforms import paragraph_basic
from doc_scraper.basic_transforms import sections_basic
from doc_scraper.basic_transforms import tags_basic
from doc_scraper.basic_transforms import tags_relation
from doc_scraper.basic_transforms import elements_basics
from doc_scraper.basic_transforms import paragraph_element_basic
from doc_scraper.basic_transforms import json_basic

from . import generic

TransformationFunction = transform_base.TransformationFunction

TransformConfig = generic.BuilderConfig


class ChainedTransformation():
    """Execute a sequence of transformations."""

    def __init__(self, *transforms: Callable[[Any], Any]) -> None:
        """Create an instance."""
        self.transforms = transforms

    def __call__(self, element: Any) -> Any:
        """Execute transformations in sequence."""
        for index, transform in enumerate(self.transforms):
            element = transform(element)
            logging.debug('Document after transform %d: %s', index,
                          str(element))
        return element


class TransformBuilder(generic.GenericBuilder[Callable[[Any], Any]]):
    """Build transformations based on string tags."""

    def create_chain(self,
                     *config_data: TransformConfig) -> Callable[[Any], Any]:
        """Create a chained transformation.

        Args:
            *config_data: Configuration of a sequence of transforms.

        Returns:
            A function that applies all of the transformations
            specified in config_data.
        """
        transformations = [
            self.create_instance(config) for config in config_data
        ]
        return ChainedTransformation(*transformations)


def get_default_builder() -> TransformBuilder:
    """Create a transform builder based on pre-registered transforms."""
    # pylint: disable=unnecessary-lambda
    default_builder = TransformBuilder()
    default_builder.register(
        'nest_bullets',
        lambda: bullets_basic.BulletsTransform(),
        help_doc='Rearrange bullet items so they are properly nested ' +
        '(in attribute named "neseted"',
    )
    default_builder.register(
        'merge_by_tag',
        paragraph_basic.build_tag_merge_transform,
        help_doc='Merge paragraph items by matching tags.',
    )

    default_builder.register(
        'split_text',
        lambda config: paragraph_basic.TextSplitTransformation(config),
        config_type=paragraph_basic.TextSplitConfig,
        help_doc='Split text-based elements by regex groups.')
    default_builder.register(
        'nest_sections',
        lambda: sections_basic.SectionNestingTransform(),
        help_doc='Rearrange the doc to match the hierarchy of headings.',
    )
    default_builder.register(
        'tag_matching',
        tags_basic.TaggingTransform.from_config,
        help_doc='Add tags to any element if they match the criteria.',
        config_type=tags_relation.RelativeTaggingConfig)

    default_builder.register(
        'strip_elements',
        elements_basics.StripElementsTransform.from_config,
        config_type=elements_basics.StripElementsConfig,
        help_doc='Remove unwanted keys from attrs, style ' +
        'and ShardData.style_rules')

    default_builder.register(
        'drop_elements',
        lambda config: elements_basics.DropElementsTransform(config),
        config_type=elements_basics.DropElementsConfig,
        help_doc='Remove matching elements from the document.'
    )
    default_builder.register(
        'regex_replace',
        lambda config: paragraph_element_basic.RegexReplacerTransform(config),
        config_type=paragraph_element_basic.RegexReplacerConfig,
        help_doc='Replace item text by regex substitution.'
    )

    default_builder.register('extract_json',
                             json_basic.build_json_extraction_transform,
                             help_doc='Extract relevant JSON parts.')

    return default_builder
