"""
Title:
    - Action Python File for Object Group Cleanup Tool

Developed by:
    - Axel Perez axperez@cisco.com
    - Alyssa Sandore asandore@cisco.com
    - Divyani Rao divyarao@cisco.com
    - Rob Gonzales robgo@cisco.com

Description:
    - Code that logs all of the user and option information of the tool, calls the
    appropriate functions depending on the option, and creates the output from the
    YANG.
"""
from __future__ import print_function
import ncs
from datetime import datetime
import time
import _ncs
import _ncs.dp
from ncs.dp import Action
from ncs.application import Application
from _namespaces.Object_group_cleaner_ns import ns
import helpers


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
        _ncs.dp.action_set_timeout(uinfo, 800)

        self.log.info(uinfo.addr)
        self.log.info(uinfo.usid)
        self.log.info(uinfo.username)
        self.log.info("option: ", name)
        self.log.info("keypath: ", str(kp))

        start = (datetime.strptime(str(datetime.now().time()), DATE_FORMAT))
        output.start_time = time.strftime("%H:%M:%S")

        if name == "cleanup" or name == "search":
            self.log.info("input: ", input)
            self.log.info("device: ", input.device)

            og_for_removal, count, stat = helpers.route(name, input.device, None, None)

            for key, value in og_for_removal.items():
                for og in value:
                    result = output.orphaned_object_groups.create()
                    result.object_group = og
                    result.og_type = key

            output.number_of_orphaned = count
            output.stat = stat

        elif name == "remove":
            self.log.info("input: ", input)
            obj_groups = helpers.build_og_list(input)
            outer_stat = "Success"

            for obj in obj_groups:
                self.log.info("device: ", obj['device_name'])
                stat = helpers.route(name, obj['device_name'], obj['og_type'], obj)

                if stat != "Success":
                    outer_stat = stat

                result = output.deleted_object_groups.create()
                result.og_type = obj['og_type']
                result.object_group = obj
            output.stat = outer_stat

        else:
            # Log & return general failures
            self.log.debug("got bad operation: {0}".format(name))
            return _ncs.CONFD_ERR

        end = (datetime.strptime(str(datetime.now().time()), DATE_FORMAT))
        output.end_time = time.strftime("%H:%M:%S")
        output.run_time = str(end - start)
        self.log.info("start time: ", start)
        self.log.info("end time: ", end)
        self.log.info("runtime: ", (end - start))

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
