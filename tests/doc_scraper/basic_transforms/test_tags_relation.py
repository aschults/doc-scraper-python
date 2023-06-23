"""Test the basic transformations for all elements."""

from typing import Set
import unittest
import dataclasses
from typing import TypeVar, Optional

from parameterized import parameterized  # type:ignore

from doc_scraper.basic_transforms import tags_relation
from doc_scraper.basic_transforms import tags_basic
from doc_scraper import doc_struct

SINGLE_LINE_TREE = doc_struct.Section(
    tags={'id': '1'},
    heading=None,
    content=[
        doc_struct.BulletItem(
            tags={'id': '2'},
            list_type='ul',
            elements=[doc_struct.Chip(tags={'id': '3'}, text='here')]),
    ])

SINGLE_LINE_TREE2 = doc_struct.Section(
    tags={'id': '1'},
    heading=None,
    content=[
        doc_struct.BulletItem(
            tags={'id': '2'},
            list_type='ul',
            elements=[
                doc_struct.TextLine(
                    elements=[doc_struct.Chip(tags={'id': '3'}, text='here')])
            ]),
    ])

DOUBLE_X_DOUBLE_TREE = doc_struct.Section(
    tags={'id': '1'},
    heading=None,
    content=[
        doc_struct.BulletItem(tags={'id': '2a'},
                              list_type='ul',
                              elements=[
                                  doc_struct.Chip(tags={'id': '3a'},
                                                  text='first text'),
                                  doc_struct.Chip(tags={'id': '3b'},
                                                  text='second text')
                              ]),
        doc_struct.Paragraph(tags={'id': '2b'},
                             elements=[
                                 doc_struct.Chip(tags={'id': '3c'},
                                                 text='third text'),
                                 doc_struct.Chip(tags={'id': '3d'},
                                                 text='fourth text')
                             ]),
    ])

PARAGRAPH_FLAT = doc_struct.Paragraph(
    tags={'id': '2'},
    elements=[
        doc_struct.Chip(tags={'id': '3a'}, text='third text'),
        doc_struct.Chip(tags={'id': '3b'}, text='fourth text'),
        doc_struct.Chip(tags={'id': '3c'}, text='third text'),
        doc_struct.Chip(tags={'id': '3d'}, text='fourth text')
    ],
)

PARAGRAPH_TEXT_LINE = doc_struct.Paragraph(
    tags={'id': '1'},
    elements=[
        doc_struct.TextLine(tags={'id': '2a'},
                            elements=[
                                doc_struct.Chip(tags={'id': '3a'},
                                                text='third text'),
                                doc_struct.Chip(tags={'id': '3b'},
                                                text='fourth text'),
                            ]),
        doc_struct.TextLine(tags={'id': '2b'},
                            elements=[
                                doc_struct.Chip(tags={'id': '3c'},
                                                text='third text'),
                                doc_struct.Chip(tags={'id': '3d'},
                                                text='fourth text'),
                            ]),
    ],
)

TABLE = doc_struct.Table(
    tags={'id': '2'},
    elements=[
        [
            doc_struct.DocContent(tags={'id': '3a'}, elements=[]),
            doc_struct.DocContent(tags={'id': '3b'}, elements=[]),
        ],
        [
            doc_struct.DocContent(tags={'id': '3c'}, elements=[]),
            doc_struct.DocContent(tags={'id': '3d'}, elements=[]),
        ],
    ],
)

_T = TypeVar('_T', bound=object)


def _deref(obj: Optional[_T]) -> _T:
    if obj is None:
        raise AssertionError('should not be none')
    return obj


def _tag_type_descendent(
    element_type: type[doc_struct.Element]
) -> tags_relation.RelationalTaggingConfig:
    return tags_relation.RelationalTaggingConfig(
        match_descendent=tags_basic.TagMatchConfig(
            element_types=[element_type]),
        tags=tags_basic.TagUpdateConfig(add={'x': '1'}),
    )


def _tag_type_ancestor(
    *element_type: type[doc_struct.Element],
    position: tags_relation.PositionMatchConfig = tags_relation.
    PositionMatchConfig()
) -> tags_relation.RelationalTaggingConfig:
    return tags_relation.RelationalTaggingConfig(
        match_ancestor_list=[
            tags_relation.PositionMatchConfig(element_types=[element])
            for element in element_type
        ],
        match_element=position,
        tags=tags_basic.TagUpdateConfig(add={'x': '1'}),
    )


