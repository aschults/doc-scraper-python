"""Common classes for working with tags."""

from typing import (
    Optional,
    Sequence,
    Tuple,
    Protocol,
    TypeVar,
    Generic,
    Iterable,
    Any,
)
import dataclasses
from abc import abstractmethod, ABC

from doc_scraper import doc_struct
from doc_scraper.basic_transforms import tags_basic

# 1d or 2d coordinates used to identify elements.
CoordinatesType = None | int | Tuple[int, int]

# Parent type for generics. Represents all one-dimensional cases.
_P = TypeVar('_P', doc_struct.Paragraph | doc_struct.TextLine,
             doc_struct.DocContent | doc_struct.Section)


class CoordinateGrid(Protocol):
    """Interface for a Coordinate grid, 1d and 2d case."""

    def find(self, element: doc_struct.Element) -> Optional[CoordinatesType]:
        """Find the passed element and return it's coordinates.

        Returns:
            1d (int) or 2d (tuple of 2 int) coordinates or None if not found.
        """

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

        cols_at_row = len(list(table[coords[1]]))
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
        raise ValueError(f'Bad parent type: {parent}')


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
        if isinstance(parent, (doc_struct.DocContent, doc_struct.Section)):
            return _1DVerticalGridWrapper(parent)
    elif isinstance(element, doc_struct.DocContent):
        if isinstance(parent, doc_struct.Table):
            return _TableGridWrapper(parent)
    raise ValueError(f'Unexpected parent {parent} for child {element}')


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


@dataclasses.dataclass(kw_only=True)
class RelationalTaggingConfig(tags_basic.TaggingTransformConfigProtocol):
    """Describe matching and tagging criteria including inter-element."""

    match_element: PositionMatchConfig = dataclasses.field(
        default_factory=PositionMatchConfig,
        metadata={
            'help_text': 'Criteria to match elements for tagging.',
        })

    tags: tags_basic.TagUpdateConfig = dataclasses.field(metadata={
        'help_text': 'Updates for tags',
    })

    match_ancestor_list: Sequence[PositionMatchConfig] = dataclasses.field(
        default_factory=list,
        metadata={
            'help_text':
                'List of ordered criteria to match along the ancestors',
        })

    match_descendent: Optional[tags_basic.TagMatchConfig] = dataclasses.field(
        default=None,
        metadata={
            'help_text':
                'Criteria to match any descendent of the current element.',
        })

    def _is_ancestor_matching(self,
                              path: Sequence[doc_struct.Element]) -> bool:
        if not self.match_ancestor_list:
            return True

        if not path:
            raise ValueError('Expecting at lteast on item on ancestor path')
        path_list = list(path[:-1])  # Exclude current element
        if not path_list:
            return False

        for matcher in self.match_ancestor_list[::-1]:
            if not path_list:
                return False
            ancestor_matched = False
            while path_list:
                ancestor = path_list.pop()
                if matcher.is_matching(ancestor, path_list + [ancestor]):
                    ancestor_matched = True
                    break
            if not ancestor_matched:
                return False
        return True

    def _are_descendents_matching(self, element: doc_struct.Element) -> bool:
        if not self.match_descendent:
            return True

        def _filter_func(element2: doc_struct.Element) -> bool:
            if not self.match_descendent:
                return True
            return self.match_descendent.is_matching(element2, [])

        filter_converter = tags_basic.ElementFilterConverter(_filter_func)

        matching_items = [
            item for item in filter_converter.convert(element)
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

    def update_tags(self, element: doc_struct.Element,
                    **variables: Any) -> doc_struct.Element:
        """Update the passed element with the speficied tags.

        Delegate to the config classes.
        """
        return self.tags.update_tags(element, **variables)
