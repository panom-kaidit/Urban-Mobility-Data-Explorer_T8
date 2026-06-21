"""
Merge Sort : sorts a list of dicts by a given key, without using
Python's built-in sorted() or list.sort().

Repeatedly splits the list in half, sorts each half, then merges them
back in order. A list of 0 or 1 items is already sorted, so that's
the base case.

Time complexity: O(n log n), space complexity: O(n).
"""


def comes_first(first_item, second_item, sort_key, descending):
    """
    Returns True if a should come before b in the sorted output.
    Larger values come first (descending order).
    """
    first_value = first_item[sort_key]
    second_value = second_item[sort_key]

    if descending:
        return first_value >= second_value

    return first_value <= second_value


def merge(left_list, right_list, sort_key, descending=True):
    """
    Merge two sorted lists into one, picking the next item from whichever
    list has the smaller (or larger) value at the front.
    """
    merged_list = []
    left_index = 0
    right_index = 0

    # While there are still items in both lists, pick the next item from the front of one of the lists and add it to the merged list.
    while left_index < len(left_list) and right_index < len(right_list):
        left_item = left_list[left_index]
        right_item = right_list[right_index]

        if comes_first(
            left_item,
            right_item,
            sort_key,
            descending,
        ):
            merged_list.append(left_item)
            left_index = left_index + 1
        else:
            merged_list.append(right_item)
            right_index = right_index + 1

    # Add any remaining items from the left list.
    while left_index < len(left_list):
        merged_list.append(left_list[left_index])
        left_index = left_index + 1

    # Add any remaining items from the right list.
    while right_index < len(right_list):
        merged_list.append(right_list[right_index])
        right_index = right_index + 1

    return merged_list


def merge_sort(items, sort_key, descending=True):
    """
    Splits the list in half, recursively sorts each half, then merges them back together.
    """
    if len(items) <= 1:
        return items

    middle_index = len(items) // 2

    # Divide step: split the list into two halves.
    left_half = items[:middle_index]
    right_half = items[middle_index:]

    # Sorting step: recursively sort both halves.
    sorted_left_half = merge_sort(left_half, sort_key, descending)
    sorted_right_half = merge_sort(right_half, sort_key, descending)

    # Merge step: combine both sorted halves into one sorted list.
    return merge(sorted_left_half, sorted_right_half, sort_key, descending)
