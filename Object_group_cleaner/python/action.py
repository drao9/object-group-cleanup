"""
NCS Action Package example.

Implements a package with actions
(C) 2015 Tail-f Systems
Permission to use this code as a starting point hereby granted

See the README file for more information
"""
from __future__ import print_function
import sys

# import your_audit_name_here # Copy and change this to the name of your Python File
import ncs
from datetime import datetime
import time
import _ncs
import _ncs.dp
from ncs.dp import Action
from ncs.application import Application
from _namespaces.Object_group_cleaner_ns import ns
import helpers
import obj_cleanup

DATE_FORMAT = "%H:%M:%S.%f"

class ActionHandler(Action):
    """This class implements the dp.Action class."""

    @Action.action
    def cb_action(self, uinfo, name, kp, input, output):
        """Called when the actionpoint is invoked.

        The function is called with:
            uinfo -- a UserInfo object
            name -- the tailf:action name (string)
            kp -- the keypath of the action (HKeypathRef)
            input -- input node (maagic.Node)
            output -- output node (maagic.Node)
        """
        #TODO determine logging standards

        _ncs.dp.action_set_timeout(uinfo, 500)

        self.log.info(uinfo.addr)
        self.log.info(uinfo.usid)
        self.log.info(uinfo.username)
        self.log.info("option: ", name)
        self.log.info("keypath: ", str(kp))

        start = (datetime.strptime(str(datetime.now().time()), DATE_FORMAT))
        output.start_time = time.strftime("%H:%M:%S")

        if name == "cleanup":
            count = 0
            devices = helpers.build_device_list(input)
            for device in devices:
                self.log.info("device: ",device)
                og_for_removal, stat = obj_cleanup.search_and_destroy(device)
                for key in og_for_removal:
                    count += len(og_for_removal[key])
                for key, value in og_for_removal.items():
                    for og in value:
                        result = output.deleted_object_groups.create()
                        result.object_group = og
                        result.og_type = key
            output.number_of_ogs_deleted = count
            output.stat = stat

        elif name == "search":
            devices = helpers.build_device_list(input)
            for device in devices:
                self.log.info("device: ",device)
                og_for_removal = obj_cleanup.flag_ogs_in_box_test(device)
                for key, value in og_for_removal.items():
                    for og in value:
                        result = output.orphaned_object_groups.create()
                        result.object_group = og
                        result.og_type = key

        elif name == "remove":
            obj_groups = helpers.build_og_list(input)
            for obj in obj_groups:
                obj_cleanup.remove_ogs(obj[0], obj[1], obj[2])
                result = output.deleted_object_groups.create()
                result.og_type = obj[1]
                result.object_group = obj[2]
            output.stat = "Success"


        else:
            # Log & return general failures
            self.log.debug("got bad operation: {0}".format(name))
            return _ncs.CONFD_ERR

        end = (datetime.strptime(str(datetime.now().time()), DATE_FORMAT))
        output.end_time = time.strftime("%H:%M:%S")
        output.run_time = str(end-start)
        self.log.info("start time: ",start)
        self.log.info("end time: ", end)
        self.log.info("runtime: ",(end-start))

# ---------------------------------------------
# COMPONENT THREAD THAT WILL BE STARTED BY NCS.
# ---------------------------------------------


class Action(Application):
    """This class is referred to from the package-meta-data.xml."""
    # DO NOT CHANGE THIS INFORMATION

    def setup(self):
        """
        Setting up the action callback.
        This is used internally by NSO when NSO is re-started or packages a reloaded by NSO.
        """
        self.log.debug('action app start')
        self.register_action('Object_group_cleaner', ActionHandler, [])
