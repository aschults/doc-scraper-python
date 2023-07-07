"""Test transformation base classes."""

import unittest
import dataclasses
from typing import Optional, Sequence, Tuple, Any

from parameterized import parameterized  # type:ignore

from doc_scraper import doc_transform
from doc_scraper import doc_struct


class SimpleChipTransform(doc_transform.Transformation):
    """Simple chip modification."""

    def _transform_chip(self, chip: doc_struct.Chip) -> doc_struct.Chip:
        """Add a dummmy URL."""
        return dataclasses.replace(chip, text=chip.text, url='a')


class SimpleLinkTransform(doc_transform.Transformation):
    """Simple link modification."""

    def _transform_link(self, link: doc_struct.Link) -> doc_struct.Link:
        """Add a dummmy URL."""
        return dataclasses.replace(link, text=link.text, url='a')


class SimpleParagraphTransform(SimpleChipTransform):
    """Add a style on paragraph to see that transformation worked."""

    def _transform_paragraph_base(
            self, paragraph: doc_struct.Paragraph) -> doc_struct.Paragraph:
        """Add mark to the paragraph."""
        paragraph = dataclasses.replace(paragraph,
                                        style=dict(paragraph.style,
                                                   mark2='modified'))
        return super()._transform_paragraph_base(paragraph)


class AppendTextTransform(doc_transform.Transformation):
    """Append some text at the end of ParagraphElements."""

    def __init__(self, suffix: str) -> None:
        """Construct an instance, passing the suffix to be added."""
        super().__init__()
        self.suffix = suffix

    def _transform_chip_url(self, url: Optional[str]) -> Optional[str]:
        """Add the suffix to Chips URL."""
        if url is None:
            return None
        return url + "-" + self.suffix

    def _transform_paragraph_element_base(
        self, paragraph_element: doc_struct.ParagraphElement
    ) -> doc_struct.ParagraphElement:
        """Append a suffix to the text content."""
        if isinstance(paragraph_element,
                      (doc_struct.TextRun, doc_struct.Chip)):
            return dataclasses.replace(paragraph_element,
                                       text=paragraph_element.text + " " +
                                       self.suffix)
        return paragraph_element

    def _transform_paragraph_element_text(self, text: str) -> str:
        """Add the suffix to all kinds of paragraph elements."""
        return text


class SimpleNotesTransform(doc_transform.Transformation):
    """Add a style to the notes appendix and an index to each element."""

    def _transform_notes_appendix(
            self, notes_appendix: doc_struct.NotesAppendix
    ) -> doc_struct.NotesAppendix:
        """Add mark to the notes appendix."""
        notes_appendix = dataclasses.replace(notes_appendix,
                                             style=dict(notes_appendix.style,
                                                        mark2='modified'))
        return super()._transform_notes_appendix(notes_appendix)

    def _transform_note_item(
            self, index: int,
            paragraph: doc_struct.Paragraph) -> Optional[doc_struct.Paragraph]:
        return dataclasses.replace(paragraph, attrs={'index': index})


class SimpleReferenceTransform(doc_transform.Transformation):
    """Change the link and id of references and targets."""

    def _transform_reference(
            self, ref: doc_struct.Reference) -> doc_struct.Reference:
        return super()._transform_reference(ref)

    def _transform_reference_id(self, ref_id: str) -> str:
        return ref_id + '_another'

    def _transform_link_url(self, url: Optional[str]) -> Optional[str]:
        return (url or '') + '_something'


class BulletItemModifyTransform(SimpleChipTransform):
    """Transform nested bullet items.

    Remove the 2nd item and add one to the end.
    """

    def _transform_bullet_item(
            self, bullet_item: doc_struct.BulletItem) -> doc_struct.BulletItem:
        """Mark all bullet items."""
        bullet_item = dataclasses.replace(bullet_item,
                                          style=dict(bullet_item.style,
                                                     mark0='modified'))
        return super()._transform_bullet_item(bullet_item)

    def _transform_nested_bullet_items(
        self, itemlist: Sequence[doc_struct.BulletItem]
    ) -> Sequence[doc_struct.BulletItem]:
        """Append a bullet item to the nested list."""
        new_item_list = list(itemlist)
        if new_item_list:
            # Don't add to empty to avoid inifite recursion.
            new_item_list.append(
                doc_struct.BulletItem(list_type='li',
                                      elements=[doc_struct.Chip(text='added')],
                                      nested=[],
                                      list_class='last'))
        return super()._transform_nested_bullet_items(new_item_list)

    def _transform_nested_bullet_item(
            self, item_number: int,
            item: doc_struct.BulletItem) -> Optional[doc_struct.BulletItem]:
        """Among the nested items, remove the 2nd item, mark all items."""
        if item_number == 1:
            return None
        new_item = dataclasses.replace(item,
                                       style=dict(
                                           item.style,
                                           location=f'item {item_number}'))
        return super()._transform_nested_bullet_item(item_number, new_item)


