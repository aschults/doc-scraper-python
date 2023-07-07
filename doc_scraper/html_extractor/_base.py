"""Base classes for the HTML-based Google Docs extractor."""

import re
from typing import Any, Dict, List, Optional, Tuple, Union

from doc_scraper import doc_struct

# Regex used to match a single style property.
_STYLE_RE = re.compile(r"(?:^|;)\s*([^:;]+?)\s*:\s*([^;]+?)\s*(?=;|$)")


class UnexpectedHtmlTag(ValueError):
    """Raise when the HTML document has unexpected/bad structure."""


class ParseContext:
    """Context class for the HTML-based extraction."""

    def __repr__(self):
        """Provide simple representation as string."""
        return "ParseContext()"


# Type for passing dictionary-like data as list of tuples or dicts.
KeyValueType = Union[List[Tuple[str, Any]], Dict[str, Any]]


class Frame:
    """Base class for the extraction."""

    def __init__(self,
                 context: ParseContext,
                 attrs: Optional[KeyValueType] = None,
                 style: Optional[KeyValueType] = None) -> None:
        """Create an instance.

        Args:
            context: Context object that is passed ot all other frames.
            attrs: The attributes of the HTML tag associated wit this frame.
            style: Optional styles to override the default style parsing.
        """
        self.context: ParseContext = context
        self.attrs: dict[str, Any] = dict(attrs or {})
        self.style: dict[str, Any] = dict(style or {}) or self._parse_style(
            self.attrs.get("style", ""))

    def _parse_style(self, style_str: str) -> Dict[str, str]:
        """Primitive conversion of HTML style attributes to dict."""
        return dict(_STYLE_RE.findall(style_str))

    def handle_start(self, tag: str, attrs: KeyValueType) -> "Optional[Frame]":
        # pylint: disable=unused-argument
        """Handle the start of child HTML tags.

        Note: The HTML tag that resulted in this frame has been processed by
        the next frame in the frame stack (in the parser). Thus a frame never
        handles its own HTML start tags, e.g. TextFrame never parses the
        `<span>` opening tag, the surrounding ParagraphFrame does.

        Returns:
            The frame to be pushed onto the frame stack/path or None.
        """
        return None

    def handle_end(self, tag: str) -> "Optional[Frame]":
        # pylint: disable=unused-argument
        """Handle the start of a tag, including the associated HTML tag.

        Note: The end tag is processed by the frame that is dealing with
        the content, e.g. ParagraphFrame will handle the `</p>` HTML tag.

        Returns:
            The frame to be taken off the frame stack/path or None.
        """
        return self

    def handle_child_end(self, tag: str, child_frame: "Frame"):
        """Handle the end tag of the child popped from the frame stack.

        Called when the top item in the stack is removed due to handle_end()
        returning a frame. The frame returned then is passed to this method
        in the new top item of the frame stack.
        """

    def handle_data(self, data: str):
        """Handle all data/text in the HTML tag."""

    def to_struct(self) -> doc_struct.Element:
        """Convert the extracted details to doc_struct structure."""
        result = doc_struct.Element(style=self.style or {},
                                    attrs=self.attrs or {})
        return result

    def __eq__(self, other: object) -> bool:
        """Compare with other using to_struct()."""
        if not isinstance(other, Frame):
            return False

        if self.context != other.context:
            return False
        return self.to_struct() == other.to_struct()

    def __repr__(self) -> str:
        """Convert to string using doc_struct serialization."""
        name = type(self).__name__
        struct_dump = self.to_struct()
        return f"{name}({self.context},'{struct_dump}')"


class DummyFrame(Frame):
    """Represents an A tag outside of a span.

    Used as target for bookmarks, footnotes and comments.
    """

    def __init__(self, context: ParseContext, tag: str) -> None:
        """Construct an instance."""
        super().__init__(context)
        self.tag = tag

    def handle_end(self, tag: str) -> Optional[Frame]:
        """Handle end tag of a and span tags."""
        if tag == self.tag:
            return self
        else:
            raise UnexpectedHtmlTag(f'Unexpected tag {tag} procesing {self}.')

    def to_struct(self) -> doc_struct.Element:
        """Convert to doc_struct structure."""
        return doc_struct.Element()
