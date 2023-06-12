"""Classes to describe a document with a simplified structure.

Based on
https://developers.google.com/docs/api/reference/rest/v1/documents#Document
with better subclassing and only relevant classes implemented.

doc_struct instances are usually created when loading and parsing docs and then
rewritten during transformations.

General concepts:

*   Immutability: To avoid pitfalls during trans formation, doc_struct.*
    classes are frozen dataclasses. This ensures that a transformation can
    either replace and instance (potentially reusing nested items) or create
    a new one, but never leave the original in a modified state.
*   JSON conversion: doc_struct.* classes are dataclasses, as this simplifies
    the implementation to convert them into dict/list structures for output
    or additional filtering.
"""

from typing import (
    Optional,
    Any,
    TypeVar,
    Type,
    Mapping,
    Sequence,
    Dict,
    cast,
    Generic,
)

from types import NoneType

from typing import Union
from dataclasses import dataclass, fields, is_dataclass, field, MISSING
import json


def tags_for(*tags: str) -> Mapping[str, str]:
    """Create tags more easily."""
    return {item: '1' for item in tags}


@dataclass(frozen=True, kw_only=True, eq=True)
class Element():
    """Commen base for all elements.

    Attributes:
        attrs: Additional attributes assoicated with the element.
            In case of HTML parsin, may contain attribute tags.
            Additional attributes may be added in transformations,
            e.g. when tagging elements.
        style: dict of HTML or other style details for the element.
        tags: Set of tags associated with the element.
    """

    attrs: Mapping[str, Any] = field(default_factory=dict)
    style: Mapping[str, str] = field(default_factory=dict)
    tags: Mapping[str, str] = field(default_factory=dict)


_AsDictArg = Union[Element, Sequence[Any], Mapping[str, Any]]


def as_dict(obj: _AsDictArg) -> Any:
    """Convert to dict/array structure."""
    return DictConverter().convert(obj)


_R = TypeVar('_R', bound=Element)


def from_super(cls: Type[_R], parent: Element, **kwargs: Any) -> _R:
    """Construct an instance based on field of a parent class.

    Args:
        cls: The type of the instance to be created.
        parent: Instance of any parent class from which the
            fields are copied.
        kwargs:
            Additional arguments. Will override parent fields.

    Returns:
        Instance of type cls with fields set from kwargs and parent.
    """
    new_kwargs: Dict[str, Any] = {}
    for field_ in fields(parent):
        new_kwargs[field_.name] = getattr(parent, field_.name)
    new_kwargs.update(kwargs)
    return cls(**new_kwargs)


@dataclass(frozen=True, kw_only=True, eq=True)
class ParagraphElement(Element):
    """Common base for all elements directly in a paragraph."""


@dataclass(frozen=True, kw_only=True, eq=True)
class TextRun(ParagraphElement):
    """Represents a fragment of text, with same attributes.

    Attributes:
        text: The actual text in the text run.
    """

    text: str


@dataclass(frozen=True, kw_only=True, eq=True)
class TextLine(ParagraphElement):
    """Represents a single line within a paragraph.

    Attributes:
        elements: Additional ParagraphElements that belong
            to the same line of text.
    """

    elements: Sequence[ParagraphElement]


@dataclass(frozen=True, kw_only=True, eq=True)
class Link(ParagraphElement):
    """Represent a text with link.

    Attributes:
        text: Actual text displayed in the chip
        url: URL/link related to the chip, e.g. to a Drive item.
    """

    text: str
    url: Optional[str] = None


@dataclass(frozen=True, kw_only=True, eq=True)
class Chip(ParagraphElement):
    """Represent a smart chip.

    Attributes:
        text: Actual text displayed in the chip
        url: URL/link related to the chip, e.g. to a Drive item.
    """

    text: str
    url: Optional[str] = None


@dataclass(frozen=True, kw_only=True, eq=True)
class Reference(ParagraphElement):
    """Represent a referemce, like footnote or comment.

    Attributes:
        text: Actual text displayed as part of the reference.
        url: Reference to the target.
    """

    text: str
    url: str


@dataclass(frozen=True, kw_only=True, eq=True)
class ReferenceTarget(ParagraphElement):
    """Represent the target of a referemce.

    Attributes:
        text: Actual text displayed as part of the reference.
        ref_id: Id to use when referring to this element.
    """

    text: str
    ref_id: str