class ParagraphModifyTransform(SimpleChipTransform):
    """Transform paragraph items.

    Remove the 2nd item and add one to the end.
    """

    def _transform_paragraph_base(
            self, paragraph: doc_struct.Paragraph) -> doc_struct.Paragraph:
        """Add a style to the paragraph element."""
        new_item = dataclasses.replace(paragraph,
                                       style=dict(paragraph.style,
                                                  mark='modified'))
        return super()._transform_paragraph_base(new_item)

    def _transform_paragraph_elements(
        self, element_list: Sequence[doc_struct.ParagraphElement]
    ) -> Sequence[doc_struct.ParagraphElement]:
        """Append a new line containing a TextRun at the end."""
        new_elements = list(element_list)
        if new_elements:
            # Don't add to empty to avoid inifite recursion.
            new_elements.append(doc_struct.TextRun(text='added'))
        return super()._transform_paragraph_elements(new_elements)

    def _transform_paragraph_elements_item(
        self, location: int, element: doc_struct.ParagraphElement
    ) -> Optional[doc_struct.ParagraphElement]:
        """Remove the second item of the first line, mark all elements."""
        if location == 1:
            return None
        new_element = dataclasses.replace(element,
                                          style=dict(element.style,
                                                     item=f'{location}'))
        return super()._transform_paragraph_elements_item(
            location, new_element)


class TableModifyingTransformation(SimpleParagraphTransform):
    """Modify a table inside the transform."""

    def _transform_table(self, table: doc_struct.Table) -> doc_struct.Table:
        """Add a mark to the table instance."""
        table = dataclasses.replace(table,
                                    style=dict(table.style, mark3='modified'))
        return super()._transform_table(table)

    def _transform_table_cells(
        self, lines: doc_transform.DocContent2dSequence
    ) -> doc_transform.DocContent2dSequence:
        """Append a row to the table."""
        new_lines = list(lines)
        new_lines.append([
            doc_struct.DocContent(attrs={'x': 'added'}, elements=[]),
            doc_struct.DocContent(attrs={'x': 'added'}, elements=[])
        ])
        return super()._transform_table_cells(new_lines)

    def _transform_table_cell_content(
            self, location: Tuple[int, int],
            content: doc_struct.DocContent) -> Optional[doc_struct.DocContent]:
        """Remove second table row, add makrer with cell location."""
        if location[0] == 1:
            return None
        content = dataclasses.replace(
            content,
            style=dict(content.style, location=f'{location[0]}-{location[1]}'))
        return super()._transform_table_cell_content(location, content)


class DocContentModifyingTransformation(SimpleParagraphTransform):
    """Modify DocContent in a transformation."""

    def _transform_doc_content(
            self, doc_content: doc_struct.DocContent) -> doc_struct.DocContent:
        """Mark DocContent elements."""
        doc_content = dataclasses.replace(doc_content,
                                          style=dict(doc_content.style,
                                                     mark4='modified'))
        return super()._transform_doc_content(doc_content)

    def _transform_doc_content_elements(
        self, element_list: Sequence[doc_struct.StructuralElement]
    ) -> Sequence[doc_struct.StructuralElement]:
        """Add a paragraph to the end."""
        new_list = list(element_list)
        new_list.append(doc_struct.Paragraph(attrs={'x': 'added'},
                                             elements=[]))
        return super()._transform_doc_content_elements(new_list)

    def _transform_doc_content_element(
        self, element_number: int, element: doc_struct.StructuralElement
    ) -> Optional[doc_struct.StructuralElement]:
        """Remove the 2nd element and mark all with their position."""
        if element_number == 1:
            return None
        element = dataclasses.replace(element,
                                      style=dict(
                                          element.style,
                                          location=f'item {element_number}'))
        return super()._transform_doc_content_element(element_number, element)


