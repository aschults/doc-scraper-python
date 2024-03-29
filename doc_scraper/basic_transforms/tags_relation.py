"""Common classes for working with tags."""

from typing import (
    Optional,
    Sequence,
    Tuple,
    Protocol,
    TypeVar,
    Generic,
    Iterable,
    Literal,
    Any,
    Mapping,
    List,
    Union,
)
import dataclasses
from abc import abstractmethod, ABC

from doc_scraper import doc_struct
from doc_scraper.basic_transforms import tags_basic
from doc_scraper import help_docs
from doc_scraper import json_query

# 1d or 2d coordinates used to identify elements.
CoordinatesType = None | int | Tuple[int, int]

# Parent type for generics. Represents all one-dimensional cases.
_P = TypeVar('_P', doc_struct.Paragraph | doc_struct.TextLine,
             doc_struct.DocContent | doc_struct.Section)


class CoordinateGrid(Protocol):
    """Interface for a Coordinate grid, 1d and 2d case."""

    @abstractmethod
    def find(self, element: doc_struct.Element) -> Optional[CoordinatesType]:
        """Find the passed element and return it's coordinates.

        Returns:
            1d (int) or 2d (tuple of 2 int) coordinates or None if not found.
        """

    @abstractmethod
    def is_position_matching(self, element: doc_struct.Element,
                             pos_range: 'PositionMatchConfig') -> bool:
        """Check if an element is within a specified range.

        Args:
            element: Element to be checked.
            pos_range: Range to constrain the wanted positions.

        Returns:
            True if the element could be found in the underlying grid data
            and was within the specified range.
        """

    def get(self, coords: CoordinatesType) -> Optional[doc_struct.Element]:
        """Retreive an element by coordinates.

        Returns:
            Element or None if the coordinates don't point to an actual
            element (wrong dimensionality, outside bounds)
        """

    def get_relative(
            self, coords: CoordinatesType, relative: 'RelativePositionConfig'
    ) -> Optional[doc_struct.Element]:
        """Get an element based on the relative position to coordinates."""


# Positions relative to the current element to address.
RelativePositionMode = Literal['first', 'prev', 'next', 'last']


def is_in_range(
    coords: Optional[int],
    start: Optional[int],
    end: Optional[int],
    length: Optional[int],
) -> bool:
    """Check if 1d coordinates are within a range.

    Assumes a container with specific `length` is underlying, to allow
    indexes to be negative (to address from the container end) or None
    (to make the range unbounded).

    Args:
        coords: Coordinate/Index to check against the range.
        start: Start index.
        end: End index (not included in range)
        length: Length of the underlying container.

    Returns:
        True if index is in the range (between `start` and `end` for regular
        cases).
    """
    if not length:
        return False
    if length < 0:
        raise ValueError('length needs to be positive')

    if coords is None:
        return False

    if start is None:
        start = 0
    elif start < 0:
        start += length

    if end is None:
        end = length
    elif end < 0:
        end += length

    if end <= start:
        return False

    return coords >= start and coords < end


def calc_relative_index(
        index: int, length: int,
        relative_pos: Optional[RelativePositionMode]) -> Optional[int]:
    """Determine the index of a relative position.

    Args:
        index: Index of the current element.
        length: Length of the container.
        relative_pos: Indicator of the relative position to find.

    Returns:
        Index of the element with relative position indicated in
        relative_pos.
    """
    if relative_pos is None:
        return index

    if relative_pos == 'first':
        return 0
    if relative_pos == 'last':
        return length - 1

    if relative_pos == 'prev':
        if index == 0:
            return None
        else:
            return index - 1
    if relative_pos == 'next':
        if index + 1 == length:
            return None
        return index + 1

    raise ValueError(f'unexpected relative move {relative_pos}')


