"""
Module to contain common use functions
"""

import ncs
import inspect
import modules

def build_og_list(input):
    """
    Function to turn all inputs into a dictionary of object group names with an
    inner dictionary that contains the object group's device name and type.
    """
    object_groups = {}

    for item in input.inputs:
        inner_dict = {'device_name': item.device_name, 'og_type': str(item.og_type)}
        object_groups[item.og_name] = inner_dict

    return object_groups

def route(name, device, og_type, og_id):
    """
    Create the factories and audits, then return the object for the appropriate module.
    Does this by calling create_modules()
    Then from the returned dictionary, callign the appropriate group and module.
    """
    dev_type = find_dev_type(device)
    module_list = create_modules()
    return module_list[dev_type].route_action(name, device, og_type, og_id)

def create_modules():
    """
    Function that builds all available factorys from modules.
    and buidls all audits from the factory objects created.
    It returns a dictionary of all factories and their modules.
    """
    dev_type_objects = {}
    facts = inspect.getmembers(modules,
                        lambda m: inspect.ismodule(m))
    for name, _module in facts:
        if "module" in name and "abs" not in name:
            classes = inspect.getmembers(_module,
                                lambda m: inspect.isclass(m) and not inspect.isabstract(m))
            for name, _class in classes:
                if "Abs" not in name:
                    new_class = _class()
                    dev_type_objects[new_class.group].append(new_class)
    return dev_type_objects

def find_dev_type(device):
    with ncs.maapi.single_read_trans('ncsadmin', 'python', groups=['ncsadmin']) as tran:
        root = ncs.maagic.get_root(tran)

        return root.devices.device[device].device_type.cli.ned_id
