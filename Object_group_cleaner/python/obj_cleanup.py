import socket
import ncs

def cleanup(box):
    """

    """
    #Initializing python lists
    og_list = []
    og_typ = []
    acl_list = []
    ret = {}
    #empty = True
    used_group_ogs = set()
    orphaned_ogs = set()
    orphaned_dict = {}
    delete_first = set()

    #Creating transaction and setting root to access NSO
    with ncs.maapi.single_write_trans('ncsadmin', 'python', groups=['ncsadmin']) as tran:
        root = ncs.maagic.get_root(tran)

        og_list, og_typ, acl_list = nso_to_python(box, root, og_list, og_typ, acl_list)

        orphaned_ogs, delete_first, used_group_ogs, orphaned_dict = find_orphaned_og(root,
        box, og_list, og_typ, acl_list, used_group_ogs, orphaned_ogs, delete_first, orphaned_dict)

        delete_first, delete_second = prioritize_del(orphaned_ogs, used_group_ogs, delete_first)

        ret = del_1(root, box, delete_first, orphaned_dict, ret)
        ret = del_2(root, box, delete_second, orphaned_dict, ret)

        try:
            tran.apply()
            stat = "Success"
        #Provides error message if there is a problem removing an OG
        except ncs.MaagicError, err:
            stat = ncs.MaagicError, err

        return ret, stat

def nso_to_python(box, root, og_list, og_typ, acl_list):
    """

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

    """
    if root.devices.device[box].config.asa__object_group[typ][og].group_object:
        for group_og in root.devices.device[box].config.asa__object_group[typ][og].group_object:
            used_group_ogs.add(group_og.id)
            used_group_ogs = rec_group_og(used_group_ogs, root, box, group_og.id, typ)

    return used_group_ogs

def find_orphaned_og(root, box, og_list, og_typ, acl_list, used_group_ogs, orphaned_ogs, delete_first, orphaned_dict):
    #Iterating through both object group and object group type lists simultaneously
    for og, typ in zip(og_list, og_typ):
        flag = 0
        for acl in acl_list:
            #flag indicates whether og was found in an access list
            for rule in acl:
                if og in rule:
                    used_group_ogs = rec_group_og(used_group_ogs, root, box, og, typ)
                    flag = 1
                    break
            #If found, continue to the next object group
            if flag:
                break
        #If not found in any of the access lists, delete from object group list
        #and add to dictionary
        if not flag:
            orphaned_ogs.add(og)
            inner_dict = {"og_type" : typ, "group_ogs" : [], "deleted" : 0}
            if root.devices.device[box].config.asa__object_group[typ][og].group_object:
                delete_first.add(og)
                for group_og in root.devices.device[box].config.asa__object_group[typ][og].group_object:
                    inner_dict["group_ogs"].append(group_og.id)
            orphaned_dict[og] = inner_dict

    return orphaned_ogs, delete_first, used_group_ogs, orphaned_dict

def prioritize_del(orphaned_ogs, used_group_ogs, delete_first):
    """

    """
    orphaned_ogs = orphaned_ogs.difference(used_group_ogs)
    delete_first = delete_first.difference(used_group_ogs)
    delete_second = orphaned_ogs.difference(delete_first)

    return delete_first, delete_second


def del_1(root, box, delete_first, orphaned_dict, ret):
    del_f_count = len(delete_first)
    while del_f_count:
        for og in delete_first:
            if orphaned_dict[og]["deleted"] == 1:
                continue
            flag = 0
            for og2 in delete_first:
                if orphaned_dict[og]["deleted"] == 1:
                    continue
                if og in orphaned_dict[og2]["group_ogs"]:
                    flag = 1
                    break
            if not flag:
                if orphaned_dict[og]["og_type"] in ret.keys():
                    ret[orphaned_dict[og]["og_type"]].append(og)
                else:
                    ret[orphaned_dict[og]["og_type"]] = [og]

                del_f_count -= 1
                orphaned_dict[og]["deleted"] = 1
                del root.devices.device[box].config.asa__object_group[orphaned_dict[og]["og_type"]][og]

    return ret


def del_2(root, box, delete_second, orphaned_dict, ret):
    """
    """
    for og in delete_second:
        if orphaned_dict[og]["og_type"] in ret.keys():
            ret[orphaned_dict[og]["og_type"]].append(og)
        else:
            ret[orphaned_dict[og]["og_type"]] = [og]
        del root.devices.device[box].config.asa__object_group[orphaned_dict[og]["og_type"]][og]

    return ret


def search(box):
    """
    A function that returns a dictionary of the object groups that are not found
    in any of the inputted device's access lists, organized by object group type.
    """

    #Initializing python lists
    og_list = []
    og_typ = []
    acl_list = []
    ret = {}
    #empty = True
    used_group_ogs = set()
    orphaned_ogs = set()
    orphaned_dict = {}
    delete_first = set()

    #Creating transaction and setting root to access NSO
    with ncs.maapi.single_read_trans('ncsadmin', 'python', groups=['ncsadmin']) as tran:
        root = ncs.maagic.get_root(tran)

        og_list, og_typ, acl_list = nso_to_python(box, root, og_list, og_typ, acl_list)

        orphaned_ogs, delete_first, used_group_ogs, orphaned_dict = find_orphaned_og(root,
        box, og_list, og_typ, acl_list, used_group_ogs, orphaned_ogs, delete_first, orphaned_dict)

        delete_first, delete_second = prioritize_del(orphaned_ogs, used_group_ogs, delete_first)

        ret = srch_1(delete_first, orphaned_dict, ret)
        ret = srch_2(delete_second, orphaned_dict, ret)

        stat = "Success"

    return ret, stat

def srch_1(delete_first, orphaned_dict, ret):
    """

    """
    del_f_count = len(delete_first)
    while del_f_count:
        for og in delete_first:
            if orphaned_dict[og]["deleted"] == 1:
                continue
            flag = 0
            for og2 in delete_first:
                if orphaned_dict[og]["deleted"] == 1:
                    continue
                if og in orphaned_dict[og2]["group_ogs"]:
                    flag = 1
                    break
            if not flag:
                if orphaned_dict[og]["og_type"] in ret.keys():
                    ret[orphaned_dict[og]["og_type"]].append(og)
                else:
                    ret[orphaned_dict[og]["og_type"]] = [og]

                del_f_count -= 1
                orphaned_dict[og]["deleted"] = 1

    return ret


def srch_2(delete_second, orphaned_dict, ret):
    for og in delete_second:
        if orphaned_dict[og]["og_type"] in ret.keys():
            ret[orphaned_dict[og]["og_type"]].append(og)
        else:
            ret[orphaned_dict[og]["og_type"]] = [og]

    return ret


def remove_ogs(box, og_id, og_type):
    """
    A function that removes the object group from the object group list using
    the arguments passed: device name, object group name, and object group type.
    """
    with ncs.maapi.single_write_trans('ncsadmin', 'python', groups=['ncsadmin']) as tran:
        root = ncs.maagic.get_root(tran)
        del root.devices.device[box].config.asa__object_group[og_type][og_id]
        try:
            tran.apply()
            stat = "Success"
        #Provides error message if there is a problem removing an OG
        except ncs.MaagicError, err:
            stat = ncs.MaagicError, err

    return stat