class _1DGridWrapper(CoordinateGrid, Generic[_P], ABC):
    """Abstract base of a 1D coordinate grid, vertical or horizontal.

    Wraps an existing Element to make its children accessible through
    a coordinate grid.
    """

    def __init__(self, element: _P) -> None:
        """Create an instane."""
        self.parent = element

    @property
    @abstractmethod
    def _children(self) -> Sequence[doc_struct.Element]:
        """Get the children of the wrapped element."""
        raise NotImplementedError('override')

    def get(self, coords: CoordinatesType) -> Optional[doc_struct.Element]:
        """Retreive for 1D cases."""
        if coords is None:
            return None
        if isinstance(coords, tuple):
            return None
        return self._children[coords]

    def find(self, element: doc_struct.Element) -> Optional[CoordinatesType]:
        """Find an element and return its coordinates."""
        if not self._children:
            # No children, no coords.
            return None

        return self._find_one_dimension(element)

    def _find_one_dimension(self,
                            element: doc_struct.Element) -> Optional[int]:
        """Perform one-dimensional search for the element."""
        for index, element2 in enumerate(self._children):
            if id(element) == id(element2):
                return index
        return None

    @abstractmethod
    def is_position_matching(self, element: doc_struct.Element,
                             pos_range: 'PositionMatchConfig') -> bool:
        """Check if the element is part of the supplied position range."""
        raise NotImplementedError('override')


class _1DVerticalGridWrapper(_1DGridWrapper[doc_struct.DocContent |
                                            doc_struct.Section]):
    """Vertical 1d grid, for Doc Content and Sections."""

    @property
    def _children(self) -> Sequence[doc_struct.StructuralElement]:
        if isinstance(self.parent, doc_struct.Section):
            return self.parent.content
        return self.parent.elements

    def is_position_matching(self, element: doc_struct.Element,
                             pos_range: 'PositionMatchConfig') -> bool:
        """Check if the element is part of the supplied position range."""
        if pos_range.start_col is not None or pos_range.end_col is not None:
            return False

        coords = self._find_one_dimension(element)
        return is_in_range(coords, pos_range.start_row, pos_range.end_row,
                           len(self._children))

    def get_relative(
            self, coords: CoordinatesType, relative: 'RelativePositionConfig'
    ) -> Optional[doc_struct.Element]:
        if relative.col is not None:
            return None
        if not isinstance(coords, int):
            return None
        index = calc_relative_index(coords, len(self._children), relative.row)
        return self.get(index)


class _1DParagraphGridWrapper(_1DGridWrapper[doc_struct.Paragraph |
                                             doc_struct.TextLine]):
    """Coordinate grid for flat paragraph elements.

    Supports when no intermediate TextLine exists to introduce a 2d
    structure, or when only working with TextLine elements, as 1d
    structure.
    """

    @property
    def _children(self) -> Sequence[doc_struct.ParagraphElement]:
        return self.parent.elements

    def is_position_matching(self, element: doc_struct.Element,
                             pos_range: 'PositionMatchConfig') -> bool:
        """Check if element is inside the position range."""
        if pos_range.start_row is not None or pos_range.end_row is not None:
            return False

        coords = self._find_one_dimension(element)
        return is_in_range(coords, pos_range.start_col, pos_range.end_col,
                           len(self._children))

    def get_relative(
            self, coords: CoordinatesType, relative: 'RelativePositionConfig'
    ) -> Optional[doc_struct.Element]:
        if relative.row is not None:
            return None
        if not isinstance(coords, int):
            return None
        index = calc_relative_index(coords, len(self._children), relative.col)
        return self.get(index)


# Parent type for generics. Represents all two-dimensional cases.
_T = TypeVar('_T', doc_struct.Paragraph, doc_struct.Table)


