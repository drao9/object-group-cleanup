from __future__ import print_function
import sys
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
        _ncs.dp.action_set_timeout(uinfo, 800)

        self.log.info(uinfo.addr)
        self.log.info(uinfo.usid)
        self.log.info(uinfo.username)
        self.log.info("option: ", name)
        self.log.info("keypath: ", str(kp))

        start = (datetime.strptime(str(datetime.now().time()), DATE_FORMAT))
        output.start_time = time.strftime("%H:%M:%S")

        if name == "cleanup":
            count = 0
            self.log.info("input: ", input)
            self.log.info("device: ", input.device)
            device = input.device
            og_for_removal, stat = obj_cleanup.cleanup_or_search(device, True)
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
            count = 0
            self.log.info("input: ", input)
            self.log.info("device: ", input.device)
            device = input.device
            og_for_removal = obj_cleanup.cleanup_or_search(device, False)
            for key in og_for_removal:
                count += len(og_for_removal[key])
            for key, value in og_for_removal.items():
                for og in value:
                    result = output.orphaned_object_groups.create()
                    result.object_group = og
                    result.og_type = key
            output.number_of_orphaned = count

        elif name == "remove":
            self.log.info("input: ", input)
            obj_groups = helpers.build_og_list(input)
            outer_stat = "Success"
            for obj in obj_groups:
                self.log.info("device: ", obj[0])
                stat = obj_cleanup.remove_ogs(obj[0], obj[1], obj[2])
                if stat != "Success":
                    outer_stat = stat
                result = output.deleted_object_groups.create()
                result.og_type = obj[1]
                result.object_group = obj[2]
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
