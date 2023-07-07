"""Extraction of structural elements (Paragraphs, bullet lists, tables)."""

from typing import List, Optional, Sequence
import re

from doc_scraper import doc_struct

from . import _base
from . import _paragraph_elements


class StructuralElementFrame(_base.Frame):
    # pylint: disable=line-too-long
    """Base class representing one structural element in a document.

    See also: https://developers.google.com/docs/api/reference/rest/v1/documents#StructuralElement     # noqa
    """

    def __init__(self,
                 context: _base.ParseContext,
                 attrs: Optional[_base.KeyValueType] = None) -> None:
        """Create an instance."""
        super().__init__(context, attrs)
        self.left_offset: Optional[int] = None
        if 'margin-left' in self.style:
            self.left_offset = int(
                self.style.get('margin-left', '0pt').replace('pt', ''))

    def to_struct(self) -> doc_struct.StructuralElement:
        """Convert to doc_struct structure."""
        return doc_struct.from_super(doc_struct.StructuralElement,
                                     super().to_struct(),
                                     left_offset=self.left_offset)


class TableFrame(StructuralElementFrame):
    """Represent HTML tables."""

    def __init__(self,
                 context: _base.ParseContext,
                 attrs: Optional[_base.KeyValueType] = None) -> None:
        """Create an instance."""
        super().__init__(context, attrs)
        self.table: 'List[List[DocContentFrame]]' = []

    def handle_start(self, tag: str,
                     attrs: _base.KeyValueType) -> Optional[_base.Frame]:
        """Handle nested start tags (tr,th,td).

        Update context when a td is started to capture the content.
        """
        if tag in ('tr', 'th'):
            self.table.append([])
            return None
        if tag == 'td':
            doc_content = DocContentFrame(self.context, 'td', attrs)
            self.table[-1].append(doc_content)
            return doc_content
        return None

    def handle_end(self, tag: str) -> 'Optional[_base.Frame]':
        """Handle end tag for the current table."""
        if tag == 'table':
            return self

        if tag in ('tr', 'th'):
            return None

        raise _base.UnexpectedHtmlTag(
            f'Unexpected tag {tag} procesing {self}.')

    def to_struct(self) -> doc_struct.Table:
        """Convert to doc_struct structure."""
        table_struct = [
            [cell.to_struct() for cell in row] for row in self.table
        ]

        return doc_struct.from_super(doc_struct.Table,
                                     super().to_struct(),
                                     elements=table_struct)


class ParagraphFrame(StructuralElementFrame):
    """Represent a paragraph in the document."""

    def __init__(self,
                 context: _base.ParseContext,
                 attrs: Optional[_base.KeyValueType] = None) -> None:
        """Create an instance."""
        super().__init__(context, attrs)
        self.elements: List[_paragraph_elements.ParagraphElementFrame] = []
        self.lines: List[List[_paragraph_elements.ParagraphElementFrame]] = []

    def handle_start(self, tag: str,
                     attrs: _base.KeyValueType) -> Optional[_base.Frame]:
        """Handle the start of a nested element (text or chip)."""
        if tag == 'span':
            element = _paragraph_elements.ParagraphElementFrame(
                self.context, attrs)
            self.elements.append(element)
            return element
        elif tag == 'sup':
            element = _paragraph_elements.SuperscriptFrame(
                self.context, attrs)
            self.elements.append(element)
            return element
        elif tag == 'a':
            element = _paragraph_elements.PlainAnchorFrame(
                self.context, attrs)
            self.elements.append(element)
            return element
        elif tag == 'br':
            element = _paragraph_elements.LineBreakFrame(self.context, attrs)
            self.elements.append(element)
            return None
        return None

    def handle_data(self, data: str):
        """Handle all data/text in the HTML tag."""
        text = _paragraph_elements.ParagraphElementFrame(self.context,
                                                         text=data)
        self.elements.append(text)

    def handle_end(self, tag: str) -> 'Optional[_base.Frame]':
        """Handle closing of the associated p tag."""
        if tag != 'p':
            raise _base.UnexpectedHtmlTag(
                f'Unexpected tag {tag} procesing {self}.')
        self.elements.append(
            _paragraph_elements.ParagraphElementFrame(self.context, text='\n'))
        return self

    def to_struct(self) -> doc_struct.Paragraph:
        """Convert to doc_struct structure."""
        elements = [e.to_struct() for e in self.elements]
        return doc_struct.from_super(doc_struct.Paragraph,
                                     super().to_struct(),
                                     elements=elements)