class _2DGridWrapper(CoordinateGrid, Generic[_T], ABC):

    def __init__(self, element: _T) -> None:
        self.parent = element

    @abstractmethod
    def _get_children(self) -> Iterable[Iterable[doc_struct.Element]]:
        """Get children as iterable grid.

        Returns:
            Iterable of iterables, supporting table and paragraph parents.
        """
        raise NotImplementedError('override')

    def _find_in_table(
            self, element: doc_struct.Element) -> Optional[Tuple[int, int]]:
        """Perform two-dimensional search for the element."""
        for row_index, row in enumerate(self._get_children()):
            for col_index, element2 in enumerate(row):
                if id(element) == id(element2):
                    return (row_index, col_index)
        return None

    def find(self, element: doc_struct.Element) -> Optional[CoordinatesType]:
        """Find an element and return its coordinates."""
        if not self.parent.elements:
            # No children, no coords.
            return None

        return self._find_in_table(element)

    def is_position_matching(self, element: doc_struct.Element,
                             pos_range: 'PositionMatchConfig') -> bool:
        """Check if the element is part of the supplied position range."""
        coords = self._find_in_table(element)
        if coords is None:
            return False

        table = list(self._get_children())
        rows = len(table)

        if not is_in_range(coords[0], pos_range.start_row, pos_range.end_row,
                           rows):
            return False

        cols_at_row = len(list(table[coords[0]]))
        return is_in_range(coords[1], pos_range.start_col, pos_range.end_col,
                           cols_at_row)

    def get(self, coords: CoordinatesType) -> Optional[doc_struct.Element]:
        """Retreive element for 2D cases."""
        if coords is None:
            return None
        if not isinstance(coords, tuple):
            return None
        table = list(self._get_children())
        row = list(table[coords[0]])
        return row[coords[1]]

    def get_relative(
            self, coords: CoordinatesType, relative: 'RelativePositionConfig'
    ) -> Optional[doc_struct.Element]:
        if not isinstance(coords, tuple):
            return None
        children = list(self._get_children())
        row_index = calc_relative_index(coords[0], len(children), relative.row)
        row = list(children[coords[0]])
        col_index = calc_relative_index(coords[1], len(row), relative.col)

        if row_index is None or col_index is None:
            return None

        return self.get((row_index, col_index))


class _2DParagraphGridWrapper(_2DGridWrapper[doc_struct.Paragraph]):
    """Grid wrapper for Paragraph elements.

    Expects TextLine children to build 2d text structure.
    """

    def _get_children(self) -> Iterable[Iterable[doc_struct.Element]]:
        """Turn paragraph of text line of elements into 2d array."""
        for row in self.parent.elements:
            if isinstance(row, doc_struct.TextLine):
                yield row.elements
            else:
                yield [row]


class _TableGridWrapper(_2DGridWrapper[doc_struct.Table]):
    """Grid wrapper for Table elements."""

    def _get_children(self) -> Iterable[Iterable[doc_struct.Element]]:
        return self.parent.elements


def _coord_grid_from_paragraph_element_child(
        path: Sequence[doc_struct.Element]) -> CoordinateGrid:
    """Handle coordinate grid creation for all paragraph element cases."""
    parent = path[-2]

    if isinstance(parent, doc_struct.TextLine):
        if len(path) < 3:
            return _1DParagraphGridWrapper(parent)
        else:
            grandparent = path[-3]
            if not isinstance(grandparent, doc_struct.Paragraph):
                raise ValueError(f'Bad parent type: {grandparent}')
            return _2DParagraphGridWrapper(grandparent)
    elif isinstance(parent, doc_struct.Paragraph):
        return _1DParagraphGridWrapper(parent)
    else:
        raise ValueError(f'Bad parent type: {parent} for child {path[-1]}')


def coord_grid_from_parent(parent: doc_struct.Element) -> CoordinateGrid:
    """Create a coordinate grid from for a parent.

    Args:
        parent: Coordinate grid is created for this object.

    Returns:
        Coordinate grid
    """
    if isinstance(parent, doc_struct.TextLine):
        return _1DParagraphGridWrapper(parent)
    elif isinstance(parent, doc_struct.Paragraph):
        if parent.elements and isinstance(parent.elements[0],
                                          doc_struct.TextLine):
            return _2DParagraphGridWrapper(parent)
        else:
            return _1DParagraphGridWrapper(parent)
    elif isinstance(parent, (doc_struct.DocContent, doc_struct.Section)):
        return _1DVerticalGridWrapper(parent)
    elif isinstance(parent, doc_struct.Table):
        return _TableGridWrapper(parent)
    else:
        raise ValueError(f'No grid for {parent}')