@dataclass(frozen=True, kw_only=True, eq=True)
class StructuralElement(Element):
    """Common base for all items that add structure/blocks.

    Attributes:
        left_offset: Space on the left side of the structural element. Allows
            to understand e.g. indention in bullet items.
    """

    left_offset: Optional[int] = None


@dataclass(frozen=True, kw_only=True, eq=True)
class DocContent(Element):
    """Represent a partyial or entire document.

    Used e.g. in table cells, as they may again contain
    structural elements (and thus behave like a doc in doc).

    Attributes:
        elements: All structural elements that make up the
            doc content.
    """

    elements: Sequence[StructuralElement]


@dataclass(frozen=True, kw_only=True, eq=True)
class SharedData(Element):
    """Represent the non-content part of a document.

    Attributes:
        style_rules: Minimally parsed original HTML styles. Made available
            to obtain style details provided by CSS classes.
    """

    style_rules: Mapping[str, Mapping[str, str]] = field(default_factory=dict)


@dataclass(frozen=True, kw_only=True, eq=True)
class Document(Element):
    """Represent the entire document.

    Attributes:
        shared_data: All shared data for the document.
        content: The actual content of the doc.
    """

    shared_data: SharedData
    content: DocContent


@dataclass(frozen=True, kw_only=True, eq=True)
class Table(StructuralElement):
    """Represent a table.

    Attributes:
        elements: list of list of table cells.
    """

    elements: Sequence[Sequence[DocContent]]


@dataclass(frozen=True, kw_only=True, eq=True)
class Paragraph(StructuralElement):
    """Common base and actual class for paragraphs.

    Attributes:
        elements: List of paragraph elements.
    """

    elements: Sequence[ParagraphElement]


@dataclass(frozen=True, kw_only=True, eq=True)
class NotesAppendix(StructuralElement):
    """Appendix containing all notes and comments.

    Attributes:
        elements: List of paragraphs, representing notes.
    """

    elements: Sequence[Paragraph]


@dataclass(frozen=True, kw_only=True, eq=True)
class Heading(Paragraph):
    """Represent headings, as a special paragraph.

    Attributes:
        level: Heading level as used in HTML, i.e.
        H1 is above H2.
    """

    level: int


@dataclass(frozen=True, kw_only=True, eq=True)
class BulletItem(Paragraph):
    """Represent a bullet item, as a special paragraph.

    Attribjutes:
        level: Indention level, where 0 are top level items.
        list_type: HTML list type, e.g. 'ul'
        list_class: class used for the surrounding bullet list.
            Useful when identifying list styles. Class should
            match some of the SharedData.style_rules.
        nested: list of bullet items with higher idention, i.e.
            that are nested below the current item.
    """

    level: Optional[int] = None
    list_type: str
    list_class: Optional[str] = None
    nested: 'Sequence[BulletItem]' = field(default_factory=list)


@dataclass(frozen=True, kw_only=True, eq=True)
class BulletList(StructuralElement):
    """Represent an entire bullet list.

    Attributes:
        items: List of bullet items.
    """

    items: Sequence[BulletItem]


# Classes resulting from transformations


@dataclass(frozen=True, kw_only=True, eq=True)
class Section(StructuralElement):
    """Encapsulate a section in the form of heading and content.

    Note: Section instances are not "naturally" appearing in the
    original documents. They are inserted as the result of a
    transformation (sections_basic.SectionNestingTransform).

    Attributes:
        heading: The element containing the actual heading, i.e.
            including text
        content: The items following the heading, until a heading
            of the same level occurs. Note that nested heading
            elements can be in the content, to encapsulate the
            content associated with lower headings.
    """

    # None for level 0 or when bridging a gap in levels.
    heading: Optional[Heading]
    content: Sequence[StructuralElement]


class DocStuctJsonEncoder(json.JSONEncoder):
    """Custom JSON serializer to support dataclasses."""

    def encode(self, o: Any) -> str:
        """Add dataclasses to the default encoder."""
        if is_dataclass(o):
            as_dict_: dict[str, Any] = {
                field.name: getattr(o, field.name) for field in fields(o)
            }
            as_dict_['type'] = type(o).__name__
            return super().encode(as_dict)
        return super().encode(o)