class TestRelationMatching(unittest.TestCase):
    """Test matching elements by tags."""

    @parameterized.expand([  # type: ignore
        (
            'Single element match',
            SINGLE_LINE_TREE,
            _tag_type_descendent(doc_struct.Chip),
            {'1', '2'},
        ),
        (
            'Single element non leaf match',
            SINGLE_LINE_TREE,
            _tag_type_descendent(doc_struct.BulletItem),
            {'1'},
        ),
        (
            'Single match root indirect',
            DOUBLE_X_DOUBLE_TREE,
            dataclasses.replace(_tag_type_descendent(doc_struct.Chip),
                                match_element=tags_basic.TagMatchConfig(
                                    element_types=[doc_struct.Section])),
            {'1'},
        ),
        (
            'Single type non match',
            SINGLE_LINE_TREE,
            _tag_type_descendent(doc_struct.Table),
            set(),
        ),
        (
            'Double x double without leaves',
            DOUBLE_X_DOUBLE_TREE,
            _tag_type_descendent(doc_struct.ParagraphElement),
            {'1', '2a', '2b'},
        ),
        (
            'Double x double only root',
            DOUBLE_X_DOUBLE_TREE,
            _tag_type_descendent(doc_struct.StructuralElement),
            {'1'},
        ),
        (
            'Double match branch only',
            DOUBLE_X_DOUBLE_TREE,
            dataclasses.replace(
                _tag_type_descendent(doc_struct.ParagraphElement),
                match_element=tags_basic.TagMatchConfig(element_types=[
                    doc_struct.BulletItem, doc_struct.Paragraph
                ])),
            {'2a', '2b'},
        ),
    ])
    # pylint: disable=unused-argument
    def test_match_descendents(self, summary: str, data: doc_struct.Element,
                               config: tags_relation.RelationalTaggingConfig,
                               expected: Set[str]):
        """Test the match_descendents function."""
        result = tags_basic.TaggingTransform(config)(data)

        print(result)
        changed = set(element.tags['id']
                      for element in tags_basic.ElementFilterConverter(
                          lambda element: 'x' in element.tags).convert(result))

        self.assertEqual(expected, changed)

    @parameterized.expand([  # type: ignore
        (
            'Single element match parent',
            SINGLE_LINE_TREE,
            _tag_type_ancestor(doc_struct.BulletItem),
            {'3'},
        ),
        (
            'Single element match parent more constraint',
            SINGLE_LINE_TREE,
            _tag_type_ancestor(doc_struct.Section, doc_struct.BulletItem),
            {'3'},
        ),
        (
            'Single element match parent constraint with gap',
            SINGLE_LINE_TREE2,
            _tag_type_ancestor(doc_struct.Section, doc_struct.TextLine),
            {'3'},
        ),
        (
            'Single element match 2 levels',
            SINGLE_LINE_TREE,
            _tag_type_ancestor(doc_struct.Section),
            {'2', '3'},
        ),
        (
            'Single non match',
            SINGLE_LINE_TREE,
            _tag_type_ancestor(doc_struct.Table),
            set(),
        ),
        (
            'Non match bad order',
            SINGLE_LINE_TREE2,
            _tag_type_ancestor(doc_struct.TextLine, doc_struct.Section),
            set(),
        ),
        (
            'Single element non match',
            doc_struct.Chip(text='blah', tags={'id': '1'}),
            _tag_type_ancestor(doc_struct.Section),
            set(),
        ),
        (
            'Single element match',
            doc_struct.Chip(text='blah', tags={'id': '1'}),
            _tag_type_ancestor(),
            set('1'),
        ),
    ])
    # pylint: disable=unused-argument
    def test_match_ancesors(self, summary: str, data: doc_struct.Element,
                            config: tags_relation.RelationalTaggingConfig,
                            expected: Set[str]):
        """Test the match_descendents function."""
        result = tags_basic.TaggingTransform(config)(data)

        print(result)
        changed = set(element.tags['id']
                      for element in tags_basic.ElementFilterConverter(
                          lambda element: 'x' in element.tags).convert(result))

        self.assertEqual(expected, changed)

    @parameterized.expand([  # type: ignore
        (
            'Match first col',
            DOUBLE_X_DOUBLE_TREE,
            _tag_type_ancestor(
                doc_struct.Section,
                position=tags_relation.PositionMatchConfig(end_col=1)),
            {'3a', '3c'},
        ),
        (
            'Match last col',
            DOUBLE_X_DOUBLE_TREE,
            _tag_type_ancestor(
                doc_struct.Section,
                position=tags_relation.PositionMatchConfig(start_col=1)),
            {'3b', '3d'},
        ),
        (
            'Match flat paragraph middle',
            PARAGRAPH_FLAT,
            _tag_type_ancestor(doc_struct.Paragraph,
                               position=tags_relation.PositionMatchConfig(
                                   start_col=1, end_col=-1)),
            {'3b', '3c'},
        ),
        (
            'Match text line paragraph first col',
            PARAGRAPH_TEXT_LINE,
            _tag_type_ancestor(
                doc_struct.TextLine,
                position=tags_relation.PositionMatchConfig(end_col=1)),
            {'3a', '3c'},
        ),
        (
            'Match text line paragraph first row',
            PARAGRAPH_TEXT_LINE,
            _tag_type_ancestor(
                doc_struct.TextLine,
                position=tags_relation.PositionMatchConfig(end_row=1)),
            {'3a', '3b'},
        ),
        (
            'Match text line paragraph top right',
            PARAGRAPH_TEXT_LINE,
            _tag_type_ancestor(doc_struct.TextLine,
                               position=tags_relation.PositionMatchConfig(
                                   end_row=1, start_col=1)),
            {'3b'},
        ),
        (
            'Match table first col',
            TABLE,
            _tag_type_ancestor(
                doc_struct.Table,
                position=tags_relation.PositionMatchConfig(end_col=1)),
            {'3a', '3c'},
        ),
        (
            'Match table first row',
            TABLE,
            _tag_type_ancestor(
                doc_struct.Table,
                position=tags_relation.PositionMatchConfig(end_row=1)),
            {'3a', '3b'},
        ),
        (
            'Match table top right',
            TABLE,
            _tag_type_ancestor(doc_struct.Table,
                               position=tags_relation.PositionMatchConfig(
                                   end_row=1, start_col=1)),
            {'3b'},
        ),
        (
            'Match structural element first row',
            DOUBLE_X_DOUBLE_TREE,
            _tag_type_ancestor(
                doc_struct.Section,
                position=tags_relation.PositionMatchConfig(end_row=1)),
            {'2a'},
        ),
    ])
    # pylint: disable=unused-argument
    def test_match_position(self, summary: str, data: doc_struct.Element,
                            config: tags_relation.RelationalTaggingConfig,
                            expected: Set[str]):
        """Test the match_descendents function."""
        result = tags_basic.TaggingTransform(config)(data)

        print(result)
        changed = set(element.tags['id']
                      for element in tags_basic.ElementFilterConverter(
                          lambda element: 'x' in element.tags).convert(result))

        self.assertEqual(expected, changed)


