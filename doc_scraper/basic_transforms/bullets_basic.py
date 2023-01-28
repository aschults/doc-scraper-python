"""Transform bullet lists into nested structure."""
import dataclasses
from typing import List, Optional, Sequence

from doc_scraper import doc_struct

from doc_scraper import doc_transform


def _nest_items(
        level: int, items: Sequence[doc_struct.BulletItem]
) -> Sequence[doc_struct.BulletItem]:
    """Nest the flat list of bullet items by indention level.

    Implemented as recursion of this function, only passing
    `items` of higher `level` into the recursion.

    Items _at_ `level` are used to divide the items list, and
    returned containing all of the nested items.
    """
    result: List[doc_struct.BulletItem] = []
    last_matched_index = len(items)

    # Go through the list backward until we hit an item at the
    # passed level and process all nested items recursively.
    for i in range(len(items) - 1, -1, -1):
        element = items[i]
        if (element.level or 0) < level:
            raise ValueError('Items list containing lower level ' +
                             f'{element.level} than processed {level}')
        if element.level == level:
            items_below = items[i + 1:last_matched_index]
            if items_below:
                nested_items = _nest_items(level + 1, items_below)
                element = dataclasses.replace(element, nested=nested_items)
                items_below = []
            result.append(element)
            last_matched_index = i

    if last_matched_index != 0:
        # If the first item is not at the passed level, insert
        # a bullet item with not content or style/class to ensure
        # the nested structure matches the indention.
        items_below = items[:last_matched_index]
        nested_items = _nest_items(level + 1, items_below)
        wrapper_item = doc_struct.BulletItem(attrs={},
                                             style={},
                                             elements=[],
                                             level=level,
                                             left_offset=-1,
                                             list_type='empty',
                                             nested=nested_items,
                                             list_class="")
        result.append(wrapper_item)
    return list(reversed(result))


def _merge_bullet_lists(
    element_list: Sequence[doc_struct.StructuralElement]
) -> Sequence[doc_struct.StructuralElement]:
    """Merge consecutive bullet lists into one.

    Implemented by going through a list of structural elements
    and replacing sequences of BulletList by a single one.
    """
    result: List[doc_struct.StructuralElement] = []
    matching_lists: List[doc_struct.BulletList] = []
    for element in element_list:
        if isinstance(element, doc_struct.BulletList):
            matching_lists.append(element)
        else:
            if matching_lists:
                first_match = matching_lists[0]
                bullet_items = [
                    item for bullet_list in matching_lists
                    for item in bullet_list.items
                ]
                result.append(
                    dataclasses.replace(first_match, items=bullet_items))
                matching_lists = []
            result.append(element)
    if matching_lists:
        first_match = matching_lists[0]
        bullet_items = [
            item for bullet_list in matching_lists
            for item in bullet_list.items
        ]
        result.append(dataclasses.replace(first_match, items=bullet_items))
    return result


class BulletsTransform(doc_transform.Transformation):
    """Merge Bullet lists and nest bullet items by indention.

    E.g.:
    ```
    BulletList(elements=[
        BulletItem(level=1,...),
        BulletItem(level=2,...)
    ])
    BulletList(elements=[
        BulletItem(level=2,...),
        BulletItem(level=3,...)
    ])
    ```
    is transformed into
    ```
    BulletList(elements=[
        BulletItem(level=1, nested=[
                BulletItem(level=2,...),
                BulletItem(level=2, nested=[
                        BulletItem(level=3,...)
                    ]),
            ]),
    ])
    ```
    """

    def __init__(
        self,
        context: Optional[doc_transform.TransformationContext] = None,
    ) -> None:
        """Create the instance."""
        super().__init__(context)

    def _transform_bullet_list(
            self, bullet_list: doc_struct.BulletList) -> doc_struct.BulletList:
        """Nest bullet items.

        This is called after merging the bullet lists.
        """
        return dataclasses.replace(bullet_list,
                                   items=_nest_items(0, bullet_list.items))

    def _transform_doc_content_elements(
        self, element_list: Sequence[doc_struct.StructuralElement]
    ) -> Sequence[doc_struct.StructuralElement]:
        """Merge bullet lists in a doc content."""
        return super()._transform_doc_content_elements(
            _merge_bullet_lists(element_list))
