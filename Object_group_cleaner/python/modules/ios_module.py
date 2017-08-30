import ncs
import _ncs
from .abs_common import AbsCommon

class IOScleanup(AbsCommon):

    def __init__(self):
        self.group = "cisco-ios"

    def delete_obj(box, root, og_id, og_type):
        del root.devices.device[box].config.ios__object_group[og_type][og_id]

    def obj_list_conversion(box, root):
        obj_dict = {}
        #Adding all of the object groups and their types to python lists
        for ogtyp in root.devices.device[box].config.ios__object_group:
            for og in root.devices.device[box].config.ios__object_group[ogtyp]:
                obj_dict[og.id] = str(og)

        return obj_dict

    def acl_list_conversion(box, root):
        acl_dict = {}
        for acl in root.devices.device[box].config.ios__access_list.access_list_id:
            acl_dict[acl] = []
            for rul in root.devices.device[box].config.ios__access_list.access_list_id[acl.id].rule:
                if "object-group" in rul.id:
                    acl_dict[acl].append(rul)

        return acl_dict

    def rec_group_og(used_group_ogs, root, box, og, typ):
        """
        A recursive function that adds a used object group's group-objects (object groups inside
        of object groups) to a set (used_group_ogs) and recursively recalls itself to check if
        the group objects added have any group objects themselves to add as well. It returns:
        1. used_group_ogs: Set of used group-objects that should not be removed.
        """
        if root.devices.device[box].config.ios__object_group[typ][og].group_object:
            for group_og in root.devices.device[box].config.ios__object_group[typ][og].group_object:
                used_group_ogs.add(group_og.id)
                used_group_ogs = rec_group_og(used_group_ogs, root, box, group_og.id, typ)

        return used_group_ogs
