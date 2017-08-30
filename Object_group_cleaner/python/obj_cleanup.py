import socket
import ncs
import _ncs

def cleanup_or_search(box, to_del):
    """
    A function that deletes all of the unused object groups in the necessary
    order from the inputted device. It returns:
    1. ret: A dictionary with all of the deleted object groups organized by type.
    2. stat: A string that contains the status of the deletion (Success or specific ncs error).
    """
    #Initializing python lists and sets
    og_list = []
    og_typ = []
    acl_list = []
    ret = {}
    used_group_ogs = set()
    orphaned_ogs = set()
    orphaned_dict = {}
    #delete_first = set()

    #Creating transaction and setting root to access NSO
    with ncs.maapi.single_write_trans('ncsadmin', 'python', groups=['ncsadmin']) as tran:
        root = ncs.maagic.get_root(tran)

        #Converting access lists and object group list to python lists
        og_list, og_typ, acl_list = nso_to_python(box, root, og_list, og_typ, acl_list)

        #Finding the unused object groups and placing them in sets for prioritization
        orphaned_ogs, used_group_ogs, orphaned_dict = find_orphaned_og(root,
        box, og_list, og_typ, acl_list, used_group_ogs, orphaned_ogs, orphaned_dict)

        #Prioritize which orphaned object groups need to be deleted first
        #delete_first, delete_second = prioritize_del(orphaned_ogs, used_group_ogs, delete_first)

        orphaned_ogs = orphaned_ogs.difference(used_group_ogs)

        #Delete the first group and then the second group
        #ret = del_1(root, box, delete_first, orphaned_dict, ret, to_del)
        ret = del_2(root, box, orphaned_ogs, orphaned_dict, ret, to_del)

        #For cleanup
        if to_del:
            #Apply the changes and show NSO errors to the stat output
            try:
                tran.apply()
                stat = "Success"

            except (_ncs.error.Error, ncs.maagic.MaagicError) as err:
                stat = err

            return ret, stat
    #For search
    return ret



def nso_to_python(box, root, og_list, og_typ, acl_list):
    """
    A function that converts the inputted device's object group list and access
    lists to python lists for optimization. It returns:
    1. og_list: A python list with object group names.
    2. og_typ:  A python list with the object group type of each object group
                which is alligned with the og_list.
    3. acl_list:A python list that contains access lists that contain the rules
                of its respective access list.
    """
    #Adding all of the object groups and their types to python lists
    for ogtyp in root.devices.device[box].config.asa__object_group:
        for og in root.devices.device[box].config.asa__object_group[ogtyp]:
            og_list.append(og.id)
            og_typ.append(str(og))      #str(og) is the object group type

    #Adding each access list's rules to a python list (temp_rul_list) and
    #then adding those lists as elements of another python list (acl_list)
    for acl in root.devices.device[box].config.asa__access_list.access_list_id:
        temp_rul_list = []
        for rul in root.devices.device[box].config.asa__access_list.access_list_id[acl.id].rule:
            if "object-group" in rul.id:
                temp_rul_list.append(rul.id)
        acl_list.append(temp_rul_list)

    return og_list, og_typ, acl_list

def rec_group_og(used_group_ogs, root, box, og, typ):
    """
    A recursive function that adds a used object group's group-objects (object groups inside
    of object groups) to a set (used_group_ogs) and recursively recalls itself to check if
    the group objects added have any group objects themselves to add as well. It returns:
    1. used_group_ogs: Set of used group-objects that should not be removed.
    """
    if root.devices.device[box].config.asa__object_group[typ][og].group_object:
        for group_og in root.devices.device[box].config.asa__object_group[typ][og].group_object:
            used_group_ogs.add(group_og.id)
            used_group_ogs = rec_group_og(used_group_ogs, root, box, group_og.id, typ)

    return used_group_ogs