def coord_grid_from_child(
        path: Sequence[doc_struct.Element]) -> Optional[CoordinateGrid]:
    """Create a coordinate grid based on a path to the child element.

    Args:
        path: Object path to the child element of the grid.

    Returns:
        Coordinate grid containing the element specidied in the path
        or None if the coordinate could not be created.
    """
    if len(path) < 2:
        return None

    element = path[-1]
    parent = path[-2]

    if isinstance(element, doc_struct.ParagraphElement):
        return _coord_grid_from_paragraph_element_child(path)
    elif isinstance(element, doc_struct.StructuralElement):
        if isinstance(parent, doc_struct.Section):
            if parent.heading == element:
                # We arrived from the heading side, not content.
                return None
            return _1DVerticalGridWrapper(parent)
        if isinstance(parent, doc_struct.DocContent):
            return _1DVerticalGridWrapper(parent)
    elif isinstance(element, doc_struct.DocContent):
        if isinstance(parent, doc_struct.Table):
            return _TableGridWrapper(parent)
    return None


@dataclasses.dataclass(kw_only=True)
class PositionMatchConfig(tags_basic.TagMatchConfig):
    """Extended TagMatchConfig, supporting positional matches."""

    start_col: int | None = dataclasses.field(
        default=None,
        metadata={
            'help_text':
                'Horitzontal start of matched elements. Unbound if not set.',
            'help_samples': [
                ('From first col', 0),
                ('Last column', -1),
            ]
        })

    end_col: int | None = dataclasses.field(
        default=None,
        metadata={
            'help_text':
                'Horitzontal end of matched elements. Unbound if not set.',
            'help_samples': [
                ('Until 3rd col', 4),
                ('First column', 1),
            ]
        })

    start_row: int | None = dataclasses.field(
        default=None,
        metadata={
            'help_text':
                'Vertical start of matched elements. Unbound if not set.',
            'help_samples': [
                ('From first row', 0),
                ('Last row', -1),
            ]
        })

    end_row: int | None = dataclasses.field(
        default=None,
        metadata={
            'help_text':
                'Vertical end of matched elements. Unbound if not set.',
            'help_samples': [
                ('Until 3rd row', 4),
                ('First row', 1),
            ]
        })

    def _is_position_match(
            self, element: doc_struct.Element,
            path: Sequence[doc_struct.Element]) -> CoordinatesType:
        """Handle all cases of positioning elements in their parents.

        * Text Line in Paragraph (vertical)
        * Paragraph Element in Paragraph (horizontal)
        * Paragraph Element in Text Line in Paragraph (2D)
        * Structural Element in Doc Content or Section (vertical)
        * Doc Content in Table (2D)
        """
        coords = (self.start_col, self.end_col, self.start_row, self.end_row)
        if all(item is None for item in coords):
            return True
        if not path:
            raise ValueError('Expecting path to be non-empty')

        coord_grid = coord_grid_from_child(path)

        if coord_grid is None:
            return False

        return coord_grid.is_position_matching(element, self)

    def is_matching(
            self,
            element: doc_struct.Element,
            path: Optional[Sequence[doc_struct.Element]] = None) -> bool:
        """Match elements, including position matching."""
        if not path:
            raise ValueError('expecting path to be set')

        if not self._is_position_match(element, path):
            return False
        return super().is_matching(element, path)


SkipModeType = Literal['any', 'exactly', 'at_least']


