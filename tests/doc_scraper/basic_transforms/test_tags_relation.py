"""Test the basic transformations for all elements."""

from typing import (
    TypeVar,
    Optional,
    Sequence,
    Any,
    Set,
    cast,
    Mapping,
    Tuple,
    List,
)
import unittest
import dataclasses

from parameterized import parameterized  # type:ignore

from doc_scraper.basic_transforms import tags_relation
from doc_scraper.basic_transforms import tags_basic
from doc_scraper import doc_struct

SINGLE_LINE_PARAGRAPH = doc_struct.Paragraph(
    tags={'id': '1'},
    elements=[doc_struct.Chip(tags={'id': '2'}, text='here')])

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

SINGLE_LINE_TREE3 = doc_struct.Section(
    tags={'id': '1'},
    heading=None,
    content=[
        doc_struct.BulletItem(
            tags={'id': '2'},
            list_type='ul',
            elements=[],
            nested=[
                doc_struct.BulletItem(
                    tags={'id': '3'},
                    list_type='ul',
                    elements=[doc_struct.Chip(tags={'id': '4'}, text='here')]),
            ])
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
) -> tags_relation.RelativeTaggingConfig:
    return tags_relation.RelativeTaggingConfig(
        match_descendent=tags_basic.TagMatchConfig(
            element_types=tags_basic.TypeMatcher(element_type)),
        tags=tags_basic.TagUpdateConfig(add={'x': '1'}),
    )


def _tag_type_ancestor(
    *element_type: type[doc_struct.Element] | int,
    position: tags_relation.PositionMatchConfig = tags_relation.
    PositionMatchConfig()
) -> tags_relation.RelativeTaggingConfig:
    ancestor_matches: List[tags_relation.PositionMatchConfig |
                           tags_relation.MatchListGapConfig] = []
    for item in element_type:
        if isinstance(item, type):
            ancestor_matches.append(
                tags_relation.PositionMatchConfig(
                    element_types=tags_basic.TypeMatcher(item)))
        else:
            if item == 0:
                mode = 'any'
            elif item > 0:
                mode = 'exactly'
            else:
                mode = 'at_least'
                item = -item
            ancestor_matches.append(
                tags_relation.MatchListGapConfig(skip_ancestors=mode,
                                                 skip_count=item))
    return tags_relation.RelativeTaggingConfig(
        match_ancestor_list=ancestor_matches,
        match_element=position,
        tags=tags_basic.TagUpdateConfig(add={'x': '1'}),
    )


def _make_gap(skip_ancestors: tags_relation.SkipModeType,
              skip_count: int = 0) -> tags_relation.MatchListGapConfig:
    return tags_relation.MatchListGapConfig(skip_ancestors=skip_ancestors,
                                            skip_count=skip_count)


class TestMatchListGapConfig(unittest.TestCase):
    """Test the Ancestor List Gap class."""

    def test_construction(self):
        """Test correct construction."""
        self.assertTrue(
            tags_relation.MatchListGapConfig(
                skip_ancestors='any',).is_open_length,)
        self.assertTrue(_make_gap('at_least', 2).is_open_length,)
        self.assertFalse(_make_gap('exactly', 2).is_open_length,)

        self.assertRaisesRegex(ValueError, '.*non-zero.*',
                               lambda: _make_gap('exactly'))

        self.assertRaisesRegex(ValueError, '.*non-zero.*',
                               lambda: _make_gap('at_least'))

        self.assertRaisesRegex(ValueError, '.*No skip.count.*',
                               lambda: _make_gap('any', 1))

        self.assertRaisesRegex(ValueError, '.*Positive.*only.*',
                               lambda: _make_gap('exactly', -1))

    @parameterized.expand([  # type: ignore
        (('exactly', 2), ('exactly', 1), ('exactly', 3)),
        (('any', 0), ('exactly', 3), ('at_least', 3)),
        (('any', 0), ('at_least', 3), ('at_least', 3)),
        (('at_least', 1), ('at_least', 2), ('at_least', 3)),
        (('exactly', 1), ('at_least', 2), ('at_least', 3)),
    ])
    def test_merge(
        self,
        arg1: Tuple[tags_relation.SkipModeType, int],
        arg2: Tuple[tags_relation.SkipModeType, int],
        expected_args: Tuple[tags_relation.SkipModeType, int],
    ):
        """Test merges of two gaps."""
        self.assertEqual(_make_gap(*expected_args),
                         _make_gap(*arg1).merge(_make_gap(*arg2)))
        self.assertEqual(_make_gap(*expected_args),
                         _make_gap(*arg2).merge(_make_gap(*arg1)))


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
            dataclasses.replace(
                _tag_type_descendent(doc_struct.Chip),
                match_element=tags_basic.TagMatchConfig(
                    element_types=tags_basic.TypeMatcher(doc_struct.Section))),
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
                match_element=tags_basic.TagMatchConfig(
                    element_types=tags_basic.TypeMatcher(
                        doc_struct.BulletItem, doc_struct.Paragraph))),
            {'2a', '2b'},
        ),
    ])
    # pylint: disable=unused-argument
    def test_match_descendents(self, summary: str, data: doc_struct.Element,
                               config: tags_relation.RelativeTaggingConfig,
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
            'Single element non match',
            doc_struct.Chip(text='blah', tags={'id': '1'}),
            _tag_type_ancestor(doc_struct.Section),
            set(),
        ),
        (
            'Single element exact match',
            doc_struct.Chip(text='blah', tags={'id': '1'}),
            _tag_type_ancestor(doc_struct.Chip),
            set(),
        ),
        (
            'Single element to many flexible needed',
            doc_struct.Chip(text='blah', tags={'id': '1'}),
            _tag_type_ancestor(1),
            set(),
        ),
        (
            'Single element match any match',
            doc_struct.Chip(text='blah', tags={'id': '1'}),
            _tag_type_ancestor(0),
            set('1'),
        ),
        (
            'Single element match no matchers',
            doc_struct.Chip(text='blah', tags={'id': '1'}),
            _tag_type_ancestor(),
            set('1'),
        ),
        (
            'single parent match',
            SINGLE_LINE_PARAGRAPH,
            _tag_type_ancestor(doc_struct.Paragraph),
            {'2'},
        ),
        (
            'single parent match any before',
            SINGLE_LINE_PARAGRAPH,
            _tag_type_ancestor(0, doc_struct.Paragraph),
            {'2'},
        ),
        (
            'single parent match any after',
            SINGLE_LINE_PARAGRAPH,
            _tag_type_ancestor(doc_struct.Paragraph, 0),
            {'2'},
        ),
        (
            'single parent match any both sides',
            SINGLE_LINE_PARAGRAPH,
            _tag_type_ancestor(0, doc_struct.Paragraph, 0),
            {'2'},
        ),
        (
            'single parent non-match bat type',
            SINGLE_LINE_PARAGRAPH,
            _tag_type_ancestor(doc_struct.Section),
            set(),
        ),
        (
            'single parent non-match multi before',
            SINGLE_LINE_PARAGRAPH,
            _tag_type_ancestor(1, doc_struct.Paragraph),
            set(),
        ),
        (
            'single parent non-match multi after',
            SINGLE_LINE_PARAGRAPH,
            _tag_type_ancestor(doc_struct.Paragraph, 1),
            set(),
        ),
        (
            'single parent non-match multi both sides',
            SINGLE_LINE_PARAGRAPH,
            _tag_type_ancestor(1, doc_struct.Paragraph, 1),
            set(),
        ),
        (
            'single parent non-match atleast before',
            SINGLE_LINE_PARAGRAPH,
            _tag_type_ancestor(-1, doc_struct.Paragraph),
            set(),
        ),
        (
            'single parent non-match atleast after',
            SINGLE_LINE_PARAGRAPH,
            _tag_type_ancestor(doc_struct.Paragraph, -1),
            set(),
        ),
        (
            'single parent non-match atleast both sides',
            SINGLE_LINE_PARAGRAPH,
            _tag_type_ancestor(-1, doc_struct.Paragraph, -1),
            set(),
        ),
        (
            'Two parent single element match full',
            SINGLE_LINE_TREE,
            _tag_type_ancestor(doc_struct.Section, doc_struct.BulletItem),
            {'3'},
        ),
        (
            'Two parent single element full match any before',
            SINGLE_LINE_TREE,
            _tag_type_ancestor(0, doc_struct.Section, doc_struct.BulletItem),
            {'3'},
        ),
        (
            'Two parent single element full match any after',
            SINGLE_LINE_TREE,
            _tag_type_ancestor(doc_struct.Section, doc_struct.BulletItem, 0),
            {'3'},
        ),
        (
            'Two parent single element one match any before',
            SINGLE_LINE_TREE,
            _tag_type_ancestor(0, doc_struct.BulletItem),
            {'3'},
        ),
        (
            'Two parent single element one match at least before',
            SINGLE_LINE_TREE,
            _tag_type_ancestor(-1, doc_struct.BulletItem),
            {'3'},
        ),
        (
            'Two parent single element one match exact before',
            SINGLE_LINE_TREE,
            _tag_type_ancestor(1, doc_struct.BulletItem),
            {'3'},
        ),
        (
            'Two parent single element non-match bad at least before',
            SINGLE_LINE_TREE,
            _tag_type_ancestor(-2, doc_struct.BulletItem),
            set(),
        ),
        (
            'Two parent single element non-match bad exact before',
            SINGLE_LINE_TREE,
            _tag_type_ancestor(2, doc_struct.BulletItem),
            set(),
        ),
        (
            'Two parent single element one match any after',
            SINGLE_LINE_TREE,
            _tag_type_ancestor(doc_struct.Section, 0),
            {'2', '3'},
        ),
        (
            'Two parent single element one match multi after',
            SINGLE_LINE_TREE,
            _tag_type_ancestor(doc_struct.Section, -1),
            {'3'},
        ),
        (
            'Two parent single element one match exact after',
            SINGLE_LINE_TREE,
            _tag_type_ancestor(doc_struct.Section, 1),
            {'3'},
        ),
        (
            'Two parent single element non-match bad multi after',
            SINGLE_LINE_TREE,
            _tag_type_ancestor(doc_struct.Section, -2),
            set(),
        ),
        (
            'Two parent single element non-match exact after',
            SINGLE_LINE_TREE,
            _tag_type_ancestor(doc_struct.Section, 2),
            set(),
        ),
        (
            'Three parent single element match any middle',
            SINGLE_LINE_TREE3,
            _tag_type_ancestor(doc_struct.Section, 0, doc_struct.BulletItem),
            {'3', '4'},
        ),
        (
            'Three parent single element match any middle exact',
            SINGLE_LINE_TREE3,
            _tag_type_ancestor(doc_struct.Section, 1, doc_struct.BulletItem),
            {'4'},
        ),
        (
            'Three parent single element non-match any middle bad exact',
            SINGLE_LINE_TREE3,
            _tag_type_ancestor(doc_struct.Section, 2, doc_struct.BulletItem),
            set(),
        ),
        (
            'Three parent single element match any any at end',
            SINGLE_LINE_TREE3,
            _tag_type_ancestor(doc_struct.Section, doc_struct.BulletItem, 0),
            {'3', '4'},
        ),
        (
            'Three parent single element match exact any at end',
            SINGLE_LINE_TREE3,
            _tag_type_ancestor(doc_struct.Section, doc_struct.BulletItem, 1),
            {'4'},
        ),
        (
            'Three parent single element match exact any at end',
            SINGLE_LINE_TREE3,
            _tag_type_ancestor(doc_struct.Section, doc_struct.BulletItem, -1),
            {'4'},
        ),
        (
            'Single element match parent indef',
            SINGLE_LINE_TREE,
            _tag_type_ancestor(-1, doc_struct.BulletItem),
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
            _tag_type_ancestor(doc_struct.Section, 0, doc_struct.TextLine),
            {'3'},
        ),
        (
            'Single element match 2 levels',
            SINGLE_LINE_TREE,
            _tag_type_ancestor(doc_struct.Section, 0),
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
    ])
    # pylint: disable=unused-argument
    def test_match_ancesors(self, summary: str, data: doc_struct.Element,
                            config: tags_relation.RelativeTaggingConfig,
                            expected: Set[str]):
        """Test the match_descendents function."""
        print(summary)
        result = tags_basic.TaggingTransform(config)(data)

        print(result)
        changed = set(element.tags['id']
                      for element in tags_basic.ElementFilterConverter(
                          lambda element: 'x' in element.tags).convert(result))

        self.assertEqual(expected, changed)

    # pylint: disable=protected-access
    def test_canonicalize_ancestor_matchers(self):
        """Test canonicalizing (merging gaps) on ancestor lists."""
        self.maxDiff = None
        self.assertEqual(
            _tag_type_ancestor(-1).match_ancestor_list,
            _tag_type_ancestor(
                0, 1)._canonicalize_ancestor_matches(),  # type: ignore
        )

        self.assertEqual(
            _tag_type_ancestor(-1, doc_struct.Element).match_ancestor_list,
            _tag_type_ancestor(0, 1, doc_struct.Element).
            _canonicalize_ancestor_matches(),  # type: ignore
        )

        self.assertEqual(
            _tag_type_ancestor(doc_struct.Element, -2).match_ancestor_list,
            _tag_type_ancestor(
                doc_struct.Element, -1,
                1)._canonicalize_ancestor_matches(),  # type: ignore
        )

        self.assertEqual(
            _tag_type_ancestor(doc_struct.Element, 4,
                               doc_struct.Element).match_ancestor_list,
            _tag_type_ancestor(doc_struct.Element, 1, 2, 1,
                               doc_struct.Element).
            _canonicalize_ancestor_matches(),  # type: ignore
        )

        self.assertEqual(
            _tag_type_ancestor(doc_struct.Element, doc_struct.Element,
                               4).match_ancestor_list,
            _tag_type_ancestor(
                doc_struct.Element, doc_struct.Element, 1, 2,
                1)._canonicalize_ancestor_matches(),  # type: ignore
        )

        self.assertEqual(
            _tag_type_ancestor(-4, doc_struct.Element,
                               doc_struct.Element).match_ancestor_list,
            _tag_type_ancestor(1, -2, 1, doc_struct.Element,
                               doc_struct.Element).
            _canonicalize_ancestor_matches(),  # type: ignore
        )

    @parameterized.expand([  # type: ignore
        (
            'Match first col',
            DOUBLE_X_DOUBLE_TREE,
            _tag_type_ancestor(
                doc_struct.Section,
                0,
                position=tags_relation.PositionMatchConfig(end_col=1)),
            {'3a', '3c'},
        ),
        (
            'Match last col',
            DOUBLE_X_DOUBLE_TREE,
            _tag_type_ancestor(
                doc_struct.Section,
                0,
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
                0,
                doc_struct.TextLine,
                position=tags_relation.PositionMatchConfig(end_col=1)),
            {'3a', '3c'},
        ),
        (
            'Match text line paragraph first row',
            PARAGRAPH_TEXT_LINE,
            _tag_type_ancestor(
                0,
                doc_struct.TextLine,
                position=tags_relation.PositionMatchConfig(end_row=1)),
            {'3a', '3b'},
        ),
        (
            'Match text line paragraph top right',
            PARAGRAPH_TEXT_LINE,
            _tag_type_ancestor(
                0,
                doc_struct.TextLine,
                position=tags_relation.PositionMatchConfig(end_row=1,
                                                           start_col=1),
            ),
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
                            config: tags_relation.RelativeTaggingConfig,
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


class TestCalcRelativeIndex(unittest.TestCase):
    """Test helper function to calculate relative index."""

    @parameterized.expand([  # type: ignore
        (
            (3, 4, 'first'),
            0,
        ),
        (
            (3, 4, None),
            3,
        ),
        (
            (1, 4, 'last'),
            3,
        ),
        (
            (3, 4, 'last'),
            3,
        ),
        (
            (2, 4, 'next'),
            3,
        ),
        (
            (3, 4, 'next'),
            None,
        ),
        (
            (2, 4, 'prev'),
            1,
        ),
        (
            (0, 4, 'prev'),
            None,
        ),
    ])
    def test_basics(self, args: Sequence[Any], expected: Optional[int]):
        """Test various cases for relative index calculation."""
        self.assertEqual(expected, tags_relation.calc_relative_index(*args))


# Larger, 4x4 table
TABLE2 = doc_struct.Table(
    tags={'id': '0'},
    elements=[
        [
            doc_struct.DocContent(tags={'id': '11'}, elements=[]),
            doc_struct.DocContent(tags={'id': '12'}, elements=[]),
            doc_struct.DocContent(tags={'id': '13'}, elements=[]),
            doc_struct.DocContent(tags={'id': '14'}, elements=[]),
        ],
        [
            doc_struct.DocContent(tags={'id': '21'}, elements=[]),
            doc_struct.DocContent(tags={'id': '22'}, elements=[]),
            doc_struct.DocContent(tags={'id': '23'}, elements=[]),
            doc_struct.DocContent(tags={'id': '24'}, elements=[]),
        ],
        [
            doc_struct.DocContent(tags={'id': '31'}, elements=[]),
            doc_struct.DocContent(tags={'id': '32'}, elements=[]),
            doc_struct.DocContent(tags={'id': '33'}, elements=[]),
            doc_struct.DocContent(tags={'id': '34'}, elements=[]),
        ],
        [
            doc_struct.DocContent(tags={'id': '41'}, elements=[]),
            doc_struct.DocContent(tags={'id': '42'}, elements=[]),
            doc_struct.DocContent(tags={'id': '43'}, elements=[]),
            doc_struct.DocContent(tags={'id': '44'}, elements=[]),
        ],
    ],
)


class TestEvaluators(unittest.TestCase):
    """Test the evaluator classes."""

    # Used as path and as elements for NESTED_PATH.
    PATH = [
        doc_struct.ParagraphElement(tags={'id': '1'}),
        doc_struct.ParagraphElement(tags={'id': '2'}),
        doc_struct.ParagraphElement(tags={'id': '3'}),
        doc_struct.ParagraphElement(tags={'id': '4'}),
    ]

    # Simple, 2 level strcuture to use for position evaluators.
    NESTED_PATH = [
        doc_struct.Paragraph(elements=PATH),
        PATH[2],
    ]

    # Inner elements of a vertical structure.
    ELEMENTS_VERTICAL = [
        doc_struct.Paragraph(tags={'id': '1'}, elements=[]),
        doc_struct.Paragraph(tags={'id': '2'}, elements=[]),
        doc_struct.Paragraph(tags={'id': '3'}, elements=[]),
        doc_struct.Paragraph(tags={'id': '4'}, elements=[]),
    ]

    # Vertical structure for position tests.
    NESTED_VERTICAL = doc_struct.DocContent(elements=ELEMENTS_VERTICAL)

    def test_ancestor_path(self):
        """Test the generation of a path from ancestors."""
        evaluator = tags_relation.AncestorPathEvaluator(
            level_value='{0.tags[id]}')
        self.assertEqual('1/2/3', evaluator.get_value(self.PATH[-1],
                                                      self.PATH))
        self.assertEqual('1', evaluator.get_value(self.PATH[-1],
                                                  self.PATH[0:2]))
        self.assertEqual('', evaluator.get_value(self.PATH[-1],
                                                 self.PATH[0:1]))

    def test_ancestor_separator_and_value(self):
        """Test custom value and separator for path generation."""
        evaluator = tags_relation.AncestorPathEvaluator(
            level_value='X{0.tags[id]}Y', separator=':')
        self.assertEqual('X1Y:X2Y',
                         evaluator.get_value(self.PATH[-1], self.PATH[:3]))

    def test_ancestor_path_range(self):
        """Test start and end for paths."""
        evaluator = tags_relation.AncestorPathEvaluator(
            level_value='{0.tags[id]}', level_start=1)
        self.assertEqual('2/3', evaluator.get_value(self.PATH[-1], self.PATH))

        evaluator = tags_relation.AncestorPathEvaluator(
            level_value='{0.tags[id]}', level_end=2)
        self.assertEqual('1/2', evaluator.get_value(self.PATH[-1], self.PATH))

        evaluator = tags_relation.AncestorPathEvaluator(
            level_value='{0.tags[id]}', level_start=1, level_end=2)
        self.assertEqual('2', evaluator.get_value(self.PATH[-1], self.PATH))

        evaluator = tags_relation.AncestorPathEvaluator(
            level_value='{0.tags[id]}', level_start=1, level_end=1)
        self.assertEqual('', evaluator.get_value(self.PATH[-1], self.PATH))

    @parameterized.expand([  # type:ignore
        (
            tags_relation.RelativePositionConfig(col='first'),
            '1',
        ),
        (
            tags_relation.RelativePositionConfig(col='last'),
            '4',
        ),
        (
            tags_relation.RelativePositionConfig(col='prev'),
            '2',
        ),
        (
            tags_relation.RelativePositionConfig(col='next'),
            '4',
        ),
        (
            tags_relation.RelativePositionConfig(row='next'),
            None,
        ),
    ])
    def test_relative_position_horizontal(
            self, rel_pos: tags_relation.RelativePositionConfig,
            expected: Optional[str]):
        """Test horizontal relative positioning."""
        evaluator = tags_relation.RelativePositionEvaluator(element_at=rel_pos)
        result: Optional[doc_struct.Element] = evaluator.get_value(
            self.PATH[2], self.NESTED_PATH)
        result_tag = result.tags['id'] if result is not None else None
        self.assertEqual(expected, result_tag)

    @parameterized.expand([  # type:ignore
        (
            tags_relation.RelativePositionConfig(),
            '4',
        ),
        (
            tags_relation.RelativePositionConfig(row='first'),
            '1',
        ),
        (
            tags_relation.RelativePositionConfig(row='last'),
            '4',
        ),
        (
            tags_relation.RelativePositionConfig(row='prev'),
            '3',
        ),
        (
            tags_relation.RelativePositionConfig(row='next'),
            None,
        ),
    ])
    def test_relative_position_vertical(
            self, rel_pos: tags_relation.RelativePositionConfig,
            expected: Optional[str]):
        """Test vertical relative positioning."""
        evaluator = tags_relation.RelativePositionEvaluator(element_at=rel_pos)
        result: Optional[doc_struct.Element] = evaluator.get_value(
            self.ELEMENTS_VERTICAL[3],
            [self.NESTED_VERTICAL, self.ELEMENTS_VERTICAL[3]])
        result_tag = result.tags['id'] if result is not None else None
        self.assertEqual(expected, result_tag)

    @parameterized.expand([  # type:ignore
        (
            tags_relation.RelativePositionConfig(),
            '43',
        ),
        (
            tags_relation.RelativePositionConfig(row='first'),
            '13',
        ),
        (
            tags_relation.RelativePositionConfig(col='first'),
            '41',
        ),
        (
            tags_relation.RelativePositionConfig(row='first', col='first'),
            '11',
        ),
        (
            tags_relation.RelativePositionConfig(row='last', col='first'),
            '41',
        ),
        (
            tags_relation.RelativePositionConfig(row='prev', col='next'),
            '34',
        ),
        (
            tags_relation.RelativePositionConfig(row='next', col='prev'),
            None,
        ),
    ])
    def test_relative_position_2d(
            self, rel_pos: tags_relation.RelativePositionConfig,
            expected: Optional[str]):
        """Test 2d relative positioning."""
        evaluator = tags_relation.RelativePositionEvaluator(element_at=rel_pos)
        result: Optional[doc_struct.Element] = evaluator.get_value(
            TABLE2.elements[3][2], [TABLE2, TABLE2.elements[3][2]])
        result_tag = result.tags['id'] if result is not None else None
        self.assertEqual(expected, result_tag)

    def test_text_aggregator(self):
        """Test text aggregation."""
        data = doc_struct.Paragraph(tags={'id': '111'},
                                    elements=[
                                        doc_struct.TextRun(text='text1'),
                                        doc_struct.TextRun(text='text2'),
                                    ])
        evaluator = tags_relation.TextAggregationEvaluator()
        self.assertEqual('text1text2', evaluator.get_value(data, []))

    def test_text_aggregator_with_regex(self):
        """Test text aggregation and perform regex substitute after."""
        data = doc_struct.Paragraph(tags={'id': '111'},
                                    elements=[
                                        doc_struct.TextRun(text='text1'),
                                        doc_struct.TextRun(text='text2'),
                                    ])
        evaluator = tags_relation.TextAggregationEvaluator(substitutions=[
            tags_basic.RegexReplaceRule(
                regex=tags_basic.StringMatcher(r'(\d)'), substitute=r'_\1_')
        ])
        self.assertEqual('text_1_text_2_', evaluator.get_value(data, []))


class TestRelativeTaggingTransform(unittest.TestCase):
    """Test the full transform for relative tagging."""

    @parameterized.expand([  # type: ignore
        (
            'no var',
            '33',
            '_{0.tags[id]}_',
            {},
            [('33', '_33_')],
        ),
        (
            'no move var',
            '43',
            '_{v.tags[id]}_',
            {
                'v':
                    tags_relation.RelativePositionEvaluator(
                        element_at=tags_relation.RelativePositionConfig()),
            },
            [('43', '_43_')],
        ),
        (
            'tl move var',
            '43',
            '_{v.tags[id]}_',
            {
                'v':
                    tags_relation.RelativePositionEvaluator(
                        element_at=tags_relation.RelativePositionConfig(
                            col='first', row='first')),
            },
            [('43', '_11_')],
        ),
        (
            'move to none var',
            '43',
            '_{v.tags[id]}_',
            {
                'v':
                    tags_relation.RelativePositionEvaluator(
                        element_at=tags_relation.RelativePositionConfig(
                            row='next')),
            },
            [],
        ),
        (
            'multiple var',
            '33',
            '_{v1.tags[id]}_{v2.tags[id]}_',
            {
                'v1':
                    tags_relation.RelativePositionEvaluator(
                        element_at=tags_relation.RelativePositionConfig(
                            row='prev')),
                'v2':
                    tags_relation.RelativePositionEvaluator(
                        element_at=tags_relation.RelativePositionConfig(
                            row='next')),
            },
            [('33', '_23_43_')],
        ),
        (
            'ancestor path var',
            '33',
            '_{v}_',
            {
                'v':
                    tags_relation.AncestorPathEvaluator(
                        level_value='>{0.tags[id]}<'),
            },
            [('33', '_>0<_')],
        ),
        (
            'ancestor path var empty',
            '33',
            '_{v}_',
            {
                'v':
                    tags_relation.AncestorPathEvaluator(
                        level_value='>{0.tags[id]}<', level_start=2),
            },
            [('33', '__')],
        ),
    ])
    # pylint: disable=unused-argument
    def test_transform(
        self,
        name: str,
        pattern: str,
        template: str,
        variables: Mapping[str, Any],
        expected: Sequence[Tuple[str, str]],
    ):
        """Execute the transformation for various configs."""
        config = tags_relation.RelativeTaggingConfig(
            match_element=tags_relation.PositionMatchConfig(required_tag_sets=[
                tags_basic.MappingMatcher(id=tags_basic.StringMatcher(pattern))
            ]),
            tags=tags_basic.TagUpdateConfig(
                add={'x': template},
                ignore_errors=True,
            ),
            variables=variables)
        transform = tags_basic.TaggingTransform(config)

        result = cast(doc_struct.Table, transform(TABLE2))

        added_tags = [(element.tags['id'], element.tags.get('x'))
                      for row in result.elements
                      for element in row
                      if 'x' in element.tags]

        self.assertEqual(expected, added_tags)
