# -*- coding: utf-8 -*-
"""
/***************************************************************************
 ShipwreckExcavation
                                 A QGIS plugin
 Archaeological excavation management system for underwater shipwrecks
                             -------------------
        begin                : 2025-01-17
        copyright            : (C) 2025 by Shipwreck Excavation Team
        email                : contact@shipwreck-excavation.org
 ***************************************************************************/
"""

def classFactory(iface):
    """Load ShipwreckExcavation class from file shipwreck_excavation.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from .shipwreck_excavation import ShipwreckExcavation
    return ShipwreckExcavation(iface)