"""
	Title:
		__init__.py

	Developed by:
		Kevin Manan (kmanan@cisco.com)

	Description:
		This file imports all the files from the package's modules and it will only import the modules with the naming scheme
		"*_module.py". So when creating new modules make sure the naming scheme is correct. This will fail, if there is a
		compile error in the module you create.

	To use for a different package:
		- Change line 19* and use your package's name.
		- Change line 25* to specify where you want to log.
"""
from .abs_common import AbsCommon
import os, fnmatch, importlib, logging

packageName = "Object_group_cleaner"
LOG = logging.getLogger("tester")

def init_logger():
    logger = logging.getLogger("tester")
    fhandler = logging.FileHandler("/var/log/ncs/modules.log")
    fhandler.setLevel(logging.DEBUG)
    logger.addHandler(fhandler)

def importLibs(packageName):
	#currentDir = os.getcwd()
	oldDir = '/var/opt/ncs/'
	currentDir = currentDir + os.sep + "packages" + os.sep + packageName + os.sep + "python" + os.sep + "modules" + os.sep
	for moduleNames in os.listdir(currentDir):
		os.chdir(currentDir)
		if fnmatch.fnmatch(moduleNames, '*_module.py'):
			LOG.info("\n\nThis is a module %s", moduleNames)
			moduleNames = moduleNames[:-3]
			my_module = importlib.import_module("modules." + moduleNames)
			LOG.info("\n\nSuccessfully load %s", moduleNames)
	os.chdir(oldDir)


importLibs(packageName)
