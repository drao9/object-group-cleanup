"""
Title:
    - Module for IOS Device Type

Developed by:
    - Axel Perez axperez@cisco.com

Description:
    - Functions that are specific to the IOS device type that replace the absract methods
      inherited by the AbsCommon class.
"""
import ncs
import _ncs
from .abs_common import AbsCommon

class IOScleanup(AbsCommon):
    """
    Class specific to IOS devices with methods that replace the abstract methods inherited
    by the AbsCommon class.
    """
    def __init__(self):
        """
        The group attribute must be the ned-id (root.devices.device[device].device_type.cli.ned_id)
        which for ASA devices is "cisco-asa". If group is not the ned-id for the device type, then
        the create_modules() function in helpers.py must be changed since the dictionary returned
        is keyed by device type's ned-id.
        """
        self.group = "cisco-ios"

    def delete_obj(self, box, root, og_id, og_type):
        """
        A function that deletes IOS object groups from the inputted device's object group list.
        """
        del root.devices.device[box].config.ios__object_group[og_type][og_id]

    def obj_list_conversion(self, box, root):
        """
        A function that converts the specific device type's object group list to
        a python dictionary with the object group name as the key and the object
        group's type as the value. This is returned:
        1. obj_dict:    A python dictionary that contains all of the object groups as
                        keys and their types as values.
        """
        obj_dict = {}
        #Adding all of the object groups and their types to python lists
        for ogtyp in root.devices.device[box].config.ios__object_group:
            for obj in root.devices.device[box].config.ios__object_group[ogtyp]:
                obj_dict[obj.name] = str(obj)

        return obj_dict

    def acl_list_conversion(self, box, root):
        """
        A function that converts the specific device type's access list (or list
        that has to be checked against) to a python dictionary with the access
        lists as keys and their rules in a list as the value. This is returned:
        FOR IOS: 'ext-named_acl' is the only access list with object groups that I know of
        for now.
        1. acl_dict:    A python dictionary that contains all of the access lists as
                        keys and their rules that contain object groups in a list as values.
        """
        acl_dict = {}

        acl_dict['ext-named-acl'] = []
        for rul in root.devices.device[box].config.ios__ip.access_list.extended.ext_named_acl:
            if "object-group" in rul.id:
                acl_dict['ext-named-acl'].append(rul)

        return acl_dict

    def rec_group_og(self, used_group_ogs, root, box, og, typ):
        """
        A recursive function that adds a used object group's group-objects (object groups inside
        of object groups) to a set (used_group_ogs) and recursively recalls itself to check if
        the group objects added have any group objects themselves to add as well.
        ----IOS Device does not seem to have group objects.----
        It returns:
        1. used_group_ogs: Set of used group-objects that should not be removed.
        """
        return used_group_ogs