def _ensure_newline(text: str) -> str:
    """Make sure the text ends with a newline."""
    if text[-1] != '\n':
        text += '\n'
    return text


# Output type for ConverterBase
_O = TypeVar('_O')


class ConverterBase(Generic[_O]):
    """Base functionality to convert elements into another type."""

    def _convert_element(self, element: Element) -> _O:
        """Convert an actual Element, or any subtype as fallback."""
        raise NotImplementedError('need to override')

    def _convert_text(
            self, element: TextRun | Link | Reference | Chip | ReferenceTarget
    ) -> _O:
        """Convert any element that has a text attribute."""
        return self._convert_element(element)

    def _convert_linklike(self, element: Link | Reference | Chip) -> _O:
        """Convert all elements that have a url attribute."""
        return self._convert_element(element)

    def _convert_ref_target(self, element: ReferenceTarget) -> _O:
        """Convert a reference target element."""
        return self._convert_element(element)

    def _convert_text_line(self, element: TextLine) -> _O:
        """Convert a text line element."""
        converted_elements = [
            self.convert(element2) for element2 in element.elements
        ]
        return self._convert_text_line_with_descendents(
            element, converted_elements)

    def _convert_text_line_with_descendents(self, element: TextLine,
                                            elements: Sequence[_O]) -> _O:
        """Convert a text line with descendents already converted."""
        return self._convert_element(element)

    def _convert_doc_content(self, element: DocContent) -> _O:
        """Convert a doc content element."""
        converted_elements = [
            self.convert(element2) for element2 in element.elements
        ]
        return self._convert_doc_content_with_descentdents(
            element, converted_elements)

    def _convert_doc_content_with_descentdents(self, element: DocContent,
                                               elements: Sequence[_O]) -> _O:
        """Convert a doc content element with descendents already converted."""
        return self._convert_element(element)

    def _convert_document(self, element: Document) -> _O:
        """Convert a document element."""
        return self._convert_document_with_descendents(
            element, self.convert(element.shared_data),
            self.convert(element.content))

    def _convert_document_with_descendents(self, element: Document,
                                           shared_data: _O, content: _O) -> _O:
        """Convert a document with descendents already converted."""
        return self._convert_element(element)

    def _convert_table(self, element: Table) -> _O:
        """Convert a table."""
        converted_elements = [
            [self.convert(cell) for cell in row] for row in element.elements
        ]
        return self._convert_table_with_descendents(element,
                                                    converted_elements)

    def _convert_table_with_descendents(
            self, element: Table, elements: Sequence[Sequence[_O]]) -> _O:
        """Convert a table with descendents already converted."""
        return self._convert_element(element)

    def _convert_paragraph(self, element: Paragraph) -> _O:
        """Convert a paragraph."""
        converted_elements = [
            self.convert(element2) for element2 in element.elements
        ]
        return self._convert_paragraph_with_descendents(
            element, converted_elements)

    def _convert_paragraph_with_descendents(self, element: Paragraph,
                                            elements: Sequence[_O]) -> _O:
        """Convert a paragraph with descendents already converted."""
        return self._convert_element(element)

    def _convert_notes_appendix(self, element: NotesAppendix) -> _O:
        """Convert the notes appendix."""
        converted_elements = [
            self.convert(element2) for element2 in element.elements
        ]
        return self._convert_notes_appendix_with_descendents(
            element, converted_elements)

    def _convert_notes_appendix_with_descendents(self, element: NotesAppendix,
                                                 elements: Sequence[_O]) -> _O:
        """Convert the notes appendix with descendents already converted."""
        return self._convert_element(element)

    def _convert_bullet_item(self, element: BulletItem) -> _O:
        """Convert convert a bullet item."""
        converted_nested = [
            self.convert(element2) for element2 in element.nested
        ]
        converted_elements = [
            self.convert(element2) for element2 in element.elements
        ]
        return self._convert_bullet_item_with_descendents(
            element, converted_elements, converted_nested)

    def _convert_bullet_item_with_descendents(self, element: BulletItem,
                                              elements: Sequence[_O],
                                              nested: Sequence[_O]) -> _O:
        """Convert a bullet item with descendents already converted."""
        return self._convert_element(element)

    def _convert_bullet_list(self, element: BulletList) -> _O:
        """Convert a bullet list element."""
        converted_items = [
            self.convert(element2) for element2 in element.items
        ]
        return self._convert_bullet_list_with_descendents(
            element, converted_items)

    def _convert_bullet_list_with_descendents(self, element: BulletList,
                                              items: Sequence[_O]) -> _O:
        """Convert a bullet list with descendents already converted."""
        return self._convert_element(element)

    def _convert_section(self, element: Section) -> _O:
        """Convert a section element."""
        converted_heading = None
        if element.heading:
            converted_heading = self.convert(element.heading)
        converted_content = [
            self.convert(element2) for element2 in element.content
        ]
        return self._convert_section_with_descendents(element,
                                                      converted_heading,
                                                      converted_content)

    def _convert_section_with_descendents(self, element: Section,
                                          heading: Optional[_O],
                                          content: Sequence[_O]) -> _O:
        """Convert a section element with descendents already converted."""
        return self._convert_element(element)

    def _convert_shared_data(self, element: SharedData) -> _O:
        """Convert the shared data element."""
        return self._convert_element(element)

    def convert(self, element: Any) -> _O:  # noqa: C901
        """Convert any element.

        Delegate to specific conversion functions.

        Args:
            element: The element to convert (including descendents)

        Returns:
            The converted element.

        Raises:
            NotImplementedError when encountering unknown types.
        """
        if isinstance(element, TextRun):
            return self._convert_text(element)
        if isinstance(element, ReferenceTarget):
            return self._convert_ref_target(element)
        if isinstance(element, (Link, Reference, Chip)):
            return self._convert_linklike(element)
        if isinstance(element, TextLine):
            return self._convert_text_line(element)
        if isinstance(element, DocContent):
            return self._convert_doc_content(element)
        if isinstance(element, Document):
            return self._convert_document(element)
        if isinstance(element, Table):
            return self._convert_table(element)
        if isinstance(element, BulletItem):
            return self._convert_bullet_item(element)
        if isinstance(element, BulletList):
            return self._convert_bullet_list(element)
        if isinstance(element, Paragraph):
            return self._convert_paragraph(element)
        if isinstance(element, NotesAppendix):
            return self._convert_notes_appendix(element)
        if isinstance(element, Section):
            return self._convert_section(element)
        if isinstance(element, SharedData):
            return self._convert_shared_data(element)
        if isinstance(element, Element):
            return self._convert_element(element)
        else:
            tp = type(element)
            raise NotImplementedError(f'Unknown type {tp}')


