"""
Module to contain common use functions
"""

import ncs

def build_og_list(input):
    """
    Function to turn all inputs into a list of object group names
    """
    object_groups = []

    for item in input.inputs:
        temp_list = []
        temp_list.append(item.device_name)
        temp_list.append(str(item.og_type))
        temp_list.append(item.og_name)
        object_groups.append(temp_list)

    return object_groups
