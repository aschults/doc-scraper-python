"""Extractor implementation and document frames."""

from typing import Any, Optional, Dict
import re

from doc_scraper import doc_struct

from . import _base
from . import _structural_elements


class BodyFrame(_structural_elements.DocContentFrame):
    """Represents the body of a document, associated with the HTML body."""

    def __init__(self,
                 context: _base.ParseContext,
                 attrs: Optional[_base.KeyValueType] = None) -> None:
        """Construct an instance."""
        super().__init__(context, 'body', attrs)

    def to_struct(self) -> doc_struct.DocContent:
        """Convert to struct."""
        return doc_struct.from_super(doc_struct.DocContent,
                                     super().to_struct())


# Regex to build a primitive CSS rule parser.
_CSS_RULE_RE = re.compile(r'\s*([^\{\}]+?)\s*\{\s*([^\{\}]*?)\s*\}\s*', re.S)

# Regex to match the spaces to compress, i.e. replace by single space.
_REMOVE_SPACES_RE = re.compile(r'\s+', re.S)


class HeadFrame(_base.Frame):
    """Represents the HTML head of a document.

    Needed to find additional CSS styles.
    """

    def __init__(self,
                 context: _base.ParseContext,
                 attrs: Optional[_base.KeyValueType] = None) -> None:
        """Construct an instance."""
        super().__init__(context, attrs)
        self.in_style_tag = False
        self.css_rules: Dict[str, Dict[str, str]] = {}

    # pylint: disable=unused-argument
    def handle_start(self, tag: str,
                     attrs: _base.KeyValueType) -> Optional[_base.Frame]:
        """Handle start tags, particularly style tags."""
        if tag != 'style':
            return None
        self.in_style_tag = True
        return None

    def handle_data(self, data: str):
        """Handle text/data, particularly inside style tags.

        Parse and add CSS rules to the context.
        """
        if not self.in_style_tag:
            return
        rules = _CSS_RULE_RE.findall(data)
        rules_as_dict = {
            _REMOVE_SPACES_RE.sub(' ', k): self._parse_style(v)
            for k, v in rules
        }
        self.css_rules.update(rules_as_dict)

    def handle_end(self, tag: str) -> 'Optional[_base.Frame]':
        """Handle the end, particularly of the style tags."""
        if tag == 'style':
            self.in_style_tag = False
            return None
        if tag == 'head':
            return self

        raise _base.UnexpectedHtmlTag(
            f'Unexpected tag {tag} procesing {self}.')

    def to_struct(self) -> doc_struct.SharedData:
        """Convert empty element as not relevant for document."""
        return doc_struct.SharedData(style_rules=self.css_rules)


class RootFrame(_base.Frame):
    """Root of the HTML document to extract data from."""

    def __init__(self,
                 context: _base.ParseContext,
                 attrs: Optional[_base.KeyValueType] = None) -> None:
        """Construct an instance."""
        super().__init__(context, attrs)
        self.document: Optional[BodyFrame] = None
        self.head: Optional[HeadFrame] = None

    def handle_start(self, tag: str,
                     attrs: _base.KeyValueType) -> Optional[_base.Frame]:
        """Handle child tags, particularly body and head."""
        if tag == 'body':
            doc = BodyFrame(self.context, attrs)
            if self.document:
                raise ValueError('document already set')
            self.document = doc
            return doc
        if tag == 'head':
            head = HeadFrame(self.context, attrs)
            if self.head is not None:
                raise ValueError('duplicate head tag')
            self.head = head
            return head

        return None

    def handle_end(self, tag: str) -> Optional[_base.Frame]:
        """Close root element."""
        return self

    def to_struct(self) -> Any:
        """Convert to struct."""
        content_as_struct = doc_struct.DocContent(elements=[])
        if self.document is not None:
            content_as_struct = self.document.to_struct()
        head_as_struct = doc_struct.SharedData()
        if self.head is not None:
            head_as_struct = self.head.to_struct()
        return doc_struct.Document(shared_data=head_as_struct,
                                   content=content_as_struct)
