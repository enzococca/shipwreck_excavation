#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script to reload the plugin in QGIS Python Console
Run this in QGIS Python Console to reload the plugin
"""

# Copy and paste this into QGIS Python Console:

import sys
import os
from qgis import utils

# Plugin name
plugin_name = 'shipwreck_excavation'

# First unload if loaded
if plugin_name in utils.plugins:
    utils.unloadPlugin(plugin_name)
    
# Remove from Python modules to force reload
if plugin_name in sys.modules:
    del sys.modules[plugin_name]
    
# Also remove submodules
modules_to_remove = []
for mod in sys.modules:
    if mod.startswith(plugin_name + '.'):
        modules_to_remove.append(mod)
        
for mod in modules_to_remove:
    del sys.modules[mod]
    
# Load plugin
utils.loadPlugin(plugin_name)

# Start plugin
if utils.startPlugin(plugin_name):
    print(f"✓ Plugin '{plugin_name}' loaded successfully!")
else:
    print(f"✗ Failed to start plugin '{plugin_name}'")