"""Base class to walk through document elements and transform them.

Implemented as visitor, recursing through all elements in a document,
allowing tor replace elements as they go.

Here the general concepts:

*   _Transformation_: Callable[[Element], Element]. Usually recursively
    descends into contained elements to modify values or structure.

*   _TransformationContext_: Class that keeps track of where the recursion
    currently is, in form of an object path and how the nested element was
    accessed, e.g. index in a list of elements, row/column for tables,...

*   `Transformation.transform_*()`: Functions that take a specific type of
    element, invididually or in containers, and transform them.

*   `Transformation.transform_*_base()`: Subclasses of elements in doc_struct
    should not only be transformed at the actual type of the element, but
    also along their chain of base classes. `transform_*_base()` functions
    achieve this, e.g. `transform_element_base()` is applied to *all* elements.
"""

import dataclasses
from typing import (Any, Callable, List, Optional, Sequence, Tuple, Type,
                    TypeVar, Union)

from doc_scraper import doc_struct

DocContent2dSequence = Sequence[Sequence[doc_struct.DocContent]]

TransformationFunction = Callable[[doc_struct.Element], doc_struct.Element]

# Type representing one path segmen, i.e. one step into the document structure.
PathType = Union[Tuple[int, int], int, str]

# Various types for generics
_T = TypeVar('_T')
_E = TypeVar('_E', bound=doc_struct.Element)
_I = TypeVar('_I', Tuple[int, int], int, str)
_R = TypeVar('_R')


def _skip_if_none(item_list: Sequence[Optional[_T]]) -> Sequence[_T]:
    """Skip None items in an array and change the type to non-optional."""
    return [item for item in item_list if item is not None]


def _safe_cast(obj: Any, cls: Type[_T]) -> _T:
    """Assert the type and cast to it."""
    if isinstance(obj, cls):
        return obj
    raise TypeError(f'Expected type {cls}, got {obj}')


class TransformationContext():
    """Context of an active transformation.

    Provides details on the path to the current item.
    """

    def __init__(self) -> None:
        """Create an instance."""
        self._path: List[PathType] = []
        self._objects: List[doc_struct.Element] = []
        self.data: Optional[doc_struct.SharedData] = None

    def add(self, element: doc_struct.Element, path_item: PathType) -> None:
        """Add a path segment and the latest object as a stack."""
        self._path.append(path_item)
        self._objects.append(element)

    def remove(self, expected_element: doc_struct.Element) -> None:
        """Remove top path stack item making sure we have the correct item."""
        removed_element = self._objects.pop()
        self._path.pop()
        if removed_element != expected_element:
            raise ValueError(
                f'Removed element {removed_element} does not match expected ' +
                f'{expected_element}\n Path:{self.path}')

    @property
    def raw_path(self) -> Sequence[PathType]:
        """Return the current path."""
        return self._path

    @property
    def path(self) -> Sequence[str]:
        """Return the current path as string."""
        result: List[str] = []
        for path_segment in self._path:
            if isinstance(path_segment, tuple):
                result.append(f'{path_segment[0]},{path_segment[1]}')
            else:
                result.append(str(path_segment))
        return result

    @property
    def path_objects(self) -> Sequence[doc_struct.Element]:
        """Return the current path."""
        return self._objects


class _TransformationBase():
    """Base class for all transformations.

    Transformations are set up in 2 phases. After construction neither context
    nor type specific transformations are available. By calling inject(), these
    are filled in with the passed values.
    """

    def __init__(self,
                 context: Optional[TransformationContext] = None) -> None:
        """Construct an instance."""
        if context is None:
            context = TransformationContext()
        self.context = context

    def _call_with_context(self, func: Callable[[_I, _E], _R], index: _I,
                           item: _E) -> _R:
        """Call the supplied function, ebsuring the conext is updated.

        Args:
            func: The function to call within the updated context.
            index: The path segment to add. Also passed to func,
            item: The item to be processed. Will be put to the top
                of the context stack.

        Returns:
            The return value of func
        """
        self.context.add(item, index)
        result = func(index, item)
        self.context.remove(item)
        return result

    def _transform_element_base(
            self, element: doc_struct.Element) -> doc_struct.Element:
        """Transform any element."""
        return element

    def __call__(self, element: doc_struct.Element) -> doc_struct.Element:
        """Transform generic Elements."""
        return self._transform_element_base(element)