@dataclass(kw_only=True)
class DictConverter(ConverterBase[Any]):
    """Convert an element with descendents to dict/array structure."""

    def _convert_element(self, element: Element) -> Any:
        """Convert an actual Element, or any subtype as fallback."""
        converted_attrs = {k: v for k, v in sorted(element.attrs.items())}
        converted_style = {k: v for k, v in sorted(element.style.items())}
        converted_tags = {k: v for k, v in sorted(element.tags.items())}

        result: Dict[str, Any] = {'type': type(element).__name__}

        for field_ in fields(element):
            name: str = field_.name

            value: Any = getattr(element, name)
            if not isinstance(value, (int, float, str, NoneType)):
                continue

            if value == field_.default:
                continue
            if not isinstance(field_.default_factory,
                              type(MISSING)) and value == cast(
                                  Any, field_.default_factory)():
                continue
            result[name] = value

        if converted_attrs:
            result['attrs'] = converted_attrs
        if converted_style:
            result['style'] = converted_style
        if converted_tags:
            result['tags'] = converted_tags
        return result

    def _convert_text_line_with_descendents(self, element: TextLine,
                                            elements: Sequence[Any]) -> Any:
        result = self._convert_element(element)
        result['elements'] = elements
        return result

    def _convert_doc_content_with_descentdents(self, element: DocContent,
                                               elements: Sequence[Any]) -> Any:
        result = self._convert_element(element)
        result['elements'] = elements
        return result

    def _convert_document_with_descendents(self, element: Document,
                                           shared_data: Any,
                                           content: Any) -> Any:
        result = self._convert_element(element)
        result['content'] = content
        result['shared_data'] = shared_data
        return result

    def _convert_table_with_descendents(
            self, element: Table, elements: Sequence[Sequence[Any]]) -> Any:
        result = self._convert_element(element)
        result['elements'] = elements
        return result

    def _convert_paragraph_with_descendents(self, element: Paragraph,
                                            elements: Sequence[Any]) -> Any:
        result = self._convert_element(element)
        result['elements'] = elements
        return result

    def _convert_notes_appendix_with_descendents(
            self, element: NotesAppendix, elements: Sequence[Any]) -> Any:
        result = self._convert_element(element)
        result['elements'] = elements
        return result

    def _convert_bullet_item_with_descendents(self, element: BulletItem,
                                              elements: Sequence[Any],
                                              nested: Sequence[Any]) -> Any:
        result: Dict[str, Any] = self._convert_paragraph(element)
        result['elements'] = elements
        if nested:
            result['nested'] = nested
        return result

    def _convert_bullet_list_with_descendents(self, element: BulletList,
                                              items: Sequence[Any]) -> Any:
        result = self._convert_element(element)
        result['items'] = items
        return result

    def _convert_section_with_descendents(self, element: Section,
                                          heading: Any | None,
                                          content: Sequence[Any]) -> Any:
        result = self._convert_element(element)
        if heading:
            result['heading'] = heading
        result['content'] = content
        return result

    def _convert_shared_data(self, element: SharedData) -> Any:
        converted_rules = {
            k: {
                k2: v2 for k2, v2 in sorted(v.items())
            } for k, v in sorted(element.style_rules.items())
        }

        result = self._convert_element(element)
        if converted_rules:
            result['style_rules'] = converted_rules
        return result


