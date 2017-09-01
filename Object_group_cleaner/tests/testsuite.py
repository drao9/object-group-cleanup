"""
Title:
    - Unittest for Object Group Cleanup Tool

Developed by:
    - Axel Perez axperez@cisco.com

Description:
    - Testsuite that checks various cases to ensure the tool's algorithm is providing the correct
      output, performance time, and recursive function. This is accomplished by using a netsim
      (virtual test device) thats name (constants.netsim) is provided in the constants.py file.
"""

import unittest
import time
import ncs
import constants
import sys
sys.path.insert(0, '/var/opt/ncs/packages/Object_group_cleaner/python')
import modules

def clear_netsim(m):
    #Clear out object groups in Netsim
    with m.start_write_trans() as t:
        root = ncs.maagic.get_root(t)
        for ogtyp in root.devices.device[constants.netsim].config.asa__object_group:
            for og in root.devices.device[constants.netsim].config.asa__object_group[ogtyp]:
                del root.devices.device[constants.netsim].config.asa__object_group[ogtyp][og.id]

        t.apply()

    #Clear out access lists in Netsim
    with m.start_write_trans() as t:
        root = ncs.maagic.get_root(t)
        for acl in root.devices.device[constants.netsim].config.asa__access_list.access_list_id:
            del root.devices.device[constants.netsim].config.asa__access_list.access_list_id[acl.id]

        t.apply()

def setup_netsim(m, num_ogs, num_rules):
    #Add 20 unique object groups to each of the Netsim's object group types
    with m.start_write_trans() as t:
        root = ncs.maagic.get_root(t)

        og = "test_og_"

        num_types = 0
        for ogtyp in root.devices.device[constants.netsim].config.asa__object_group:
            og_num = og + str(num_types) + '_'
            num_types += 1
            for j in range(num_ogs):
                fake_og = og_num + str(j)
                root.devices.device[constants.netsim].config.asa__object_group[ogtyp].create(fake_og)

        t.apply()

    #Create the same amount of access lists as there are object group types and add 20 rules with the previously made object groups to each ACL
    with m.start_write_trans() as t:
        root = ncs.maagic.get_root(t)

        holder = "access_list_"
        rul = "extended permit icmp object-group test_og_"

        for i in range(num_types):
            acl_num = holder + str(i)
            root.devices.device[constants.netsim].config.asa__access_list.access_list_id.create(acl_num)
            rul_num = rul + str(i) + '_'
            for j in range(num_rules):
                fake_rule = rul_num + str(j)
                root.devices.device[constants.netsim].config.asa__access_list.access_list_id[acl_num].rule.create(fake_rule)

        t.apply()

def create_rec_og(test_og, depth, root):
    if depth:
        fake_og = test_og + str(depth)
        root.devices.device[constants.netsim].config.asa__object_group.network[test_og].group_object.create(fake_og)
        create_rec_og(test_og, depth - 1, root)

