"""
Title:
    - Functions to Assist Action.py

Developed by:
    - Axel Perez axperez@cisco.com

Description:
    - Functions that produce factories from available modules, routes the calling of our
      tool's options, and builds a dictionary of the inputted object groups for the remove_ogs
      function.
"""
import inspect
import ncs
import modules

def build_og_list(input):
    """
    Function to turn all inputs into a dictionary of object group names with an
    inner dictionary that contains the object group's device name and type. Returns:
    1. object_groups:   A dictionary with object group names as keys and values of
                        dictionaries that have two keys: device_name, og_type.
    """
    object_groups = {}

    for item in input.inputs:
        inner_dict = {'device_name': item.device_name, 'og_type': str(item.og_type)}
        object_groups[item.og_name] = inner_dict

    return object_groups

def route(name, device, og_type, og_id):
    """
    A function that at least receives an option name and device name in order to route
    to the correct object for the specifc device type and call its appropriate method to
    return the necessary output. Returns:
    1.  module_list[dev_type].route_action(name, device, og_type, og_id): A dictionary, count,
        or/and stat depending on what the name (search, cleanup, remove) is.
    """
    dev_type = find_dev_type(device)
    module_list = create_modules()
    return module_list[dev_type].route_action(name, device, og_type, og_id)

def create_modules():
    """
    A function that builds all available factories from the modules in modules.py by
    placing an object, defined by each module, as a value for each key in a dictionary
    that has the module's class attribute 'group' (cisco-asa, cisco-ios, etc.) as its keys.
    Returns:
    1.  dev_type_objects: Dictionary of objects from each module with the key being the ned-id
        ('group' member variable from module).
    """
    dev_type_objects = {}
    facts = inspect.getmembers(modules,
                        lambda m: inspect.ismodule(m))
    for name, _module in facts:
        if "module" in name and "abs" not in name:
            classes = inspect.getmembers(_module,
                                lambda m: inspect.isclass(m) and not inspect.isabstract(m))
            for name1, _class in classes:
                if "Abs" not in name1:
                    new_class = _class()
                    dev_type_objects[new_class.group] = new_class
    return dev_type_objects

def find_dev_type(device):
    """
    A function that finds the device type by looking at the ned-id and returns:
    1. dev_type: device type by ned-id.
    """
    with ncs.maapi.single_read_trans('ncsadmin', 'python', groups=['ncsadmin']) as tran:
        root = ncs.maagic.get_root(tran)

        dev_type = root.devices.device[device].device_type.cli.ned_id
    return dev_type