@dataclass(kw_only=True)
class RawTextConverter(ConverterBase[str]):
    """Extract all text portions of an element tree."""

    def _convert_element(self, element: Element) -> str:
        """Convert any generic element to empty string."""
        return ''

    def _convert_text(
            self, element: TextRun | Link | Reference | Chip | ReferenceTarget
    ) -> str:
        """Extract the text from all types containing text."""
        return element.text

    def _convert_linklike(self, element: Link | Reference | Chip) -> str:
        return self._convert_text(element)

    def _convert_ref_target(self, element: ReferenceTarget) -> str:
        return self._convert_text(element)

    def _convert_text_line(self, element: TextLine) -> str:
        """Convert text lines, assuming each line already ends with newline."""
        return "".join(self.convert(element2) for element2 in element.elements)

    def _convert_doc_content_with_descentdents(self, element: DocContent,
                                               elements: Sequence[str]) -> str:
        """Convert doc content, ensuring structural elements are separated."""
        return "".join(_ensure_newline(element2) for element2 in elements)

    def _convert_document_with_descendents(self, element: Document,
                                           shared_data: str,
                                           content: str) -> str:
        return content

    def _convert_table_with_descendents(
            self, element: Table, elements: Sequence[Sequence[str]]) -> str:
        r"""Convert a table.

        Use '\t' to mark cell boundaries, '\v' for row boundaries.
        """
        return "\v".join("\t".join(row) for row in elements) + "\n"

    def _convert_paragraph_with_descendents(self, element: Paragraph,
                                            elements: Sequence[str]) -> str:
        return "".join(elements)

    def _convert_notes_appendix_with_descendents(
            self, element: NotesAppendix, elements: Sequence[str]) -> str:
        return "".join(_ensure_newline(element2) for element2 in elements)

    def _convert_bullet_item_with_descendents(self, element: BulletItem,
                                              elements: Sequence[str],
                                              nested: Sequence[str]) -> str:
        """Convert and indent bullet items, including nested items."""
        indent_spc = "  " * (element.level or 0)
        text = "".join(elements)
        text = _ensure_newline('\n'.join(
            f'{indent_spc}{line}' for line in text.split('\n')))
        nested_text = "".join(_ensure_newline(item) for item in nested)
        return f'{text}{nested_text}'

    def _convert_bullet_list_with_descendents(self, element: BulletList,
                                              items: Sequence[str]) -> str:
        return "".join(_ensure_newline(item) for item in items)

    def _convert_section_with_descendents(self, element: Section,
                                          heading: Optional[str],
                                          content: Sequence[str]) -> str:
        """Convert a section, heading and content."""
        heading_text = heading or ''
        content_text = "".join(_ensure_newline(item) for item in content)

        return f'{heading_text}\n{content_text}\f'

    def _convert_shared_data(self, element: SharedData) -> str:
        return ''
