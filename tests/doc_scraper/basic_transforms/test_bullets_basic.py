"""Test the basic transformations for bullet lists/items."""
# pylint: disable=protected-access

import unittest
from typing import Any, Optional, Sequence, Union

from doc_scraper.basic_transforms import bullets_basic
from doc_scraper import doc_struct

_nest_items = bullets_basic._nest_items  # type: ignore
_merge_bullet_lists = bullets_basic._merge_bullet_lists  # type: ignore


def mkitem(
    level: Optional[int],
    label: str,
    nested: Optional[Sequence[doc_struct.BulletItem]] = None
) -> doc_struct.BulletItem:
    """Make a bullet item more easily."""
    return doc_struct.BulletItem(elements=[],
                                 level=level,
                                 left_offset=0,
                                 list_type=label,
                                 nested=nested or [])


class NestItemsTest(unittest.TestCase):
    """Test the nest_items function."""

    def condense_result(
        self, data: Union[doc_struct.BulletItem,
                          Sequence[doc_struct.BulletItem]]
    ) -> Any:
        """Filter out only what is relevant from results."""
        if isinstance(data, list):
            return [self.condense_result(e) for e in data]

        if isinstance(data, doc_struct.BulletItem):
            nested_data = self.condense_result(data.nested)
            return (data.list_type, data.level, nested_data)

        raise Exception(f'unexpected type of: {data}')

    def test_nested_two_toplevel(self):
        """Test nested items function."""
        items = [mkitem(0, 'a'), mkitem(1, 'a1'), mkitem(0, 'b')]
        result = _nest_items(0, items)

        self.assertEqual([
            ('a', 0, [
                ('a1', 1, []),
            ]),
            ('b', 0, []),
        ], self.condense_result(result))

    def test_nested_subtree(self):
        """Test nested items function fo multiple."""
        items = [
            mkitem(0, 'a'),
            mkitem(1, 'a1'),
            mkitem(1, 'a2'),
            mkitem(2, 'a2i'),
            mkitem(1, 'a3'),
            mkitem(0, 'b'),
            mkitem(1, 'b1'),
        ]
        result = _nest_items(0, items)
        self.assertEqual([
            ('a', 0, [
                ('a1', 1, []),
                ('a2', 1, [
                    ('a2i', 2, []),
                ]),
                ('a3', 1, []),
            ]),
            ('b', 0, [
                ('b1', 1, []),
            ]),
        ], self.condense_result(result))

    def test_wrapper_items(self):
        """Check that wrapper items are added."""
        items = [
            # Wrapper here x2
            mkitem(2, '__i'),
            mkitem(1, '_a'),
            mkitem(2, '_ai'),
            mkitem(0, '1'),
            # Wrapper here
            mkitem(2, '1_i'),
            mkitem(2, '1_ii'),
        ]
        result = _nest_items(0, items)
        self.assertEqual([
            ('empty', 0, [
                ('empty', 1, [
                    ('__i', 2, []),
                ]),
                ('_a', 1, [
                    ('_ai', 2, []),
                ]),
            ]),
            ('1', 0, [
                ('empty', 1, [
                    ('1_i', 2, []),
                    ('1_ii', 2, []),
                ]),
            ]),
        ], self.condense_result(result))

    def test_empty(self):
        """Test empty input."""
        result = _nest_items(0, [])
        self.assertEqual([], self.condense_result(result))

    def test_single_wrapper(self):
        """Test single item with wrapper."""
        result = _nest_items(
            0,
            [
                # Wrapper here
                mkitem(1, "x")
            ])
        self.assertEqual([('empty', 0, [('x', 1, [])])],
                         self.condense_result(result))

    def test_exception_on_bad_levels(self):
        """Test if exception is thrown when levels are wrong."""
        with self.assertRaisesRegex(ValueError,
                                    'Items list containing lower level.*'):
            _nest_items(1, [mkitem(0, "x")])


