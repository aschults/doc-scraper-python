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

from typing import Optional, Any, TypeVar, Type, Mapping, Sequence, Dict, cast
from typing import Union
from dataclasses import dataclass, fields, is_dataclass, field, MISSING
import json


@dataclass(frozen=True, kw_only=True, eq=True)
class Element():
    """Commen base for all elements.

    Attributes:
        attrs: Additional attributes assoicated with the element.
            In case of HTML parsin, may contain attribute tags.
            Additional attributes may be added in transformations,
            e.g. when tagging elements.
        style: dict of HTML or other style details for the element.
    """

    attrs: Mapping[str, Any] = field(default_factory=dict)
    style: Mapping[str, str] = field(default_factory=dict)


_AsDictArg = Union[Element, Sequence[Any], Mapping[str, Any]]


def as_dict(obj: _AsDictArg) -> Any:
    """Convert a doc_struct tree to dict/list."""
    if isinstance(obj, list):
        return [as_dict(item) for item in obj]
    if isinstance(obj, set):
        return {as_dict(item): True for item in sorted(obj)}
    if isinstance(obj, dict):
        return {
            k: as_dict(v)
            for k, v in sorted(cast(Mapping[str, Any], obj).items())
        }
    if isinstance(obj, Element):
        result: Dict[str, Any] = {}
        for field_ in fields(obj):
            name: str = field_.name
            value: Any = getattr(obj, name)
            if value == field_.default:
                continue
            if not isinstance(field_.default_factory,
                              type(MISSING)) and value == cast(
                                  Any, field_.default_factory)():
                continue
            result[name] = as_dict(value)
        result['type'] = type(obj).__name__
        return result

    return obj


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

    def as_plain_text(self) -> str:
        """Convert element to plain text."""
        raise NotImplementedError('as_plain')


@dataclass(frozen=True, kw_only=True, eq=True)
class TextRun(ParagraphElement):
    """Represents a fragment of text, with same attributes.

    Attributes:
        text: The actual text in the text run.
    """

    text: str

    def as_plain_text(self) -> str:
        """Convert element to plain text."""
        return self.text


@dataclass(frozen=True, kw_only=True, eq=True)
class TextLine(ParagraphElement):
    """Represents a single line within a paragraph.

    Attributes:
        elements: Additional ParagraphElements that belong
            to the same line of text.
    """

    elements: Sequence[ParagraphElement]

    def as_plain_text(self) -> str:
        """Convert element to plain text."""
        return "".join(element.as_plain_text() for element in self.elements)


@dataclass(frozen=True, kw_only=True, eq=True)
class Link(ParagraphElement):
    """Represent a text with link.

    Attributes:
        text: Actual text displayed in the chip
        url: URL/link related to the chip, e.g. to a Drive item.
    """

    text: str
    url: Optional[str] = None

    def as_plain_text(self) -> str:
        """Convert element to plain text."""
        result = f'[{self.text}]'
        if self.url:
            result += f'({self.url})'
        return result


@dataclass(frozen=True, kw_only=True, eq=True)
class Chip(ParagraphElement):
    """Represent a smart chip.

    Attributes:
        text: Actual text displayed in the chip
        url: URL/link related to the chip, e.g. to a Drive item.
    """

    text: str
    url: Optional[str] = None

    def as_plain_text(self) -> str:
        """Convert element to plain text."""
        result = f'[{self.text}]'
        if self.url:
            result += f'({self.url})'
        return result


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
