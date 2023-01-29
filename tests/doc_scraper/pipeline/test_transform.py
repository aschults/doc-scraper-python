"""Test the basic transformations for bullet lists/items."""

import dataclasses
import unittest
from typing import Type, List

from doc_scraper.pipeline import transforms

from doc_scraper import doc_struct
from doc_scraper import doc_transform


@dataclasses.dataclass(kw_only=True)
class ConfigForTest():
    """Configuration class to test build configs."""

    attrib_a: int = 0
    attrib_b: str = ''
    attrib_c: Type[doc_struct.Element] = doc_struct.Element


class ChainTransformationTest(unittest.TestCase):
    """Test the transformation chain class."""

    def test_simple_chain(self):
        """Test basic functionality."""
        transform_list: List[transforms.TransformationFunction] = [
            lambda element: dataclasses.replace(
                element, attrs=dict(element.attrs, v1=1)),
            lambda element: dataclasses.replace(
                element, attrs=dict(element.attrs, v2=2)),
        ]
        chain = transforms.ChainedTransformation(*transform_list)

        result = chain(doc_struct.Element(attrs={'v0': 0}))

        self.assertEqual(doc_struct.Element(attrs={
            'v0': 0,
            'v1': 1,
            'v2': 2
        }), result)

    def test_empty_chain(self):
        """Test empty chain, expecting identity."""
        chain = transforms.ChainedTransformation()

        result = chain(doc_struct.Element(attrs={'v0': 0}))

        self.assertEqual(doc_struct.Element(attrs={'v0': 0}), result)


class TestBuilder(unittest.TestCase):
    """Test the transformation builder."""

    def test_simple_register(self):
        """Test simple registration/creation."""
        bld = transforms.TransformBuilder()

        bld.register(
            'some_key', lambda x: lambda b: doc_struct.Element(
                attrs={'y': x + b.attrs['y'] + 'b'}))

        result = bld.create_instance('some_key',
                                     '_')(doc_struct.Element(attrs={'y': 'a'}))
        self.assertEqual(result.attrs['y'], '_ab')

    def test_register_with_hint(self):
        """Test registration with type hint in builder function."""
        bld = transforms.TransformBuilder()

        def transform_builder(
                config: int) -> doc_transform.TransformationFunction:
            return lambda b: doc_struct.Element(
                attrs={'y': str(config) + b.attrs['y'] + 'b'})

        bld.register('some_key', transform_builder)

        result = bld.create_instance('some_key',
                                     33)(doc_struct.Element(attrs={'y': 'a'}))
        self.assertEqual(result.attrs['y'], '33ab')

    def test_create_chain(self):
        """Test the creation of chained transformations."""
        bld = transforms.TransformBuilder()

        def transform_func1(
                config: int) -> doc_transform.TransformationFunction:
            return lambda b: doc_struct.Element(
                attrs={'y': str(config) + b.attrs['y'] + 'b'})

        def transform_func2(
                config: int) -> doc_transform.TransformationFunction:
            return lambda b: doc_struct.Element(
                attrs={'y': str(config) + b.attrs['y'] + 'c'})

        bld.register('t1', transform_func1)
        bld.register('t2', transform_func2)

        transform_config = [
            transforms.TransformConfig(kind='t1', config=11),
            transforms.TransformConfig(kind='t2', config=22),
        ]
        chained = bld.create_chain(*transform_config)

        result = chained(doc_struct.Element(attrs={'y': 'a'}))
        self.assertEqual(result.attrs['y'], '2211abc')