class NotesFrame(StructuralElementFrame):
    """Represent the div at the end containing footnotes and others."""

    def __init__(self,
                 context: _base.ParseContext,
                 attrs: Optional[_base.KeyValueType] = None) -> None:
        """Create an instance."""
        super().__init__(context, attrs)
        self.elements: List[ParagraphFrame] = []

    def handle_start(self, tag: str,
                     attrs: _base.KeyValueType) -> Optional[_base.Frame]:
        """Handle the start of a nested element (text or chip)."""
        if tag == 'p':
            element = ParagraphFrame(
                self.context, attrs)
            self.elements.append(element)
            return element
        return None

    def handle_end(self, tag: str) -> 'Optional[_base.Frame]':
        """Handle closing of the associated p tag."""
        if tag != 'div':
            raise _base.UnexpectedHtmlTag(
                f'Unexpected tag {tag} procesing {self}.')
        return self

    def to_struct(self) -> doc_struct.NotesAppendix:
        """Convert to doc_struct structure."""
        elements = [e.to_struct() for e in self.elements]
        return doc_struct.from_super(doc_struct.NotesAppendix,
                                     super().to_struct(),
                                     elements=elements)


def _get_heading_level(tag: str) -> Optional[int]:
    r"""Extract the heading level from h\d HTML tags."""
    if tag[0] != 'h':
        return None
    try:
        return int(tag[1:])
    except ValueError:
        return None


class HeadingFrame(ParagraphFrame):
    """Extract heading tag."""

    def __init__(self,
                 context: _base.ParseContext,
                 closing_tag: str,
                 attrs: Optional[_base.KeyValueType] = None) -> None:
        """Construct instance."""
        super().__init__(context, attrs)
        self.closing_tag = closing_tag
        self.level = _get_heading_level(closing_tag)

    def to_struct(self) -> doc_struct.Heading:
        """Convert to doc_struct structure."""
        return doc_struct.from_super(doc_struct.Heading,
                                     super().to_struct(),
                                     level=self.level)

    def handle_end(self, tag: str) -> 'Optional[_base.Frame]':
        """Handle the associated closing heading tag."""
        if tag != self.closing_tag:
            raise _base.UnexpectedHtmlTag(
                f'Unexpected tag {tag} procesing {self}.')
        return self


_LIST_CLASS_RE = re.compile(r'^lst-(.*)-\d+$')


class BulletItemFrame(ParagraphFrame):
    """Represent a bullet item with indented items as nested."""

    def __init__(
        self,
        context: _base.ParseContext,
        list_type: str,
        list_attrs: _base.KeyValueType,
        attrs: Optional[_base.KeyValueType] = None,
    ) -> None:
        """Construct an instance.

        Args:
            context: Parse context for the document.
            list_type: tag name (ul or ol) of the containing bullet list.
            list_attrs: all attributes of the containing ul or ol tag to get
                bullet type and other details.
            attrs: Attributes, e.g. from the original HTML tag).
        """
        super().__init__(context, attrs)
        self.level: Optional[int] = None
        self.list_type = list_type
        self.list_attrs = dict(list_attrs or {})
        self.list_styles = self._parse_style(self.list_attrs.get('styles', ''))

        self.nested_items: List[BulletItemFrame] = []

    @property
    def list_class(self) -> Optional[str]:
        """Get the class of the containing list tag for the bullet type."""
        my_classes = self.list_attrs.get('class', '').split(' ')
        for cls in my_classes:
            match = _LIST_CLASS_RE.match(cls)
            if match:
                return match.group(1)
        return None

    def to_struct(self) -> doc_struct.BulletItem:
        """Convert to doc_struct structure."""
        items_as_dict: Sequence[doc_struct.BulletItem] = [
            n.to_struct() for n in self.nested_items
        ]
        return doc_struct.from_super(doc_struct.BulletItem,
                                     super().to_struct(),
                                     level=self.level,
                                     list_type=self.list_type,
                                     list_class=self.list_class,
                                     nested=items_as_dict)

    def handle_end(self, tag: str) -> 'Optional[_base.Frame]':
        """Handle the closing li tag."""
        if tag == 'li':
            return self
        raise _base.UnexpectedHtmlTag(
            f'Unexpected tag {tag} procesing {self}.')


