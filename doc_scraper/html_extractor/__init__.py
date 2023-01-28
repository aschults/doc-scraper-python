"""Extraction of doc_struct classes from Google Docs HTML export.

Background
    Google Docs API provides functionality to fetch documents
    in JSON format. However smart chips, which are very useful
    to manage structuredinformation in docs, are not included.

    However in the HTML export via Drive API, chips, as well as
    most other constructs are recognizable.

    Note also that the HTML export is structurally closely
    aligned with the JSON document form, thus making paring easier
    than for general HTML documents.

General concepts:

*   `ToStructParser`: Simple parser based on parser.HTMLParser.
    Walks through a Google Drive HTML export and delegates
    processing to ParserFrame. ParserFrames are tracked in the
    parser to ensure the correct frame is used when going trhough the
    HTML document.

*   `ParserFrame`: Provides functionality to process a part of an
    HTML document, based on a specific tag (e.g. ParagraphFrame for
    all within `<p>....</p>`)

*   _Frame stack_ : The Parser keeps track of the current frame in
    form of a stack of frames. Encountering an HTML opening tag (in a
    frame) may cause the a new frame to land on top of the stack, thus
    providing a new active frame. Certain closing tags can remove
    the current frame (i.e. themselves).

*   `Root`: The top frame to parse HTML documents is (unsurprisingly)
    the root frame. It is pushed onto the frame stack, when encountering
    `<html>`.

*   `to_struct()`: The frames store the parsed details in their instances.
    Once the parsing is completed, to_struct() allows to convert the
    stored information to a doc_struc.Element tree.
"""


from ._extractor import ToStructParser

_ = [ToStructParser]