def find_orphaned_og(root, box, og_list, og_typ, acl_list, used_group_ogs, orphaned_ogs, orphaned_dict):
    """
    A function that finds all of the unused object groups by iterating through all of the access
    lists for each object group, checking if the object group is in any of the rules of any of
    the access lists of the inputted device. It returns:
    1. orphaned_ogs:    A set of all of the unused object groups within the device.
    2. delete_first:    A set of the unused object groups that have group objects.
    3. used_group_ogs:  A set of all of the group-objects that are actually being used.
    4. orphaned_dict:   A dictionary of the unused object groups that each contains an inner dictionary
                        with the object group's type, group-objects, and flag that indicates whether
                        it's been deleted (True) or not (False).

    """
    #Iterating through both object group and object group type lists simultaneously
    for og, typ in zip(og_list, og_typ):
        #flag indicates whether the object group was found in an access list
        flag = False
        for acl in acl_list:
            for rule in acl:
                if og in rule:
                    used_group_ogs = rec_group_og(used_group_ogs, root, box, og, typ)
                    #object group was found, update flag and break
                    flag = True
                    break
            #If found, continue to the next object group
            if flag:
                break
        #If not found in any of the access lists, add to set and create dictionary of orphaned ogs
        if not flag:
            orphaned_ogs.add(og)
            inner_dict = {"og_type" : typ, "group_ogs" : [], "deleted" : False}
            #If the object group has group-objects, add to delete_first set
            if root.devices.device[box].config.asa__object_group[typ][og].group_object:
                #delete_first.add(og)
                for group_og in root.devices.device[box].config.asa__object_group[typ][og].group_object:
                    inner_dict["group_ogs"].append(group_og.id)
            #Add inner dictionary to orphaned object group key in dictionary
            orphaned_dict[og] = inner_dict

    return orphaned_ogs, used_group_ogs, orphaned_dict

def prioritize_del(orphaned_ogs, used_group_ogs, delete_first):
    """
    A function that removes the used group-objects from a set of all of the orphaned object
    groups and from the high priority deletion set, and creates a delete second set by removing
    the delete first set from the general orphaned object groups. It returns:
    1. delete_first: The orphaned object groups that have group-objects (highest priority to delete)
    2. delete_second: The orphaned object groups that don't have group-objects (NSO error if deleted first)
    """
    orphaned_ogs = orphaned_ogs.difference(used_group_ogs)
    delete_first = delete_first.difference(used_group_ogs)
    delete_second = orphaned_ogs.difference(delete_first)

    return delete_first, delete_second


def del_1(root, box, delete_first, orphaned_dict, ret, to_del):
    """
    A function that deletes the object groups that have group-objects in this specific order:
    object groups that are not group-objects for any other object group are deleted first (avoiding NSO error).
    It also adds all of the deleted object groups to a dictionary. It returns:
    1. ret: A dictionary organized by object group type with all of the deleted object groups.
    """
    #The number of object groups that are left to delete first
    del_f_count = len(delete_first)
    #While there are still object groups to delete within delete first
    while del_f_count:
        for og in delete_first:
            #If that object group has already been deleted, move on to the next object group
            if orphaned_dict[og]["deleted"]:
                continue
            #flag indicates whether the current object group is a group-object within another
            #object group inside delete first that has yet to be deleted
            flag = False
            for og2 in delete_first:
                if orphaned_dict[og2]["deleted"]:
                    continue
                #If the current object group is a group-object, set flag = True
                if og in orphaned_dict[og2]["group_ogs"]:
                    flag = True
                    break
            #If object group is not a group-object in a non-deleted delete first object group,
            #add to dictionary, decrement delete first count, set delete flag to True, and delete
            if not flag:
                if orphaned_dict[og]["og_type"] in ret.keys():
                    ret[orphaned_dict[og]["og_type"]].append(og)
                else:
                    ret[orphaned_dict[og]["og_type"]] = [og]

                del_f_count -= 1
                orphaned_dict[og]["deleted"] = True
                if to_del:
                    del root.devices.device[box].config.asa__object_group[orphaned_dict[og]["og_type"]][og]

    return ret


def del_2(root, box, delete_second, orphaned_dict, ret, to_del):
    """
    A function that deletes the remaining orphaned object groups and adds them to the dictionary
    that will be returned. It returns:
    1. ret: A dictionary organized by object group type with all of the deleted object groups.
    """
    for og in delete_second:
        if orphaned_dict[og]["og_type"] in ret.keys():
            ret[orphaned_dict[og]["og_type"]].append(og)
        else:
            ret[orphaned_dict[og]["og_type"]] = [og]
        if to_del:
            del root.devices.device[box].config.asa__object_group[orphaned_dict[og]["og_type"]][og]

    return ret


def remove_ogs(box, og_type, og_id):
    """
    A function that removes the object group from the object group list using
    the arguments passed: device name, object group name, and object group type.
    It returns:
    1. stat: Status of applying delete to device (Success or NSO error)
    """
    with ncs.maapi.single_write_trans('ncsadmin', 'python', groups=['ncsadmin']) as tran:
        root = ncs.maagic.get_root(tran)
        del root.devices.device[box].config.asa__object_group[og_type][og_id]
        try:
            tran.apply()
            stat = "Success"
        #Provides error message if there is a problem removing an OG
        except (_ncs.error.Error, ncs.maagic.MaagicError) as err:
            stat = err

    return stat