class BulletListModifyingTransformation(SimpleParagraphTransform):
    """Transform Bullet list."""

    def _transform_bullet_list(
            self, bullet_list: doc_struct.BulletList) -> doc_struct.BulletList:
        """Mark bullet list in styles."""
        bullet_list = dataclasses.replace(bullet_list,
                                          style=dict(bullet_list.style,
                                                     mark5='modified'))
        return super()._transform_bullet_list(bullet_list)

    def _transform_bullet_list_items(
        self, item_list: Sequence[doc_struct.BulletItem]
    ) -> Sequence[doc_struct.BulletItem]:
        """Add a bullet list item to the end."""
        new_list = list(item_list)
        new_list.append(
            doc_struct.BulletItem(attrs={'x': 'added'},
                                  list_type='li',
                                  elements=[],
                                  nested=[]))
        return super()._transform_bullet_list_items(new_list)

    def _transform_bullet_list_item(
            self, item_number: int,
            item: doc_struct.BulletItem) -> Optional[doc_struct.BulletItem]:
        """Remove the first bullet item, mark with their position."""
        if item_number == 1:
            return None
        item = dataclasses.replace(item,
                                   style=dict(item.style,
                                              location=f'item {item_number}'))
        return super()._transform_bullet_list_item(item_number, item)


class ModifyAllElementsTransform(doc_transform.Transformation):
    """Add an attribute to all of the elements."""

    def _transform_element_base(
            self, element: doc_struct.Element) -> doc_struct.Element:
        """Process all elements, adding an attribute."""
        return dataclasses.replace(element, attrs={'x': 1})


class PathAwareTextTransform(doc_transform.Transformation):
    """Add text runs based on supplied path in the context."""

    @classmethod
    def _format_path_item(cls, path_segment: str,
                          element: doc_struct.Element) -> str:
        type_name = type(element).__name__
        ref = element.style.get('ref', '-')
        return f'{path_segment}:{type_name}({ref})'

    def _transform_paragraph_element_base(
        self, paragraph_element: doc_struct.ParagraphElement
    ) -> doc_struct.ParagraphElement:
        """Insert the traversed path into a Text run."""
        if isinstance(paragraph_element,
                      (doc_struct.TextRun, doc_struct.Chip)):
            new_text = "\n".join(
                (self._format_path_item(path_segment, element)
                 for path_segment, element in zip(self.context.path,
                                                  self.context.path_objects)))
            return dataclasses.replace(paragraph_element, text=new_text)
        return paragraph_element


###########################################################################
# Test cases
###########################################################################


class ParagraphElementTransformationTest(unittest.TestCase):
    """Test the paragraph element transform class."""

    @parameterized.expand([  # type:ignore
        (doc_struct.Chip(text='xxx'), doc_struct.Chip(text='xxx', url='a')),
        (doc_struct.TextRun(text='xxx'), doc_struct.TextRun(text='xxx')),
    ])
    def test_simple_chip(self, data: doc_struct.ParagraphElement,
                         expected: doc_struct.ParagraphElement):
        """Test simple transformation."""
        self.assertEqual(expected, SimpleChipTransform()(data))

    @parameterized.expand([  # type:ignore
        (doc_struct.Link(text='xxx'), doc_struct.Link(text='xxx', url='a')),
        (doc_struct.TextRun(text='xxx'), doc_struct.TextRun(text='xxx')),
    ])
    def test_simple_link(self, data: doc_struct.ParagraphElement,
                         expected: doc_struct.ParagraphElement):
        """Test simple transformation."""
        self.assertEqual(expected, SimpleLinkTransform()(data))

    @parameterized.expand([  # type:ignore
        (doc_struct.Chip(text='xxx'), doc_struct.Chip(text='xxx transformed')),
        (
            doc_struct.Chip(text='xxx', url='a'),
            doc_struct.Chip(text='xxx transformed', url='a-transformed'),
        ),
        (
            doc_struct.TextRun(text='yyy'),
            doc_struct.TextRun(text='yyy transformed'),
        ),
    ])
    def test_text_transform(self, data: doc_struct.ParagraphElement,
                            expected: doc_struct.ParagraphElement):
        """Test text transform for multiple types."""
        self.assertEqual(expected, AppendTextTransform('transformed')(data))