class MergeListsTest(unittest.TestCase):
    """Test merging bullet items."""

    def test_merge_two(self):
        """Test nested items function."""
        data = [
            doc_struct.BulletList(items=[mkitem(0, 'a')]),
            doc_struct.BulletList(items=[mkitem(0, 'b')]),
        ]
        expected = [
            doc_struct.BulletList(
                items=[mkitem(0, 'a'), mkitem(0, 'b')]),
        ]

        result = _merge_bullet_lists(data)
        self.assertEqual(expected, result)

    def test_merge_three(self):
        """Test nested items function."""
        data = [
            doc_struct.BulletList(items=[mkitem(0, 'a')]),
            doc_struct.BulletList(items=[mkitem(0, 'b')]),
            doc_struct.BulletList(items=[mkitem(0, 'c')]),
        ]
        expected = [
            doc_struct.BulletList(
                items=[mkitem(0, 'a'),
                       mkitem(0, 'b'),
                       mkitem(0, 'c')]),
        ]

        result = _merge_bullet_lists(data)
        self.assertEqual(expected, result)

    def test_merge_empty(self):
        """Test nested items function."""
        data = []
        expected = []

        result = _merge_bullet_lists(data)
        self.assertEqual(expected, result)

    def test_merge_one(self):
        """Test nested items function."""
        data = [
            doc_struct.BulletList(items=[mkitem(0, 'a')]),
        ]
        expected = [
            doc_struct.BulletList(items=[mkitem(0, 'a')]),
        ]

        result = _merge_bullet_lists(data)
        self.assertEqual(expected, result)

    def test_merge_empty_lists(self):
        """Test nested items function."""
        data = [
            doc_struct.BulletList(items=[]),
            doc_struct.BulletList(items=[]),
        ]
        expected = [
            doc_struct.BulletList(items=[]),
        ]

        result = _merge_bullet_lists(data)
        self.assertEqual(expected, result)

    def test_no_merge(self):
        """Test nested items function."""
        data = [
            doc_struct.BulletList(items=[mkitem(0, 'a')]),
            doc_struct.Paragraph(elements=[]),
            doc_struct.BulletList(items=[mkitem(0, 'c')]),
        ]
        expected = [
            doc_struct.BulletList(items=[mkitem(0, 'a')]),
            doc_struct.Paragraph(elements=[]),
            doc_struct.BulletList(items=[mkitem(0, 'c')]),
        ]

        result = _merge_bullet_lists(data)
        self.assertEqual(expected, result)

    def test_merge_on_other_element(self):
        """Test nested items function."""
        data = [
            doc_struct.BulletList(items=[mkitem(0, 'a')]),
            doc_struct.BulletList(items=[mkitem(0, 'b')]),
            doc_struct.Paragraph(elements=[]),
        ]
        expected = [
            doc_struct.BulletList(
                items=[mkitem(0, 'a'), mkitem(0, 'b')]),
            doc_struct.Paragraph(elements=[]),
        ]

        result = _merge_bullet_lists(data)
        self.assertEqual(expected, result)

    def test_merge_after_other_element(self):
        """Test nested items function."""
        data = [
            doc_struct.Paragraph(elements=[]),
            doc_struct.BulletList(items=[mkitem(0, 'a')]),
            doc_struct.BulletList(items=[mkitem(0, 'b')]),
        ]
        expected = [
            doc_struct.Paragraph(elements=[]),
            doc_struct.BulletList(
                items=[mkitem(0, 'a'), mkitem(0, 'b')]),
        ]

        result = _merge_bullet_lists(data)
        self.assertEqual(expected, result)


class BulletTransformTest(unittest.TestCase):
    """Test the whole transformation."""

    def test_transformation(self):
        """Test using simple merge and nesting of 2 items."""
        data = doc_struct.DocContent(elements=[
            doc_struct.BulletList(items=[mkitem(0, 'a')]),
            doc_struct.BulletList(items=[mkitem(1, 'b')]),
        ])
        expected = doc_struct.DocContent(elements=[
            doc_struct.BulletList(
                items=[mkitem(0, 'a', nested=[mkitem(1, 'b')])])
        ])

        transform = bullets_basic.BulletsTransform()
        print(transform(data))
        self.assertEqual(expected, transform(data))