class BulletListFrame(StructuralElementFrame):
    """Handle bullet lists."""

    def __init__(self,
                 context: _base.ParseContext,
                 closing_tag: str,
                 attrs: Optional[_base.KeyValueType] = None) -> None:
        """Create an instance."""
        super().__init__(context, attrs)
        self.items: List[BulletItemFrame] = []
        self.closing_tag = closing_tag  # HTML tag that started the list

    def handle_start(self, tag: str,
                     attrs: _base.KeyValueType) -> Optional[BulletItemFrame]:
        """Handle start of children li items."""
        if tag == 'li':
            item = BulletItemFrame(self.context, self.closing_tag, self.attrs,
                                   attrs)
            self.items.append(item)
            return item
        return None

    def handle_end(self, tag: str) -> 'Optional[_base.Frame]':
        """Handle end of the current list."""
        if tag == self.closing_tag:
            return self
        raise _base.UnexpectedHtmlTag(
            f'Unexpected tag {tag} procesing {self}.')

    def to_struct(self) -> doc_struct.BulletList:
        """Convert to doc_struct structure.

        Nest the contained list items according to indention.
        """
        offsets: List[int] = list(
            sorted(item.left_offset or 0 for item in self.items))
        level_for_offset = dict(zip(offsets, range(len(offsets))))
        for item in self.items:
            item.level = level_for_offset[item.left_offset or 0]

        items_as_struct: list[doc_struct.BulletItem] = [
            item.to_struct() for item in self.items
        ]
        return doc_struct.from_super(doc_struct.BulletList,
                                     super().to_struct(),
                                     items=items_as_struct)


class DocContentFrame(_base.Frame):
    """Repersent a list of structural elements.

    Used for table cells and is the base class for the entire document.
    """

    def __init__(self,
                 context: _base.ParseContext,
                 closing_tag: str,
                 attrs: Optional[_base.KeyValueType] = None) -> None:
        """Create an instance."""
        super().__init__(context, attrs)
        self.elements: List[StructuralElementFrame] = []
        self.closing_tag = closing_tag

    def handle_start(self, tag: str,
                     attrs: _base.KeyValueType) -> Optional[_base.Frame]:
        """Handle start of the various nested HTML tags."""
        if tag == 'p':
            paragraph = ParagraphFrame(self.context, attrs)
            self.elements.append(paragraph)
            return paragraph
        elif tag == 'div':
            paragraph = NotesFrame(self.context, attrs)
            self.elements.append(paragraph)
            return paragraph
        if _get_heading_level(tag) is not None:
            heading = HeadingFrame(self.context, tag, attrs)
            self.elements.append(heading)
            return heading
        if tag == 'table':
            table = TableFrame(self.context, attrs)
            self.elements.append(table)
            return table
        if tag in ('ul', 'ol'):
            bullet_list = BulletListFrame(self.context, tag, attrs)
            self.elements.append(bullet_list)
            return bullet_list
        if tag == 'a':
            element = _base.DummyFrame(self.context, tag)
            return element
        return None

    def handle_end(self, tag: str) -> 'Optional[_base.Frame]':
        """Handle the end tag."""
        if tag == self.closing_tag:
            return self
        raise _base.UnexpectedHtmlTag(
            f'Unexpected tag {tag} procesing {self}.')

    def to_struct(self) -> doc_struct.DocContent:
        """Convert to doc_struct structure."""
        elements_as_struct: List[doc_struct.Element] = [
            element.to_struct() for element in self.elements
        ]
        return doc_struct.from_super(doc_struct.DocContent,
                                     super().to_struct(),
                                     elements=elements_as_struct)
