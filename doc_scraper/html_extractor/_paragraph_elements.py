"""HTML extractor frames handling in-paragraph content."""

from typing import List, Optional, Union
import re

from doc_scraper import doc_struct
from doc_scraper.html_extractor import _base

# Regex to remove multiline whitespace from HTML data.
_DATA_WHITESPACE_RE = re.compile(r'\s+', re.S)


class ParagraphElementFrame(_base.Frame):
    """Frame for all elements within a single paragraph.

    converts to an element of type:
    *   Chip if the style is matching.
    *   Link if it's not a chip but has a URL set.
    *   TextRun for anything else.
    """

    def __init__(self,
                 context: _base.ParseContext,
                 attrs: Optional[_base.KeyValueType] = None,
                 style: Optional[_base.KeyValueType] = None,
                 text: Optional[Union[str, List[str]]] = None) -> None:
        """Create an instance.

        Uses the style matcher in the context to determine the
        category for the element to allow matching and data extraction
        based on style.
        """
        super().__init__(context, attrs, style)
        self.text: List[str] = []
        if text:
            if isinstance(text, str):
                self.text = [text]
            else:
                self.text = text
        self.url: Optional[str] = None

    def _is_chip(self) -> bool:
        """Check if the passed style shows we have a smart chip.

        The Google Docs HTML export nicely colors all chip spans
        with a specific blue and underlines them.

        Returns:
            True if the styles indicate the span is a chip.
        """
        return self.style.get('color', '') == '#0000ee' and self.style.get(
            'text-decoration', "") == 'underline'

    def handle_data(self, data: str):
        """Process data/text within HTML tags.

        Any whitespace including newline is compressed to a single
        space.
        """
        text = str(data)
        text = _DATA_WHITESPACE_RE.sub(' ', text)
        self.text.append(text)

    def handle_start(self, tag: str,
                     attrs: _base.KeyValueType) -> Optional[_base.Frame]:
        r"""Handle start of nested br and a tags.

        br tags are converted to text items containing '\n'.
        a tags cause the span to be treated as link or chip.
        """
        if tag == 'br':
            self.text.append('\n')

        if tag == 'a':
            attrs_dict = dict(attrs)
            if self.url:
                raise ValueError('url already set')
            self.url = attrs_dict.get('href', None)

    def handle_end(self, tag: str) -> 'Optional[_base.Frame]':
        """Handle the closing 'span' HTML tag used to extract Texts from."""
        if tag == 'span':
            return self

        if tag in ('b', 'i', 'br', 'a'):
            return None

        raise _base.UnexpectedHtmlTag(
            f'Unexpected tag {tag} procesing {self}.')

    def to_struct(self) -> doc_struct.ParagraphElement:
        """Convert to doc_struct structure."""
        text = "".join(self.text)
        if self._is_chip():
            return doc_struct.from_super(doc_struct.Chip,
                                         super().to_struct(),
                                         text=text,
                                         url=self.url)
        elif self.url is not None:
            return doc_struct.from_super(doc_struct.Link,
                                         super().to_struct(),
                                         text=text,
                                         url=self.url)
        else:
            return doc_struct.from_super(doc_struct.TextRun,
                                         super().to_struct(),
                                         text=text)


class LineBreakFrame(ParagraphElementFrame):
    """Represents a line break within a paragraph."""

    def __init__(self,
                 context: _base.ParseContext,
                 attrs: Optional[_base.KeyValueType] = None,
                 style: Optional[_base.KeyValueType] = None) -> None:
        """Construct an instance."""
        super().__init__(context, attrs, style)
        self.text: List[str] = ['\n']

    def to_struct(self) -> doc_struct.TextRun:
        """Convert to doc_struct structure."""
        return doc_struct.from_super(doc_struct.TextRun,
                                     super().to_struct(),
                                     text='\n')


class SuperscriptFrame(ParagraphElementFrame):
    """Represents comment and footnote superscript references."""

    def __init__(self,
                 context: _base.ParseContext,
                 attrs: Optional[_base.KeyValueType] = None,
                 style: Optional[_base.KeyValueType] = None) -> None:
        """Construct an instance."""
        super().__init__(context, attrs, style)

    def handle_end(self, tag: str) -> Optional[_base.Frame]:
        """Handle the end tags for sup and span."""
        if tag == 'sup':
            return self
        if tag == 'span':
            raise _base.UnexpectedHtmlTag(
                f'Unexpected tag {tag} procesing {self}.')
        return super().handle_end(tag)

    def to_struct(self) -> doc_struct.Reference:
        """Convert to doc_struct structure."""
        text = "".join(self.text)
        return doc_struct.from_super(doc_struct.Reference,
                                     super().to_struct(),
                                     text=text,
                                     url=self.url)


class PlainAnchorFrame(ParagraphElementFrame):
    """Represents an A tag outside of a span.

    Used as target for bookmarks, footnotes and comments.
    """

    def __init__(self,
                 context: _base.ParseContext,
                 attrs: Optional[_base.KeyValueType] = None,
                 style: Optional[_base.KeyValueType] = None) -> None:
        """Construct an instance."""
        super().__init__(context, attrs, style)

    def handle_end(self, tag: str) -> Optional[_base.Frame]:
        """Handle end tag of a and span tags."""
        if tag == 'a':
            return self
        if tag == 'span':
            raise _base.UnexpectedHtmlTag(
                f'Unexpected tag {tag} procesing {self}.')
        return super().handle_end(tag)

    def to_struct(self) -> doc_struct.ReferenceTarget:
        """Convert to doc_struct structure."""
        text = "".join(self.text)
        ref_id = self.attrs.get('id', '')
        return doc_struct.from_super(doc_struct.ReferenceTarget,
                                     super().to_struct(),
                                     text=text,
                                     ref_id=ref_id)
