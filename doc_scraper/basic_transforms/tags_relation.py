"""Common classes for working with tags."""

from typing import Optional, Sequence
import dataclasses

from doc_scraper import doc_struct
from doc_scraper.basic_transforms import tags_basic


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

    def _check_table(self, element: doc_struct.DocContent,
                     parent: doc_struct.Table) -> bool:
        """Check table if `element` is in the range specified in self."""
        for row in parent.elements[self.start_row:self.end_row]:
            if element in row[self.start_col:self.end_col]:
                return True
        return False

    def _check_vertical(self, element: doc_struct.TextLine,
                        parent: doc_struct.Paragraph) -> bool:
        """Check text line if `element` is in the range specified in self."""
        return element in parent.elements[self.start_row:self.end_row]

    def _check_horizontal(
            self, element: doc_struct.ParagraphElement,
            parent: doc_struct.TextLine | doc_struct.Paragraph) -> bool:
        """Check par element if `element` is in the range specified in self."""
        return element in parent.elements[self.start_col:self.end_col]

    def _handle_doc_content(self, element: doc_struct.DocContent,
                            path: Sequence[doc_struct.Element]) -> bool:
        """Determine if a doc content element matches within a table.

        Considered a 2D structure with both col and row to constrain.
        """
        if len(path) < 2:
            return False

        parent = path[-2]

        if not isinstance(parent, doc_struct.Table):
            return False

        return self._check_table(element, parent)

    def _handle_structural_element(self, element: doc_struct.StructuralElement,
                                   path: Sequence[doc_struct.Element]) -> bool:
        """Determine if a struct element matches in a doc content/section.

        Considered vertical position (row).
        """
        if len(path) < 2:
            return False

        if self.start_col is not None or self.end_col is not None:
            return False

        parent = path[-2]

        if isinstance(parent, doc_struct.DocContent):
            if element not in parent.elements[self.start_row:self.end_row]:
                return False
        elif isinstance(parent, doc_struct.Section):
            if element not in parent.content[self.start_row:self.end_row]:
                return False
        else:
            raise ValueError('Expected parent to be DocContent or Section')

        return True

    def _handle_par_element_text_line(
            self, element: doc_struct.ParagraphElement,
            parent: doc_struct.TextLine,
            grandparent: Optional[doc_struct.Element]) -> bool:
        """Handle position of par element in text line in paragraph.

        The position of the par element within the text line is
        considered as horizontal(col), the position of the text line
        is considered vertical(row) within the paragraph.
        """
        if not self._check_horizontal(element, parent):
            return False
        if grandparent:
            if isinstance(grandparent, doc_struct.Paragraph):
                if not self._check_vertical(parent, grandparent):
                    return False
            elif self.start_row is not None or self.end_row is not None:
                return False
        return True

    def _handle_text_line(self, element: doc_struct.TextLine,
                          path: Sequence[doc_struct.Element]) -> bool:
        """Determine if a text line matches within a paragraph.

        Only considers text lines, ignoring their content, thus
        considering the position vertical(row).
        """
        if len(path) < 2:
            return False
        parent = path[-2]
        if not isinstance(parent, doc_struct.Paragraph):
            raise ValueError(
                'Expecting text runs to be contained in paragraphs')
        if self.start_row is not None or self.end_row is not None:
            return False
        if not self._check_vertical(element, parent):
            return False

        return True

    def _handle_paragraph_element(self, element: doc_struct.ParagraphElement,
                                  path: Sequence[doc_struct.Element]) -> bool:
        """Determine if a par element matches within a paragraph.

        If paragraph elements are direct children of paragraphs, the
        text is considered flat, i.e. only horizontal (col).

        If a text line element is in between, the structure is considered
        2D.
        """
        if len(path) < 2:
            return False
        parent = path[-2]
        if isinstance(parent, doc_struct.TextLine):
            grandparent: Optional[doc_struct.Element] = None
            if len(path) >= 3:
                grandparent = path[-3]
            return self._handle_par_element_text_line(element, parent,
                                                      grandparent)
        elif isinstance(parent, doc_struct.Paragraph):
            if self.start_row is not None or self.end_row is not None:
                return False
            if not self._check_horizontal(element, parent):
                return False

        return True

    def _is_position_match(self, element: doc_struct.Element,
                           path: Sequence[doc_struct.Element]) -> bool:
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
        if isinstance(element, doc_struct.TextLine):
            return self._handle_text_line(element, path)
        if isinstance(element, doc_struct.ParagraphElement):
            return self._handle_paragraph_element(element, path)
        if isinstance(element, doc_struct.StructuralElement):
            return self._handle_structural_element(element, path)
        if isinstance(element, doc_struct.DocContent):
            return self._handle_doc_content(element, path)
        else:
            return False

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

        if not self.match_element.is_matching(element, path):
            return False

        if not self._is_ancestor_matching(path):
            return False

        if not self._are_descendents_matching(element):
            return False

        return True

    def update_tags(self, element: doc_struct.Element) -> doc_struct.Element:
        """Update the passed element with the speficied tags.

        Delegate to the config classes.
        """
        return self.tags.update_tags(element)
