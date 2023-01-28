"""Class to extract document data from HTML export."""

from html import parser
from typing import Optional, List
import logging

from doc_scraper import doc_struct

from . import _base
from . import _document_elements


class ToStructParser(parser.HTMLParser):
    """Parse HTML content into a doc_struct.Document instance."""

    def __init__(self, context: Optional[_base.ParseContext] = None):
        """Create an instance."""
        super().__init__(convert_charrefs=True)

        if context is None:
            context = _base.ParseContext()
        self.context = context
        self.root_frame: Optional[_document_elements.RootFrame] = None
        self.frame_stack: List[_base.Frame] = []

    @property
    def _active_frame(self) -> Optional[_base.Frame]:
        """Return the top (active) frame on the stack."""
        if not self.frame_stack:
            return None
        return self.frame_stack[-1]

    def handle_starttag(self, tag: str, attrs: _base.KeyValueType):
        """Handle the HTML parser's start tag event.

        Delegate to the current frame on the stack.
        """
        if tag == 'html':
            if self.frame_stack:
                raise ValueError('Parsing html tag, but stack not empty.')
            self.root_frame = _document_elements.RootFrame(self.context)
            self.frame_stack.append(self.root_frame)
            return

        top_frame = self._active_frame
        if top_frame is None:
            raise ValueError('Expected items on context stack' +
                             f'processing start tag {tag}, found none.')
        frame: Optional[_base.Frame] = top_frame.handle_start(tag, attrs)
        # print('s', tag, self._last_frame, n)
        if frame:
            self.frame_stack.append(frame)

    def handle_endtag(self, tag: str) -> None:
        """Handle the HTML parser's end tag event.

        Delegate to the current frame on the stack.
        """
        try:
            top_frame = self._active_frame
            if top_frame is None:
                raise _base.UnexpectedHtmlTag(
                    'Expected items on context stack' +
                    f'processing tag {tag}, found none.')
            child_frame: Optional[_base.Frame] = top_frame.handle_end(tag)
            # print('e', tag, child_frame)
            if child_frame is not None:
                self.frame_stack.pop()
                parent_frame = self._active_frame
                if parent_frame:
                    parent_frame.handle_child_end(tag, child_frame)
        except _base.UnexpectedHtmlTag:
            logging.exception('Unmatched tag with frame stack %s',
                              str(self.frame_stack))
            raise

    def handle_data(self, data: str) -> None:
        """Handle the HTML parser's event for content/data.

        Delegate to the current frame on the stack.
        """
        top_frame = self._active_frame
        if top_frame is None:
            # Getting data outside of HTML tags. Ignore.
            return
        top_frame.handle_data(data)

    def as_struct(self) -> doc_struct.Document:
        """Convert the parsed content into a doc_struct."""
        if self.frame_stack:
            raise _base.UnexpectedHtmlTag(
                f'HTML tags not balanced. Remaining: {self.frame_stack[1:]}')
        if self.root_frame is None:
            raise _base.UnexpectedHtmlTag('No HTML document root found.')
        return self.root_frame.to_struct()