class TransformationTest(unittest.TestCase):
    """Parametrized transformation tests."""

    @parameterized.expand([  # type:ignore
        (
            'Simple paragraph',
            doc_struct.Paragraph(elements=[
                doc_struct.Chip(text='yyy'),
                doc_struct.TextRun(text='abc'),
                doc_struct.Chip(text='zzz'),
            ]),
            doc_struct.Paragraph(elements=[
                doc_struct.Chip(text='yyy', url='a'),
                doc_struct.TextRun(text='abc'),
                doc_struct.Chip(text='zzz', url='a'),
            ]),
            SimpleChipTransform(),
        ),
        (
            'Simple note appendix',
            doc_struct.NotesAppendix(elements=[
                doc_struct.Paragraph(elements=[]),
                doc_struct.Paragraph(elements=[]),
            ]),
            doc_struct.NotesAppendix(
                style={'mark2': 'modified'},
                elements=[
                    doc_struct.Paragraph(attrs={'index': 0}, elements=[]),
                    doc_struct.Paragraph(attrs={'index': 1}, elements=[]),
                ]),
            SimpleNotesTransform(),
        ),
        (
            'Simple reference and target',
            doc_struct.Paragraph(elements=[
                doc_struct.Reference(text='yyy', url='http://link'),
                doc_struct.ReferenceTarget(text='zzz', ref_id='#here'),
            ]),
            doc_struct.Paragraph(elements=[
                doc_struct.Reference(text='yyy', url='http://link_something'),
                doc_struct.ReferenceTarget(text='zzz', ref_id='#here_another'),
            ]),
            SimpleReferenceTransform(),
        ),
        (
            'Nested bullets test',
            doc_struct.BulletItem(
                elements=[],
                list_type='li',
                nested=[
                    doc_struct.BulletItem(elements=[
                        doc_struct.Chip(text='first'),
                    ],
                                          list_type='li'),
                    doc_struct.BulletItem(elements=[
                        doc_struct.Chip(text='second'),
                    ],
                                          list_type='li'),
                ],
            ),
            doc_struct.BulletItem(
                style={'mark0': 'modified'},
                elements=[],
                list_type='li',
                nested=[
                    doc_struct.BulletItem(
                        style={
                            'location': 'item 0',
                            'mark0': 'modified'
                        },
                        left_offset=None,
                        elements=[doc_struct.Chip(text='first', url='a')],
                        list_type='li',
                        nested=[]),
                    doc_struct.BulletItem(
                        style={
                            'location': 'item 2',
                            'mark0': 'modified'
                        },
                        elements=[doc_struct.Chip(text='added', url='a')],
                        level=None,
                        list_type='li',
                        list_class='last',
                        nested=[])
                ]),
            BulletItemModifyTransform(),
        ),
        ('Paragraph test',
         doc_struct.Paragraph(elements=[
             doc_struct.TextRun(text='first first'),
             doc_struct.TextRun(text='first second'),
             doc_struct.Chip(text='first third'),
         ],),
         doc_struct.Paragraph(style={'mark': 'modified'},
                              elements=[
                                  doc_struct.TextRun(style={'item': '0'},
                                                     text='first first'),
                                  doc_struct.Chip(style={'item': '2'},
                                                  text='first third',
                                                  url='a'),
                                  doc_struct.TextRun(style={'item': '3'},
                                                     text='added')
                              ]), ParagraphModifyTransform()),
        (
            'Paragraph test',
            doc_struct.DocContent(elements=[
                doc_struct.Paragraph(elements=[
                    doc_struct.Chip(text='yyy'),
                    doc_struct.TextRun(text='abc'),
                    doc_struct.Chip(text='zzz'),
                ])
            ]),
            doc_struct.DocContent(elements=[
                doc_struct.Paragraph(style={'mark2': 'modified'},
                                     elements=[
                                         doc_struct.Chip(text='yyy', url='a'),
                                         doc_struct.TextRun(text='abc'),
                                         doc_struct.Chip(text='zzz', url='a'),
                                     ])
            ]),
            SimpleParagraphTransform(),
        ),
        ('Table Test',
         doc_struct.Table(elements=[
             [
                 doc_struct.DocContent(elements=[
                     doc_struct.Paragraph(
                         elements=[doc_struct.Chip(text='cell 0,0')])
                 ]),
                 doc_struct.DocContent(elements=[
                     doc_struct.Paragraph(
                         elements=[doc_struct.TextRun(text='cell 0,1')])
                 ])
             ],
             [
                 doc_struct.DocContent(elements=[
                     doc_struct.Paragraph(
                         elements=[doc_struct.Chip(text='cell 1,0')])
                 ]),
                 doc_struct.DocContent(elements=[
                     doc_struct.Paragraph(
                         elements=[doc_struct.TextRun(text='cell 1,1')])
                 ])
             ],
             [
                 doc_struct.DocContent(elements=[
                     doc_struct.Paragraph(
                         elements=[doc_struct.Chip(text='cell 2,0')])
                 ]),
                 doc_struct.DocContent(elements=[
                     doc_struct.Paragraph(
                         elements=[doc_struct.TextRun(text='cell 2,1')])
                 ])
             ],
         ]),
         doc_struct.Table(
             style={'mark3': 'modified'},
             elements=[
                 [
                     doc_struct.DocContent(attrs={},
                                           style={'location': '0-0'},
                                           elements=[
                                               doc_struct.Paragraph(
                                                   style={'mark2': 'modified'},
                                                   elements=[
                                                       doc_struct.Chip(
                                                           text='cell 0,0',
                                                           url='a')
                                                   ])
                                           ]),
                     doc_struct.DocContent(
                         style={
                             'location': '0-1',
                         },
                         elements=[
                             doc_struct.Paragraph(
                                 style={'mark2': 'modified'},
                                 elements=[
                                     doc_struct.TextRun(text='cell 0,1')
                                 ])
                         ]),
                 ],
                 [
                     doc_struct.DocContent(style={'location': '2-0'},
                                           elements=[
                                               doc_struct.Paragraph(
                                                   style={'mark2': 'modified'},
                                                   elements=[
                                                       doc_struct.Chip(
                                                           text='cell 2,0',
                                                           url='a')
                                                   ])
                                           ]),
                     doc_struct.DocContent(
                         style={
                             'location': '2-1',
                         },
                         elements=[
                             doc_struct.Paragraph(
                                 style={'mark2': 'modified'},
                                 elements=[
                                     doc_struct.TextRun(text='cell 2,1')
                                 ])
                         ]),
                 ],
                 [
                     doc_struct.DocContent(attrs={'x': 'added'},
                                           style={'location': '3-0'},
                                           elements=[]),
                     doc_struct.DocContent(attrs={'x': 'added'},
                                           style={'location': '3-1'},
                                           elements=[]),
                 ],
             ]), TableModifyingTransformation()),
        (
            'Doc Content Test',
            doc_struct.DocContent(elements=[
                doc_struct.Paragraph(elements=[doc_struct.Chip(text='par 0')]),
                doc_struct.Paragraph(
                    elements=[doc_struct.TextRun(text='par 1')]),
                doc_struct.Paragraph(elements=[doc_struct.Chip(text='par 2')]),
            ],),
            doc_struct.DocContent(
                attrs={},
                style={'mark4': 'modified'},
                elements=[
                    doc_struct.Paragraph(
                        attrs={},
                        style={
                            'location': 'item 0',
                            'mark2': 'modified'
                        },
                        left_offset=None,
                        elements=[doc_struct.Chip(text='par 0', url='a')]),
                    doc_struct.Paragraph(
                        style={
                            'location': 'item 2',
                            'mark2': 'modified'
                        },
                        left_offset=None,
                        elements=[doc_struct.Chip(text='par 2', url='a')]),
                    doc_struct.Paragraph(attrs={'x': 'added'},
                                         style={
                                             'location': 'item 3',
                                             'mark2': 'modified'
                                         },
                                         left_offset=None,
                                         elements=[])
                ]),
            DocContentModifyingTransformation(),
        ),
        (
            'Bullet List test',
            doc_struct.BulletList(items=[
                doc_struct.BulletItem(list_type='li',
                                      elements=[
                                          doc_struct.Chip(text='par 0'),
                                      ]),
                doc_struct.BulletItem(
                    list_type='li',
                    elements=[doc_struct.TextRun(text='par 1')]),
                doc_struct.BulletItem(
                    list_type='li',
                    elements=[doc_struct.Chip(text='par 2')],
                    nested=[
                        doc_struct.BulletItem(
                            list_type='li',
                            elements=[doc_struct.Chip(text='par 2.1')]),
                    ]),
            ],),
            doc_struct.BulletList(
                style={'mark5': 'modified'},
                items=[
                    doc_struct.BulletItem(
                        style={
                            'location': 'item 0',
                            'mark2': 'modified'
                        },
                        elements=[doc_struct.Chip(text='par 0', url='a')],
                        list_type='li',
                        nested=[]),
                    doc_struct.BulletItem(
                        style={
                            'location': 'item 2',
                            'mark2': 'modified'
                        },
                        elements=[doc_struct.Chip(text='par 2', url='a')],
                        list_type='li',
                        nested=[
                            doc_struct.BulletItem(style={'mark2': 'modified'},
                                                  elements=[
                                                      doc_struct.Chip(
                                                          text='par 2.1',
                                                          url='a')
                                                  ],
                                                  list_type='li',
                                                  nested=[])
                        ]),
                    doc_struct.BulletItem(attrs={'x': 'added'},
                                          style={
                                              'location': 'item 3',
                                              'mark2': 'modified'
                                          },
                                          elements=[],
                                          list_type='li',
                                          nested=[]),
                ]),
            BulletListModifyingTransformation(),
        ),
        (
            'Simple document transform',
            doc_struct.Document(
                shared_data=doc_struct.SharedData(),
                content=doc_struct.DocContent(elements=[
                    doc_struct.Paragraph(
                        elements=[doc_struct.Chip(text='text')])
                ])),
            doc_struct.Document(
                shared_data=doc_struct.SharedData(),
                content=doc_struct.DocContent(elements=[
                    doc_struct.Paragraph(
                        style={'mark2': 'modified'},
                        elements=[doc_struct.Chip(text='text', url='a')])
                ])),
            SimpleParagraphTransform(),
        ),
        (
            'All elements transform',
            doc_struct.Document(
                shared_data=doc_struct.SharedData(),
                content=doc_struct.DocContent(elements=[
                    doc_struct.Paragraph(elements=[
                        doc_struct.Chip(text='text'),
                        doc_struct.TextRun(text='text2')
                    ]),
                    doc_struct.BulletList(items=[
                        doc_struct.BulletItem(elements=[], list_type='li')
                    ]),
                    doc_struct.Table(elements=[])
                ])),
            doc_struct.Document(
                attrs={'x': 1},
                shared_data=doc_struct.SharedData(attrs={'x': 1}),
                content=doc_struct.DocContent(
                    attrs={'x': 1},
                    elements=[
                        doc_struct.Paragraph(
                            attrs={'x': 1},
                            elements=[
                                doc_struct.Chip(attrs={'x': 1}, text='text'),
                                doc_struct.TextRun(attrs={'x': 1},
                                                   text='text2')
                            ]),
                        doc_struct.BulletList(attrs={'x': 1},
                                              items=[
                                                  doc_struct.BulletItem(
                                                      attrs={'x': 1},
                                                      elements=[],
                                                      list_type='li')
                                              ]),
                        doc_struct.Table(attrs={'x': 1}, elements=[])
                    ])),
            ModifyAllElementsTransform(),
        ),
    ])
    # pylint: disable=unused-argument
    def test_transform(self, name: str, data: Any, expected: Any,
                       transform: doc_transform.Transformation):
        """Test bullet list transformation."""
        print(expected)
        print(transform(data))
        self.assertEqual(expected, transform(data))

    @parameterized.expand([  # type:ignore
        (
            'Simple paragraph',
            doc_struct.Paragraph(style={'ref': 'a'},
                                 elements=[
                                     doc_struct.TextRun(style={'ref': 'b'},
                                                        text='to be replaced'),
                                 ]),
            doc_struct.Paragraph(style={'ref': 'a'},
                                 elements=[
                                     doc_struct.TextRun(
                                         style={'ref': 'b'},
                                         text='.:Paragraph(a)\n0:TextRun(b)'),
                                 ]),
            PathAwareTextTransform(),
        ),
        (
            'Two paragraphs',
            doc_struct.DocContent(
                style={'ref': 'a'},
                elements=[
                    doc_struct.Paragraph(style={'ref': 'aa'},
                                         elements=[
                                             doc_struct.TextRun(
                                                 style={'ref': 'aaa'},
                                                 text='to be replaced'),
                                         ]),
                    doc_struct.Paragraph(style={'ref': 'ab'},
                                         elements=[
                                             doc_struct.TextRun(
                                                 style={'ref': 'aba'},
                                                 text='to be replaced'),
                                         ]),
                ]),
            doc_struct.DocContent(
                style={'ref': 'a'},
                elements=[
                    doc_struct.Paragraph(
                        style={'ref': 'aa'},
                        elements=[
                            doc_struct.TextRun(
                                style={'ref': 'aaa'},
                                text='.:DocContent(a)\n' +
                                '0:Paragraph(aa)\n0:TextRun(aaa)'),
                        ]),
                    doc_struct.Paragraph(
                        style={'ref': 'ab'},
                        elements=[
                            doc_struct.TextRun(
                                style={'ref': 'aba'},
                                text='.:DocContent(a)\n' +
                                '1:Paragraph(ab)\n0:TextRun(aba)'),
                        ]),
                ]),
            PathAwareTextTransform(),
        ),
        (
            'Section and paragraph',
            doc_struct.Section(
                style={'ref': 'a'},
                heading=doc_struct.Heading(
                    level=1,
                    style={'ref': 'ah'},
                    elements=[
                        doc_struct.TextRun(style={'ref': 'aha'},
                                           text='to be replaced'),
                    ],
                ),
                content=[
                    doc_struct.Paragraph(
                        style={'ref': 'aa'},
                        elements=[
                            doc_struct.TextRun(style={'ref': 'aaa'},
                                               text='to be replaced'),
                        ],
                    ),
                ],
            ),
            doc_struct.Section(
                style={'ref': 'a'},
                heading=doc_struct.Heading(
                    level=1,
                    style={'ref': 'ah'},
                    elements=[
                        doc_struct.TextRun(
                            style={'ref': 'aha'},
                            text='.:Section(a)\n' +
                            'heading:Heading(ah)\n0:TextRun(aha)'),
                    ],
                ),
                content=[
                    doc_struct.Paragraph(
                        style={'ref': 'aa'},
                        elements=[
                            doc_struct.TextRun(
                                style={'ref': 'aaa'},
                                text='.:Section(a)\n' +
                                '0:Paragraph(aa)\n0:TextRun(aaa)'),
                        ],
                    ),
                ],
            ),
            PathAwareTextTransform(),
        ),
        (
            'Table and paragraph',
            doc_struct.DocContent(
                style={'ref': 'a'},
                elements=[
                    doc_struct.Table(
                        style={'ref': 'aa'},
                        elements=[[
                            doc_struct.DocContent(
                                style={
                                    'ref': 'aaa',
                                },
                                elements=[
                                    doc_struct.Paragraph(
                                        style={
                                            'ref': 'a4',
                                        },
                                        elements=[
                                            doc_struct.TextRun(
                                                style={'ref': 'a5'},
                                                text='to be replaced'),
                                        ]),
                                ]),
                        ]]),
                    doc_struct.Paragraph(style={'ref': 'ab'},
                                         elements=[
                                             doc_struct.TextRun(
                                                 style={'ref': 'aba'},
                                                 text='to be replaced'),
                                         ]),
                ]),
            doc_struct.DocContent(
                style={'ref': 'a'},
                elements=[
                    doc_struct.Table(
                        style={'ref': 'aa'},
                        elements=[[
                            doc_struct.DocContent(
                                style={
                                    'ref': 'aaa',
                                },
                                elements=[
                                    doc_struct.Paragraph(
                                        style={
                                            'ref': 'a4',
                                        },
                                        elements=[
                                            doc_struct.TextRun(
                                                style={'ref': 'a5'},
                                                text='.:DocContent(a)\n' +
                                                '0:Table(aa)\n' +
                                                '0,0:DocContent(aaa)\n' +
                                                '0:Paragraph(a4)\n' +
                                                '0:TextRun(a5)'),
                                        ]),
                                ]),
                        ]]),
                    doc_struct.Paragraph(
                        style={'ref': 'ab'},
                        elements=[
                            doc_struct.TextRun(
                                style={'ref': 'aba'},
                                text='.:DocContent(a)\n' +
                                '1:Paragraph(ab)\n0:TextRun(aba)'),
                        ]),
                ]),
            PathAwareTextTransform(),
        ),
    ])
    # pylint: disable=unused-argument
    def test_transform_with_context(self, name: str, data: Any, expected: Any,
                                    transform: doc_transform.Transformation):
        """Test bullet list transformation."""
        print(expected)
        print(transform(data))
        self.assertEqual(expected, transform(data))