class TestOGC(unittest.TestCase):
    """
    Test to ensure that the functions within the Object Group Cleaner Tool are
    providing the correct output and are running efficiently.
    """

    def test_search_empty(self):
        """
        Test case: All of the object groups are being used in the device's ACLs.
        This test passes if no object groups are returned as orphaned object groups.
        """

        orphaned_ogs = {}
        empty_dict = {}

        #Begin NSO session
        with ncs.maapi.Maapi() as m:
            with ncs.maapi.Session(m, 'ncsadmin', 'python', groups=['ncsadmin']):

                clear_netsim(m)

                setup_netsim(m, 20, 20)

                #Call the search action and retreive the output
                with m.start_write_trans() as t:

                    root = ncs.maagic.get_root(t)
                    input1 = root.Object_group_cleaner.search.get_input()
                    new_obj = input1
                    new_obj.device = constants.netsim

                    output1 = root.Object_group_cleaner.search(input1)

                    org_gps = output1.orphaned_object_groups

                    #Add output to dictionary
                    for og in org_gps:
                        if og.og_type in orphaned_ogs.keys():
                            orphaned_ogs[og.og_type].append(og.object_group)
                        else:
                            orphaned_ogs[og.og_type] = [og.object_group]

                    #Check that the output of the search function is empty
                    self.assertEqual(orphaned_ogs, empty_dict)

                clear_netsim(m)

    def test_seach_reg(self):
        """
        Test case: Certain object groups are not used in the device's ACL.
        This test passes if the correct object groups are returned from the search action.
        """

        orphaned_ogs = []

        #Begin NSO session
        with ncs.maapi.Maapi() as m:
            with ncs.maapi.Session(m, 'ncsadmin', 'python', groups=['ncsadmin']):

                clear_netsim(m)

                setup_netsim(m, 50, 20)

                #Call the search action and retreive the output
                with m.start_write_trans() as t:

                    root = ncs.maagic.get_root(t)
                    input1 = root.Object_group_cleaner.search.get_input()
                    new_obj = input1
                    new_obj.device = constants.netsim

                    output1 = root.Object_group_cleaner.search(input1)
                    org_gps = output1.orphaned_object_groups

                    #add object groups from output to a list
                    for og in org_gps:
                        orphaned_ogs.append(og.object_group)

                    #check whether the output is the same as the correct answer
                    self.assertEqual(set(orphaned_ogs), set(constants.answer1))

                clear_netsim(m)

    def test_perform(self):
        """
        Test case: performance test of the cleanup action.
        The cleanup action should run in less than 600 seconds for this particular netsim set up.
        """

        with ncs.maapi.Maapi() as m:
            with ncs.maapi.Session(m, 'ncsadmin', 'python', groups=['ncsadmin']):

                clear_netsim(m)

                setup_netsim(m, 1800, 1797)

                #Call the cleanup action and record the run time
                with m.start_write_trans() as t:
                    root = ncs.maagic.get_root(t)
                    input1 = root.Object_group_cleaner.cleanup.get_input()
                    new_obj = input1
                    new_obj.device = constants.netsim

                    b = time.time()
                    root.Object_group_cleaner.cleanup(input1)
                    af = time.time()
                    run_time = af - b

                    #Assert that cleanup runs in less than 600 seconds
                    print run_time
                    self.assertTrue(run_time < 200)

                clear_netsim(m)

    def test_remove(self):
        """
        Test case: None of the object groups are being used in the access list, thus all
        are orphaned. This test will pass if the device's object group list is empty.
        """

        empty_list = []
        og_list = []

        #Begin NSO session
        with ncs.maapi.Maapi() as m:
            with ncs.maapi.Session(m, 'ncsadmin', 'python', groups=['ncsadmin']):

                clear_netsim(m)

                setup_netsim(m, 20, 0)

                #Call the cleanup action and check the device's object group list
                with m.start_write_trans() as t:

                    root = ncs.maagic.get_root(t)
                    input1 = root.Object_group_cleaner.cleanup.get_input()
                    new_obj = input1
                    new_obj.device = constants.netsim

                    root.Object_group_cleaner.cleanup(input1)

                    #Add any object groups in the device's object group list to og_list
                    for ogtyp in root.devices.device[constants.netsim].config.asa__object_group:
                        for og in root.devices.device[constants.netsim].config.asa__object_group[ogtyp]:
                            og_list.append(og.id)

                    #Assert that og_list is empty
                    self.assertEqual(og_list, empty_list)

                clear_netsim(m)

    def test_recurs(self):
        #Begin NSO session
        with ncs.maapi.Maapi() as m:
            with ncs.maapi.Session(m, 'ncsadmin', 'python', groups=['ncsadmin']):

                clear_netsim(m)

                with m.start_write_trans() as t:
                    root = ncs.maagic.get_root(t)

                    test_og = 'test_og_'
                    root.devices.device[constants.netsim].config.asa__object_group['network'].create(test_og)
                    create_rec_og(test_og, 20, root)

                    t.apply()

                with m.start_read_trans() as t:
                    root = ncs.maagic.get_root(t)
                    used_group_ogs = set()
                    modules.asa_module.rec_group_og(used_group_ogs, root, constants.netsim, test_og, 'network')

                print used_group_ogs

                clear_netsim(m)

if __name__ == '__main__':
    unittest.main()