@dataclasses.dataclass(kw_only=True)
class MatchListGapConfig():
    """Placed in match_ancestor_list to mark gaps."""

    skip_ancestors: SkipModeType = dataclasses.field(  # type:ignore
        metadata={
            'help_text':
                'Mode for skipping ancestors at this point in the list.',
            'help_samples': [
                ('Require exactly skip_count ancestor in between', 'exactly'),
                ('Allow skip_count or more ancestors in between', 'at_least'),
                ('Allow any number of ancestors in between', 'any'),
            ],
        })

    skip_count: int = dataclasses.field(
        default=0,
        metadata={
            'help_text': 'Number of ancestors to skip (depending on mode).',
            'help_samples': [1],
        })

    def __post_init__(self):
        """Validate that parameters passed are correct."""
        if self.skip_ancestors != 'any':
            if self.skip_count == 0:
                raise ValueError('Need to have non-zero skip_count')
        else:
            if self.skip_count != 0:
                raise ValueError('No skip count for "any" mode')

        if self.skip_count < 0:
            raise ValueError('Positive skip_count only')

    @property
    def is_open_length(self) -> bool:
        """Return True if the gap can extend indefinitely."""
        return self.skip_ancestors in ('any', 'at_least')

    def merge(self, other: 'MatchListGapConfig') -> 'MatchListGapConfig':
        """Merge two gaps."""
        num_items = self.skip_count + other.skip_count
        if num_items == 0:
            mode = 'any'
        elif self.is_open_length or other.is_open_length:
            mode = 'at_least'
        else:
            mode = 'exactly'
        return MatchListGapConfig(skip_ancestors=mode, skip_count=num_items)


@dataclasses.dataclass(kw_only=True)
class RelationalMatchingConfig():
    """Describe matching and tagging criteria including inter-element."""

    match_element: PositionMatchConfig = dataclasses.field(
        default_factory=PositionMatchConfig,
        metadata={
            'help_text': 'Criteria to match elements for tagging.',
            'help_samples': [help_docs.ClassBasedSample(PositionMatchConfig)],
        })

    match_ancestor_list: Sequence[
        MatchListGapConfig | PositionMatchConfig] = dataclasses.field(
            default_factory=list,
            metadata={
                'help_text':
                    'List of criteria to match along the ancestors path',
                'help_samples': [[
                    help_docs.ClassBasedSample(tags_basic.TagMatchConfig),
                    help_docs.ClassBasedSample(MatchListGapConfig),
                ]],
            })

    match_descendent: Optional[tags_basic.TagMatchConfig] = dataclasses.field(
        default=None,
        metadata={
            'help_text':
                'Criteria to match any descendent of the current element.',
            'help_samples': [
                help_docs.ClassBasedSample(tags_basic.TagMatchConfig)
            ],
        })

    def _canonicalize_ancestor_matches(
            self) -> List[PositionMatchConfig | MatchListGapConfig]:
        """Clean up the ancestor match list by merging gaps."""
        result: List[PositionMatchConfig | MatchListGapConfig] = []
        last_item: Optional[MatchListGapConfig] = None
        for matcher in self.match_ancestor_list:
            if isinstance(matcher, MatchListGapConfig):
                if last_item:
                    last_item = last_item.merge(matcher)
                else:
                    last_item = matcher
            else:
                if last_item:
                    result.append(last_item)
                last_item = None
                result.append(matcher)
        if last_item:
            result.append(last_item)
        return result

    @classmethod
    # flake8: noqa
    def _is_ancestor_subpaths_matching(
        cls,
        match_list_: Sequence[PositionMatchConfig | MatchListGapConfig],
        path_list_: Sequence[doc_struct.Element],
    ) -> bool:
        """Match the front part of the ancestor match list."""
        if not match_list_:
            return len(path_list_) == 0

        if not path_list_:
            return all(
                isinstance(item, MatchListGapConfig) and
                item.skip_ancestors == 'any' for item in match_list_)

        match_list = list(match_list_)
        path_list = list(path_list_)

        while match_list:
            matcher = match_list.pop()
            if isinstance(matcher, MatchListGapConfig):
                if matcher.skip_count > 0:
                    for _ in range(abs(matcher.skip_count)):
                        if not path_list:
                            return False
                        path_list.pop()
                if matcher.is_open_length:
                    while path_list:
                        if cls._is_ancestor_subpaths_matching(
                                match_list, path_list):
                            return True
                        path_list.pop()
            else:
                if not path_list:
                    return False
                ancestor = path_list[-1]
                if not matcher.is_matching(ancestor, path_list):
                    return False
                path_list.pop()

        return len(path_list) == 0

    def _is_ancestor_matching(self,
                              path: Sequence[doc_struct.Element]) -> bool:
        if not self.match_ancestor_list:
            return True

        if not path:
            raise ValueError('Expecting at lteast on item on ancestor path')
        path_list = list(path[:-1])  # Exclude current element
        match_list2 = self._canonicalize_ancestor_matches()

        return self._is_ancestor_subpaths_matching(match_list2, path_list)

    def _are_descendents_matching(self, element: doc_struct.Element) -> bool:
        if not self.match_descendent:
            return True

        def _filter_func(element2: doc_struct.Element) -> bool:
            if not self.match_descendent:
                return True
            return self.match_descendent.is_matching(element2, [])

        filter_converter = tags_basic.ElementFilterConverter(_filter_func)

        matching_items = [
            item for item in filter_converter.convert(element) or []
            if id(item) != id(element)
        ]
        if not matching_items:
            # No descendent matched the criteria.
            return False
        return True

    def is_matching(
            self,
            element: doc_struct.Element,
            path: Optional[Sequence[doc_struct.Element]] = None) -> bool:
        """Match elements, including ancestor and descenent match."""
        if not path:
            raise ValueError('expecting path to be set')

        if not self._is_ancestor_matching(path):
            return False

        if not self._are_descendents_matching(element):
            return False

        if not self.match_element.is_matching(element, path):
            return False

        return True