class _ParagraphElementTransformation(_TransformationBase):
    """Transformation class for ParagraphElement and subclasses.

    A transform_...() function is called for each element in the
    document. self.context allows to see the path down to the
    current element.

    Default behaviour for all transformation is to return the
    original element/data.
    """

    def _transform_text_run(
            self, text_run: doc_struct.TextRun) -> doc_struct.TextRun:
        """Transform a text run."""
        return text_run

    def _transform_chip_url(self, url: Optional[str]) -> Optional[str]:
        """Transform the URL of a chip."""
        return url

    def _transform_chip(self, chip: doc_struct.Chip) -> doc_struct.Chip:
        """Transform a chip."""
        new_url = self._transform_chip_url(chip.url)
        return dataclasses.replace(chip, url=new_url)

    def _transform_reference(
            self, ref: doc_struct.Reference) -> doc_struct.Reference:
        """Transform a reference."""
        new_url = self._transform_link_url(ref.url)
        return dataclasses.replace(ref, url=new_url)

    def _transform_reference_id(self, ref_id: str) -> str:
        """Transform the ID of the reference."""
        return ref_id

    def _transform_reference_target(
            self,
            ref: doc_struct.ReferenceTarget) -> doc_struct.ReferenceTarget:
        """Transform a reference."""
        new_id = self._transform_reference_id(ref.ref_id)
        return dataclasses.replace(ref, ref_id=new_id)

    def _transform_link_url(self, url: Optional[str]) -> Optional[str]:
        """Transform the URL of a link."""
        return url

    def _transform_link(self, link: doc_struct.Link) -> doc_struct.Link:
        """Transform a chip."""
        new_url = self._transform_link_url(link.url)
        return dataclasses.replace(link, url=new_url)

    # pylint: disable=unused-argument
    def _transform_text_line_elements_item(
        self, index: int, item: doc_struct.ParagraphElement
    ) -> Optional[doc_struct.ParagraphElement]:
        """Transform an item in the elements of a text line."""
        return self._transform_paragraph_element(item)

    def _transform_text_line_elements(
        self, element_list: Sequence[doc_struct.ParagraphElement]
    ) -> Sequence[doc_struct.ParagraphElement]:
        """Transform the list of paragraph elements of a text line.

        Updates the context so the currently processed element is at the top
        of the path stack.
        """
        return _skip_if_none([
            self._call_with_context(self._transform_text_line_elements_item,
                                    index, item)
            for index, item in enumerate(element_list)
        ])

    def _transform_text_line(
            self, text_line: doc_struct.TextLine) -> doc_struct.TextLine:
        """Transform a text line."""
        return dataclasses.replace(text_line,
                                   elements=self._transform_text_line_elements(
                                       text_line.elements))

    def _transform_paragraph_element_base(
        self, paragraph_element: doc_struct.ParagraphElement
    ) -> doc_struct.ParagraphElement:
        """Transform generic paragraph element."""
        return _safe_cast(self._transform_element_base(paragraph_element),
                          doc_struct.ParagraphElement)

    def _transform_paragraph_element(
        self, paragraph_element: doc_struct.ParagraphElement
    ) -> doc_struct.ParagraphElement:
        """Transform a Paragraph element.

        Transforms the text(transform_paragraph_element_text), then applies
        another transformation specific to the type (e.g. transform_text_run).
        """
        paragraph_element = self._transform_paragraph_element_base(
            paragraph_element)
        if isinstance(paragraph_element, doc_struct.TextRun):
            return self._transform_text_run(paragraph_element)
        if isinstance(paragraph_element, doc_struct.Link):
            return self._transform_link(paragraph_element)
        if isinstance(paragraph_element, doc_struct.Chip):
            return self._transform_chip(paragraph_element)
        if isinstance(paragraph_element, doc_struct.Reference):
            return self._transform_reference(paragraph_element)
        if isinstance(paragraph_element, doc_struct.ReferenceTarget):
            return self._transform_reference_target(paragraph_element)
        if isinstance(paragraph_element, doc_struct.TextLine):
            return self._transform_text_line(paragraph_element)
        argtype = type(paragraph_element)
        raise Exception(f'Cannot handle type {argtype}.')

    def __call__(self, element: doc_struct.Element) -> doc_struct.Element:
        """Transform any paragraph element."""
        if isinstance(element, doc_struct.ParagraphElement):
            return self._transform_paragraph_element(element)
        else:
            return super().__call__(element)