class TestIsInRange(unittest.TestCase):
    """Teset the is_in_range function."""

    def test_bounded_matches(self):
        """Test element in relation with bounded range."""
        self.assertTrue(tags_relation.is_in_range(1, 0, 2, 4))
        self.assertTrue(tags_relation.is_in_range(1, 0, 2, 1))
        self.assertTrue(tags_relation.is_in_range(1, 1, 2, 2))

    def test_unbounded_matches(self):
        """Test element in relation with UNbounded range."""
        self.assertTrue(tags_relation.is_in_range(1, None, 2, 4))
        self.assertTrue(tags_relation.is_in_range(1, 0, None, 4))
        self.assertTrue(tags_relation.is_in_range(1, None, None, 4))

    def test_bounded_nonmatch(self):
        """Test element NOT in relation with bounded range."""
        self.assertFalse(tags_relation.is_in_range(2, 0, 2, 4))
        self.assertFalse(tags_relation.is_in_range(3, 0, 2, 4))
        self.assertFalse(tags_relation.is_in_range(1, 2, 3, 4))

    def test_unbounded_nonmatch(self):
        """Test element NOT in relation with UNbounded range."""
        self.assertFalse(tags_relation.is_in_range(2, None, 2, 4))
        self.assertFalse(tags_relation.is_in_range(3, None, 2, 4))
        self.assertFalse(tags_relation.is_in_range(1, 2, None, 4))

    def test_negative(self):
        """Test negative range indices."""
        self.assertTrue(tags_relation.is_in_range(2, 0, -1, 4))
        self.assertFalse(tags_relation.is_in_range(2, 0, -2, 4))
        self.assertTrue(tags_relation.is_in_range(2, -2, 4, 4))
        self.assertFalse(tags_relation.is_in_range(1, -1, 2, 4))

    def test_special(self):
        """Test special cases."""
        self.assertFalse(tags_relation.is_in_range(1, 0, 2, 0))  # zero length
        self.assertFalse(tags_relation.is_in_range(2, 2, 2, 4))  # empty range
        self.assertFalse(tags_relation.is_in_range(None, 0, 4,
                                                   4))  # None as coordinate
        self.assertRaisesRegex(
            ValueError, '.*positive.*',
            lambda: tags_relation.is_in_range(2, 0, 2, -1))  # negative length