class Evaluator(Protocol):
    """Interface to evaluate a variable's value from current element."""

    @abstractmethod
    def get_value(self, element: doc_struct.Element,
                  path: Optional[Sequence[doc_struct.Element]]) -> Any:
        """Get the value by evaluating this instance.

        Args:
            element: Current element to be used for the evaluation.
            path: Full ancestor path to be used for the evaluation.

        Returns:
            Any data type.
        """


@dataclasses.dataclass(kw_only=True)
class RelativePositionConfig():
    """Retreive an element with relative position to the current one."""

    col: Optional[RelativePositionMode] = dataclasses.field(
        default=None,
        metadata={
            'help_text':
                'Horizontal relative position of the element.',
            'help_samples': [
                ('', help_docs.RawSample('first # others: last, prev, next')),
            ]
        })
    row: Optional[RelativePositionMode] = dataclasses.field(
        default=None,
        metadata={
            'help_text':
                'Vertical relative position of the element.',
            'help_samples': [
                ('', help_docs.RawSample('first # others: last, prev, next')),
            ]
        })


@dataclasses.dataclass(kw_only=True)
class RelativePositionEvaluator(Evaluator):
    """Retrieve an element as value, relative to current element."""

    element_at: RelativePositionConfig = dataclasses.field(
        metadata={
            'help_text':
                'Relative position at which to get the element.',
            'help_samples':
                [help_docs.ClassBasedSample(RelativePositionConfig)],
        })

    def get_value(self, element: doc_struct.Element,
                  path: Optional[Sequence[doc_struct.Element]]) -> Any:
        """Fetch the element from the specified position."""
        if not path:
            raise ValueError('need path and elements in path')

        grid = coord_grid_from_child(path)
        if grid is None:
            return None

        coords = grid.find(element)
        if not coords:
            return None

        return grid.get_relative(coords, self.element_at)


@dataclasses.dataclass(kw_only=True)
class AncestorPathEvaluator(Evaluator):
    """Get the current element's ancestors as string.

    Interpolates the level_value for each ancestor and
    join it in path-like form by separator.
    """

    level_value: str = dataclasses.field(
        metadata={
            'help_text':
                'Template to use to render each level\'s value.',
            'help_samples': [('tag "heading" of each level',
                              '0.tags[heading]')],
        })

    separator: str = dataclasses.field(
        default='/',
        metadata={'help_text': 'Separator between each level_value'})
    level_start: Optional[int] = dataclasses.field(
        default=None,
        metadata={
            'help_text':
                'Level starting from 0 at the root to start the path.',
            'help_samples': [('start at the 2nd level', 1)],
        })
    level_end: Optional[int] = dataclasses.field(
        default=None,
        metadata={
            'help_text': 'Level starting from 0 at the root to end the path.',
            'help_samples': [('exclude level 3 and below', 2)],
        })

    def get_value(self, element: doc_struct.Element,
                  path: Optional[Sequence[doc_struct.Element]]) -> Any:
        """Calculate the path and return it."""
        if not path:
            raise ValueError('need path and elements in path')

        path = path[:-1]
        path = path[self.level_start:self.level_end]

        return self.separator.join(
            (self.level_value.format(element) for element in path))


