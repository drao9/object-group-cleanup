import ncs
import _ncs
import socket
import abc

class AbsCommon(object):

    @abc.abstractmethod
    def delete_obj(self, box, root, og_id, og_type):
        raise NotImplementedError

    @abc.abstractmethod
    def obj_list_conversion(self, box, root):
        raise NotImplementedError

    @abc.abstractmethod
    def acl_list_conversion(self, box, root):
        raise NotImplementedError

    @abc.abstractmethod
    def rec_group_og(self, used_group_ogs, root, box, og, typ):
        raise NotImplementedError

    def route_action(self, name, device, og_type, og_id):
        if name == "search":
            return self.search(device)
        elif name == "cleanup":
            return self.cleanup(device)
        elif name == "remove":
            return self.remove_ogs(device, og_type, og_id)

    def search(self, box):
        """
        A function that deletes all of the unused object groups in the necessary
        order from the inputted device. It returns:
        1. ret: A dictionary with all of the deleted object groups organized by type.
        2. stat: A string that contains the status of the deletion (Success or specific ncs error).
        """

        #Creating transaction and setting root to access NSO
        with ncs.maapi.single_write_trans('ncsadmin', 'python', groups=['ncsadmin']) as tran:
            root = ncs.maagic.get_root(tran)

            #Converting access lists and object group list to python dictionaries
            obj_dict = self.obj_list_conversion(box, root)
            acl_dict = self.acl_list_conversion(box, root)

            #Finding the unused object groups and placing them in sets for prioritization
            orphaned_ogs, used_group_ogs = self.find_orphaned_og(root, box, obj_dict, acl_dict)

            #Remove the used group objects from the orphaned object group set
            orphaned_ogs = orphaned_ogs.difference(used_group_ogs)
            orphan_count = len(orphaned_ogs)
            ret = self.del_2(root, box, orphaned_ogs, obj_dict, False)

        return ret, orphan_count, "Success"

    def cleanup(self, box):
        """
        A function that deletes all of the unused object groups in the necessary
        order from the inputted device. It returns:
        1. ret: A dictionary with all of the deleted object groups organized by type.
        2. stat: A string that contains the status of the deletion (Success or specific ncs error).
        """

        #Creating transaction and setting root to access NSO
        with ncs.maapi.single_write_trans('ncsadmin', 'python', groups=['ncsadmin']) as tran:
            root = ncs.maagic.get_root(tran)

            #Converting access lists and object group list to python lists
            obj_dict = self.obj_list_conversion(box, root)
            acl_dict = self.acl_list_conversion(box, root)

            #Finding the unused object groups and placing them in sets for prioritization
            orphaned_ogs, used_group_ogs = self.find_orphaned_og(root, box, obj_dict, acl_dict)

            #Remove the used group objects from the orphaned object group set
            orphaned_ogs = orphaned_ogs.difference(used_group_ogs)
            orphan_count = len(orphaned_ogs)
            ret = self.del_2(root, box, orphaned_ogs, obj_dict, True)

        #Apply the changes and show NSO errors to the stat output
        try:
            tran.apply()
            stat = "Success"

        except (_ncs.error.Error, ncs.maagic.MaagicError) as err:
            stat = err

        return ret, orphan_count, stat
        """
    def obj_list_conversion(self):
        raise NotImplemented
        """
    def find_orphaned_og(self, root, box, obj_dict, acl_dict):
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
        used_group_ogs = set()
        orphaned_ogs = set()

        #Iterating through both object group and object group type lists simultaneously
        for og in obj_dict:
            #flag indicates whether the object group was found in an access list
            flag = False
            for acl in acl_dict:
                for rule in acl_dict[acl]:
                    if og in rule:
                        used_group_ogs = self.rec_group_og(used_group_ogs, root, box, og, obj_dict[og])
                        #object group was found, update flag and break
                        flag = True
                        break
                #If found, continue to the next object group
                if flag:
                    break
            #If not found in any of the access lists, add to set and create dictionary of orphaned ogs
            if not flag:
                orphaned_ogs.add(og)


        return orphaned_ogs, used_group_ogs

    def del_2(self, root, box, orphaned_ogs, obj_dict, to_del):
        """
        A function that deletes the remaining orphaned object groups and adds them to the dictionary
        that will be returned. It returns:
        1. ret: A dictionary organized by object group type with all of the deleted object groups.
        """
        ret = {}
        for og in orphaned_ogs:
            if obj_dict[og] in ret.keys():
                ret[obj_dict[og]].append(og)
            else:
                ret[obj_dict[og]] = [og]
            if to_del:
                self.delete_obj(box, root, og, obj_dict[og])

        return ret

    def remove_ogs(self, box, og_type, og_id):
        """
        A function that removes the object group from the object group list using
        the arguments passed: device name, object group name, and object group type.
        It returns:
        1. stat: Status of applying delete to device (Success or NSO error)
        """
        with ncs.maapi.single_write_trans('ncsadmin', 'python', groups=['ncsadmin']) as tran:
            root = ncs.maagic.get_root(tran)
            self.delete_obj(box, root, og_id, og_type)
            try:
                tran.apply()
                stat = "Success"
            #Provides error message if there is a problem removing an OG
            except (_ncs.error.Error, ncs.maagic.MaagicError) as err:
                stat = err

        return stat