class TestCoordinateGrid(unittest.TestCase):
    """Test the coordinate grid classes."""

    def test_flat_paragraph(self):
        """Test coordinate grid over flat paragraphs."""
        grid = tags_relation.coord_grid_from_parent(PARAGRAPH_FLAT)
        self.assertEqual('3b', _deref(grid.get(1)).tags['id'])
        self.assertEqual(3, grid.find(PARAGRAPH_FLAT.elements[3]))
        self.assertIsNone(grid.find(doc_struct.Element()))

    def test_empty_flat_paragraph(self):
        """Test coordinate grid over empty paragraphs."""
        grid = tags_relation.coord_grid_from_parent(
            doc_struct.Paragraph(elements=[]))
        self.assertIsNone(grid.get(None))
        self.assertIsNone(grid.get((2, 3)))
        self.assertIsNone(grid.find(PARAGRAPH_FLAT.elements[3]))

    def test_flat_paragraph_special(self):
        """Test special cases for coordinate grid for flat paragraphs."""
        grid = tags_relation.coord_grid_from_parent(PARAGRAPH_FLAT)
        self.assertIsNone(grid.get(None))
        self.assertIsNone(grid.get((2, 3)))
        self.assertIsNone(grid.find(doc_struct.Chip(text='no match')))

    def test_doc_content(self):
        """Test coordinate grid over doc content (vertical)."""
        grid = tags_relation.coord_grid_from_parent(
            doc_struct.DocContent(elements=[PARAGRAPH_FLAT]))
        self.assertEqual('2', _deref(grid.get(0)).tags['id'])
        self.assertEqual(0, grid.find(PARAGRAPH_FLAT))
        self.assertIsNone(grid.find(doc_struct.Element()))

    def test_2d_paragraph(self):
        """Test coordinate grid of 2d paragraphs."""
        grid = tags_relation.coord_grid_from_parent(PARAGRAPH_TEXT_LINE)
        self.assertEqual('3c', _deref(grid.get((1, 0))).tags['id'])
        row = PARAGRAPH_TEXT_LINE.elements[0]
        if not isinstance(row, doc_struct.TextLine):
            self.fail(f'Bad type {row}')

        self.assertEqual((0, 1), grid.find(row.elements[1]))
        self.assertIsNone(grid.find(doc_struct.Element()))

    def test_table(self):
        """Test coordinate grid of tables (2d)."""
        content = doc_struct.DocContent(elements=[], tags={'id': '1'})
        grid = tags_relation.coord_grid_from_parent(
            doc_struct.Table(elements=[[content]]))
        self.assertEqual('1', _deref(grid.get((0, 0))).tags['id'])
        self.assertEqual((0, 0), grid.find(content))
        self.assertIsNone(grid.find(doc_struct.DocContent(elements=[])))

    def test_table_special(self):
        """Test special cases for coordinate grid for table."""
        content = doc_struct.DocContent(elements=[], tags={'id': '1'})
        grid = tags_relation.coord_grid_from_parent(
            doc_struct.Table(elements=[[content]]))
        self.assertIsNone(grid.get(None))

    def test_empty_table(self):
        """Test coordinate grid for empty table."""
        grid = tags_relation.coord_grid_from_parent(
            doc_struct.Table(elements=[]))
        self.assertIsNone(grid.get(None))
        self.assertIsNone(grid.get(2))
        self.assertIsNone(grid.find(PARAGRAPH_FLAT.elements[3]))