@dataclasses.dataclass(kw_only=True)
class TextAggregationEvaluator(Evaluator, tags_basic.RegexReplacer):
    """Get aggregated text from an element and its descendents."""

    aggregation_mode: Literal['raw'] = dataclasses.field(
        default='raw',
        metadata={
            'help_text': 'Text extraction mode.',
            'help_samples': [('Default and only avaiable', 'raw')],
        })

    section_heading_only: bool = dataclasses.field(
        default=False,
        metadata={
            'help_text': 'For Section element, only collect heading.',
            'help_samples': [('Default', False)],
        })

    def get_value(self, element: doc_struct.Element,
                  path: Optional[Sequence[doc_struct.Element]]) -> Any:
        """Provide the aggregated text for interpolation."""
        _text_converter = doc_struct.RawTextConverter()
        if self.section_heading_only and isinstance(element,
                                                    doc_struct.Section):
            agg_text = _text_converter.convert(element.heading)
        else:
            agg_text = _text_converter.convert(element)
        if agg_text is None:
            return None
        return self.transform_text(agg_text)


@dataclasses.dataclass(kw_only=True)
class JsonQueryEvaluator(Evaluator):
    """Evaluate JSON query."""

    def __post_init__(self):
        """Compile the query after construction."""
        self._query_prog = json_query.Query(self.json_query,
                                            var_names=['root'])
        self._root_element: Optional[doc_struct.Element] = None

    json_query: str = dataclasses.field(
        metadata={
            'help_text': 'JSON query to evaluate',
            'help_samples': [('Merge all text', '[..|.text?] |join("")')],
        })

    def get_value(self, element: doc_struct.Element,
                  path: Optional[Sequence[doc_struct.Element]]) -> Any:
        """Evaluate the JSON query.."""
        if not path:
            raise ValueError('Need path for evaluator')

        result = self._query_prog.get_first(doc_struct.as_dict(element),
                                            root=doc_struct.as_dict(path[0]))
        if not json_query.is_output(result):
            return None
        return result


# All evaluators as Union so Dacite can pick up on them.
# Note: Dacite does currently not support creating subclases when
#       a field is of type base class.
EvaluatorsType = Union[RelativePositionEvaluator, AncestorPathEvaluator,
                       TextAggregationEvaluator, JsonQueryEvaluator]


@dataclasses.dataclass(kw_only=True)
class RelativeTaggingConfig(
        RelationalMatchingConfig,
        tags_basic.TaggingConfig,
        tags_basic.TaggingTransformConfigProtocol,
):
    """Match and tag elements, including variables for interpolation."""

    variables: Mapping[str, EvaluatorsType] = dataclasses.field(
        default_factory=lambda: {},
        metadata={
            'help_text':
                'Variables to provide for the interpolation of tags.',
            'help_samples': [{
                'ancestor_path':
                    help_docs.ClassBasedSample(AncestorPathEvaluator),
                'related_element':
                    help_docs.ClassBasedSample(RelativePositionEvaluator),
                'text_aggregation':
                    help_docs.ClassBasedSample(TextAggregationEvaluator),
                'json_eval':
                    help_docs.ClassBasedSample(JsonQueryEvaluator),
            }],
        })

    def get_variables(
            self,
            element: doc_struct.Element,
            path: Sequence[doc_struct.Element] | None = None
    ) -> Mapping[str, Any]:
        """Gather variables and values from all evaluators."""
        return {
            name: variable.get_value(element, path)
            for name, variable in self.variables.items()
        }