class _ParagraphTransformation(_ParagraphElementTransformation):
    """Transformation for Paragraph elements and subclasses.

    A transform_...() function is called for each element in the
    document. self.context allows to see the path down to the
    current element.

    Default behaviour for all transformation is to return the
    original element/data.
    """

    # pylint: disable=unused-argument
    def _transform_nested_bullet_item(
            self, item_number: int,
            item: doc_struct.BulletItem) -> Optional[doc_struct.BulletItem]:
        """Transform a bullet item that is nested in another.

        Called from transform_nested_bullet_items(), for each item.

        Returns:
            The transformed bullet item or None if the item should be filtered.
        """
        return _safe_cast(self._transform_paragraph(item),
                          doc_struct.BulletItem)

    def _transform_nested_bullet_items(
        self, itemlist: Sequence[doc_struct.BulletItem]
    ) -> Sequence[doc_struct.BulletItem]:
        """Transform the list of nested bullet items.

        Updates the context so the currently processed element is at the top
        of the path stack.
        """
        return _skip_if_none([
            self._call_with_context(self._transform_nested_bullet_item, index,
                                    item)
            for index, item in enumerate(itemlist)
        ])

    def _transform_bullet_item(
            self, bullet_item: doc_struct.BulletItem) -> doc_struct.BulletItem:
        """Transform a bullet item and all nested ones."""
        new_nested = self._transform_nested_bullet_items(bullet_item.nested)
        new_item = dataclasses.replace(bullet_item, nested=new_nested)
        return new_item

    # pylint: disable=unused-argument
    def _transform_paragraph_elements_item(
        self,
        location: int,
        element: doc_struct.ParagraphElement,
    ) -> Optional[doc_struct.ParagraphElement]:
        """Transform a single element that is part of a paragraph.

        Called from transform_paragraph_elements(), for each item.

        Args:
            location: Tuple of the form (line_number, fragment_number_in_line).
        """
        return self._transform_paragraph_element(element)

    def _transform_paragraph_elements(
        self, element_list: Sequence[doc_struct.ParagraphElement]
    ) -> Sequence[doc_struct.ParagraphElement]:
        """Transform the list of paragraph elements of a paragraph.

        Updates the context so the currently processed element is at the top
        of the path stack.
        """
        return _skip_if_none([
            self._call_with_context(self._transform_paragraph_elements_item,
                                    index, item)
            for index, item in enumerate(element_list)
        ])

    def _transform_paragraph_base(
            self, paragraph: doc_struct.Paragraph) -> doc_struct.Paragraph:
        """Transform a paragraph and all contained elements."""
        paragraph = _safe_cast(self._transform_element_base(paragraph),
                               doc_struct.Paragraph)
        new_lines = self._transform_paragraph_elements(paragraph.elements)
        return dataclasses.replace(paragraph, elements=new_lines)

    def _transform_heading(self,
                           heading: doc_struct.Heading) -> doc_struct.Heading:
        """Transform a heading elment.

        Applied after the standard Paragraph transform.
        """
        return heading

    def _transform_paragraph(
            self, paragraph: doc_struct.Paragraph) -> doc_struct.Paragraph:
        """Transform a paragrpah.

        Performs an additional transformation (transform_bullet_item)
        if the paragraph is of type BulletItem.
        """
        paragraph = self._transform_paragraph_base(paragraph)
        if isinstance(paragraph, doc_struct.BulletItem):
            paragraph = self._transform_bullet_item(paragraph)
        if isinstance(paragraph, doc_struct.Heading):
            paragraph = self._transform_heading(paragraph)
        return paragraph

    def __call__(self, element: doc_struct.Element) -> doc_struct.Element:
        """Transform any paragraph element."""
        if isinstance(element, doc_struct.Paragraph):
            return self._transform_paragraph(element)
        else:
            return super().__call__(element)


