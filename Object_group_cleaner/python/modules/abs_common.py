"""
Title:
    - Abstract Methods and Common Functions

Developed by:
    - Axel Perez axperez@cisco.com
    - Alyssa Sandore asandore@cisco.com
    - Divyani Rao divyarao@cisco.com
    - Rob Gonzales robgo@cisco.com

Description:
    - Abstract methods and common functions class for the Object Group Cleanup Tool
      NSO package. The AbsCommon class should be inherited by any modules wishing
      to use this algorithm. Those modules must also implement the abstract methods
      defined below.
"""
import abc
import ncs
import _ncs

class AbsCommon(object):
    """
    A class that contains all of the abstract methods that must be implemented by
    any class that inherits this class and contains functions that are not specific
    to device type.
    """

    @abc.abstractmethod
    def delete_obj(self, box, root, og_id, og_type):
        """
        A function that deletes an object group from a specific device type's
        object group list and doesn't return anything. This function receives
        the device name, the root of the NSO transaction, the name of the object
        group, and the object group type as arguments in that order.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def obj_list_conversion(self, box, root):
        """
        A function that converts the specific device type's object group list to
        a python dictionary with the object group name as the key and the object
        group's type as the value. This dictionary is returned.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def acl_list_conversion(self, box, root):
        """
        A function that converts the specific device type's access list (or list
        that has to be checked against) to a python dictionary with the access
        lists as keys and their rules in a list as the value. The dictionary is returned.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def rec_group_og(self, used_group_ogs, root, box, og, typ):
        """
        A recursive function that adds a used object group's group-objects (object groups inside
        of object groups) to a set (used_group_ogs) and recursively recalls itself to check if
        the group objects added have any group objects themselves to add as well. It does this
        in order to ensure that used group objects are not deleted. (Look at asa_module.py for ex)
        It returns:
        1. used_group_ogs: Set of used group-objects that should not be removed.
        """
        raise NotImplementedError

    def route_action(self, name, device, og_type, og_id):
        """
        A function called by the route function in helpers.py to call specific methods
        depending on the name/action (cleanup, search, remove). It returns whatever the
        function it callls returns.
        """
        if name == "search":
            return self.search(device)
        elif name == "cleanup":
            return self.cleanup(device)
        elif name == "remove":
            return self.remove_ogs(device, og_type, og_id)

    def search(self, box):
        """
        A function that finds all of the unused object groups (object groups that
        are in the object group list but are never called in the access list) from the inputted
        device. It returns:
        1. ret: A dictionary with all of the orphaned object groups organized by type.
        2. orphan_count: The number of object groups that should be deleted.
        3. "Success": Search will always be succesfull since it is not applying any transactions.
        """

        #Creating transaction and setting root to access NSO
        with ncs.maapi.single_read_trans('ncsadmin', 'python', groups=['ncsadmin']) as tran:
            root = ncs.maagic.get_root(tran)

            #Converting access lists and object group list to python dictionaries
            obj_dict = self.obj_list_conversion(box, root)
            acl_dict = self.acl_list_conversion(box, root)

            #Finding the unused object groups and the group objects that are actually being used
            orphaned_ogs, used_group_ogs = self.find_orphaned_og(root, box, obj_dict, acl_dict)

            #Remove the used group objects from the orphaned object group set
            orphaned_ogs = orphaned_ogs.difference(used_group_ogs)

            #Delete the orphaned object groups from the object group list and record the count
            ret, orphan_count = self.del_orphaned_ogs(root, box, orphaned_ogs, obj_dict, False)

        return ret, orphan_count, "Success"

    def cleanup(self, box):
        """
        A function that deletes all of the unused object groups (object groups that
        are in the object group list but are never called in the access list) from the inputted
        device. It returns:
        1. ret: A dictionary with all of the deleted object groups organized by type.
        2. orphan_count: The number of object groups that were deleted.
        3. stat: A string that contains the status of the deletion (Success or specific ncs error).
        """

        #Creating transaction and setting root to access NSO
        with ncs.maapi.single_write_trans('ncsadmin', 'python', groups=['ncsadmin']) as tran:
            root = ncs.maagic.get_root(tran)

            #Converting access lists and object group list to python dictionaries
            obj_dict = self.obj_list_conversion(box, root)
            acl_dict = self.acl_list_conversion(box, root)

            #Finding the unused object groups and the group objects that are actually being used
            orphaned_ogs, used_group_ogs = self.find_orphaned_og(root, box, obj_dict, acl_dict)

            #Remove the used group objects from the orphaned object group set
            orphaned_ogs = orphaned_ogs.difference(used_group_ogs)

            #Delete the orphaned object groups from the object group list and record the count
            ret, orphan_count = self.del_orphaned_ogs(root, box, orphaned_ogs, obj_dict, True)

            #Apply the changes and show only NSO errors to the stat output
            try:
                tran.apply()
                stat = "Success"

            except (_ncs.error.Error, ncs.maagic.MaagicError) as err:
                stat = err

        return ret, orphan_count, stat

    def find_orphaned_og(self, root, box, obj_dict, acl_dict):
        """
        A function that finds all of the unused object groups by iterating through all of the access
        lists for each object group, checking if the object group is in any of the rules of any of
        the access lists of the inputted device.
        It returns:
        1. orphaned_ogs:    A set of all of the unused object groups within the device.
        2. used_group_ogs:  A set of all of object groups that are not necessarily mentioned in
                            the access list but are inside object groups that are used in the
                            access list.
        """
        used_group_ogs = set()
        orphaned_ogs = set()

        #Iterating through the keys in the object group list dictionary
        for obj in obj_dict:
            #flag indicates whether the object group was found in an access list
            flag = False
            #Iterating through the access lists and their rules
            for acl in acl_dict:
                for rule in acl_dict[acl]:
                    #If found, check for group objects inside of it and update flag
                    if obj in rule:
                        used_group_ogs = self.rec_group_og(used_group_ogs, root, box, obj, obj_dict[obj])
                        #object group was found, update flag and break
                        flag = True
                        break
                #If found, continue to the next object group
                if flag:
                    break
            #If not found in any of the access lists, add to orphaned_ogs set
            if not flag:
                orphaned_ogs.add(obj)


        return orphaned_ogs, used_group_ogs

    def del_orphaned_ogs(self, root, box, orphaned_ogs, obj_dict, to_del):
        """
        A function that deletes the remaining orphaned object groups and adds them to the dictionary
        that will be returned. It returns:
        1. ret: A dictionary organized by object group type with all of the deleted object groups.
        2. count: A count of the orphaned object groups
        """
        ret = {}
        count = 0
        for obj in orphaned_ogs:
            count += 1
            if obj_dict[obj] in ret.keys():
                ret[obj_dict[obj]].append(obj)
            else:
                ret[obj_dict[obj]] = [obj]
            if to_del:
                self.delete_obj(box, root, obj, obj_dict[obj])

        return ret, count

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
