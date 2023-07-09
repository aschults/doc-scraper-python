"""Classes for basic sections and headings transforms."""

from typing import List, Optional, Sequence

from doc_scraper import doc_struct

from doc_scraper import doc_transform


def _structure_doc(
        level: int, heading: Optional[doc_struct.Heading],
        items: Sequence[doc_struct.StructuralElement]) -> doc_struct.Section:
    """Convert a list of structural elements into a section.

    Args:
        level: The level at which the new section items are to be.
            To be the parent's level +1.
        heading: The heading that opened the section. Needs to be
            at least at level -1. If larger than level, a wrapper section
            is returned.
        items: Structual elements at level or greater.
            Items before the first heading are considered at level as well.

    Return:
        Section containing a heading at level l and only items at level.
            higher level items are wrapped into a Section at level.
    """
    if heading and level < heading.level:
        # The heading encountered is skipping a level.
        return doc_struct.Section(
            heading=None, content=[_structure_doc(level + 1, heading, items)])

    intro_elements: List[doc_struct.StructuralElement] = []
    first_heading_index: int = -1
    for index, item in enumerate(items):
        if isinstance(item, doc_struct.Heading):
            first_heading_index = index
            break
    if first_heading_index == -1:
        first_heading_index = len(items)
    intro_elements += items[0:first_heading_index]

    level_sections: List[doc_struct.StructuralElement] = []
    last_heading_index: int = len(items)
    for index in range(len(items) - 1, first_heading_index - 1, -1):
        item = items[index]
        if isinstance(item, doc_struct.Heading):
            if item.level < level:
                raise ValueError(
                    f'Should not see headings lower than level {level}.')
            if item.level == level:
                # A heading we need to react to.
                new_items = items[index + 1:last_heading_index]
                level_sections.append(
                    _structure_doc(level + 1, item, new_items))
                last_heading_index = index

    if last_heading_index != first_heading_index:
        # Section started with heading > level.
        new_items = items[first_heading_index:last_heading_index]
        level_sections.append(_structure_doc(level + 1, None, new_items))

    level_sections.reverse()
    return doc_struct.Section(heading=heading,
                              content=intro_elements + level_sections)


class SectionNestingTransform(doc_transform.Transformation):
    """Transform a document to nest text by heading level.

    Introduces doc_stuct.Section elements, containing heading and content.
    Inside the content, Section instances for lower headings (i.e. higher level
    number) are nested.

    E.g.
    ```
    Heading(level=1,...)
    Paragraph(...)
    Heading(level=2,...)
    BulletList(...)
    ```
    is transformed into
    ```
    Section(
        heading=Heading(level=1,...),
        content=[
            Paragraph(...),
            Section(
                heading=Heading(level=2,...),
                content=[BulletList(...)]
            )
        ]
    )
    ```
    """

    def _transform_doc_content_elements(
        self, element_list: Sequence[doc_struct.StructuralElement]
    ) -> Sequence[doc_struct.StructuralElement]:
        """Transform the document."""
        element_list = super()._transform_doc_content_elements(element_list)
        top_section = _structure_doc(1, None, element_list)
        return top_section.content