class _StructuralElementTransformation(_ParagraphTransformation):
    """Transform strutural elements.

    Transforms the text(transform_paragraph_element_text), then applies
    another transformation specific to the type (e.g. transform_text_run).
    """

    # pylint: disable=unused-argument
    def _transform_doc_content_element(
        self, element_number: int, element: doc_struct.StructuralElement
    ) -> Optional[doc_struct.StructuralElement]:
        """Transform a single document content inside a doc content.

        Called from transform_doc_content_elements(), for each element.
        """
        new_element = self._transform_structural_element(element)
        return new_element

    def _transform_doc_content_elements(
        self, element_list: Sequence[doc_struct.StructuralElement]
    ) -> Sequence[doc_struct.StructuralElement]:
        """Transform the list of doc content elements of one doc content.

        Updates the context so the currently processed element is at the top
        of the path stack.
        """
        return _skip_if_none([
            self._call_with_context(self._transform_doc_content_element, index,
                                    element)
            for index, element in enumerate(element_list)
        ])

    def _transform_doc_content(
            self, doc_content: doc_struct.DocContent) -> doc_struct.DocContent:
        """Transform a doc content element and all contained elements."""
        doc_content = _safe_cast(self._transform_element_base(doc_content),
                                 doc_struct.DocContent)
        new_elements = self._transform_doc_content_elements(
            doc_content.elements)
        return dataclasses.replace(doc_content, elements=new_elements)

    # pylint: disable=unused-argument
    def _transform_table_cell_content(
            self, location: Tuple[int, int],
            content: doc_struct.DocContent) -> Optional[doc_struct.DocContent]:
        """Transform the content of a single table cell within a table.

        Called from transform_table_cells.

        Returns:
            The transformed DocContent or None if the cell is to be filtered.
        """
        return self._transform_doc_content(content)

    def _transform_table_cells(
            self, lines: DocContent2dSequence) -> DocContent2dSequence:
        """Transform the list of table cells for one table.

        Updates the context so the currently processed element is at the top
        of the path stack.
        """

        def _inner_func(
            row: int, line: Sequence[doc_struct.DocContent]
        ) -> Optional[Sequence[doc_struct.DocContent]]:
            """Transform the inner array represnting a table row.

            Returns:
                The transformed row or None if empty.
            """
            return _skip_if_none([
                self._call_with_context(self._transform_table_cell_content,
                                        (row, col), el)
                for col, el in enumerate(line)
            ]) or None

        return _skip_if_none(
            [_inner_func(row, line) for row, line in enumerate(lines)])

    def _transform_table(self, table: doc_struct.Table) -> doc_struct.Table:
        """Transform a table and all of its cells."""
        new_table = self._transform_table_cells(table.elements)
        return dataclasses.replace(table, elements=new_table)

    # pylint: disable=unused-argument
    def _transform_bullet_list_item(
            self, item_number: int,
            item: doc_struct.BulletItem) -> Optional[doc_struct.BulletItem]:
        """Transform a bullet item within a bullet list.

        Called from transform_bullet_list_items(), for each item.

        Returns:
            The transformed bullet item or None if the item should be filtered.
        """
        return _safe_cast(self._transform_paragraph(item),
                          doc_struct.BulletItem)

    def _transform_bullet_list_items(
        self, item_list: Sequence[doc_struct.BulletItem]
    ) -> Sequence[doc_struct.BulletItem]:
        """Transform the list of bullet items for one bullet list.

        Updates the context so the currently processed element is at the top
        of the path stack.
        """
        return _skip_if_none([
            self._call_with_context(self._transform_bullet_list_item, index,
                                    item)
            for index, item in enumerate(item_list)
        ])

    def _transform_bullet_list(
            self, bullet_list: doc_struct.BulletList) -> doc_struct.BulletList:
        """Transform a bullet list and all of its items."""
        new_items = self._transform_bullet_list_items(bullet_list.items)
        return dataclasses.replace(bullet_list, items=new_items)

    def _transform_section_heading(
            self, heading: Optional[doc_struct.Heading]
    ) -> Optional[doc_struct.Heading]:
        """Transform the heading of a section object."""
        if heading is None:
            return None
        return _safe_cast(self._transform_paragraph(heading),
                          doc_struct.Heading)

    # pylint: disable=unused-argument
    def _transform_section_content_item(
        self, index: int, item: doc_struct.StructuralElement
    ) -> Optional[doc_struct.StructuralElement]:
        """Transform and filter an item in the content of a section."""
        return self._transform_structural_element(item)

    def _transform_section_content(
        self, item_list: Sequence[doc_struct.StructuralElement]
    ) -> Sequence[doc_struct.StructuralElement]:
        """Transform the content items of a section."""
        return _skip_if_none([
            self._call_with_context(self._transform_section_content_item,
                                    index, item)
            for index, item in enumerate(item_list)
        ])

    def _transform_section(self,
                           section: doc_struct.Section) -> doc_struct.Section:
        """Transform a section instance."""
        return dataclasses.replace(
            section,
            heading=self._transform_section_heading(section.heading),
            content=self._transform_section_content(section.content))

    def _transform_structural_element_base(
        self, structural_element: doc_struct.StructuralElement
    ) -> doc_struct.StructuralElement:
        """Transform generic structural elements."""
        return _safe_cast(self._transform_element_base(structural_element),
                          doc_struct.StructuralElement)

    def _transform_note_item(
            self, index: int,
            paragraph: doc_struct.Paragraph) -> Optional[doc_struct.Paragraph]:
        """Transform a single note item (of type Paragraph)."""
        return self._transform_paragraph(paragraph)

    def _transform_note_items(
        self, item_list: Sequence[doc_struct.Paragraph]
    ) -> Sequence[doc_struct.Paragraph]:
        """Transform each element in the notes appendix."""
        return _skip_if_none([
            self._call_with_context(self._transform_note_item, index, item)
            for index, item in enumerate(item_list)
        ])

    def _transform_notes_appendix(
            self, notes_appendix: doc_struct.NotesAppendix
    ) -> doc_struct.NotesAppendix:
        """Transform the notes appendix."""
        return dataclasses.replace(notes_appendix,
                                   elements=self._transform_note_items(
                                       notes_appendix.elements))

    def _transform_structural_element(
        self, structural_element: doc_struct.StructuralElement
    ) -> doc_struct.StructuralElement:
        """Transform a structural element, depending on its type."""
        structural_element = self._transform_structural_element_base(
            structural_element)
        if isinstance(structural_element, doc_struct.Paragraph):
            return self._transform_paragraph(structural_element)
        if isinstance(structural_element, doc_struct.BulletList):
            return self._transform_bullet_list(structural_element)
        if isinstance(structural_element, doc_struct.Table):
            return self._transform_table(structural_element)
        if isinstance(structural_element, doc_struct.Section):
            return self._transform_section(structural_element)
        if isinstance(structural_element, doc_struct.NotesAppendix):
            return self._transform_notes_appendix(structural_element)
        argtype = type(structural_element)
        raise TypeError(f'Cannot handle type {argtype}.')

    def __call__(self, element: doc_struct.Element) -> doc_struct.Element:
        """Transform any structural element."""
        if isinstance(element, doc_struct.StructuralElement):
            return self._transform_structural_element(element)
        if isinstance(element, doc_struct.DocContent):
            return self._transform_doc_content(element)
        else:
            return super().__call__(element)


# pylint: disable=too-few-public-methods
class Transformation(_StructuralElementTransformation):
    """Transform an entire document."""

    def _transform_shared_data(
            self, shared_data: doc_struct.SharedData) -> doc_struct.SharedData:
        """Transform the shared data of a document."""
        return _safe_cast(self._transform_element_base(shared_data),
                          doc_struct.SharedData)

    def __call__(self, element: doc_struct.Element) -> doc_struct.Element:
        """Transform an element, usually a document."""
        self.context.add(element, ".")
        if isinstance(element, doc_struct.Document):
            new_element = _safe_cast(self._transform_element_base(element),
                                     doc_struct.Document)
            result = dataclasses.replace(
                new_element,
                shared_data=self._transform_shared_data(
                    new_element.shared_data),
                content=self._transform_doc_content(new_element.content))
        elif isinstance(element, doc_struct.SharedData):
            result = self._transform_shared_data(element)
        else:
            result = super().__call__(element)

        self.context.remove(element)
        return result
