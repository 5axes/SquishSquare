# Copyright (c) 2022 5@xes
# Based on the Tab+ plugin  and licensed under LGPLv3 or higher.

VERSION_QT5 = False
try:
    from PyQt6.QtCore import QT_VERSION_STR
except ImportError:
    VERSION_QT5 = True
    
from . import SquishSquare

from UM.i18n import i18nCatalog
i18n_catalog = i18nCatalog("cura")

def getMetaData():
    if not VERSION_QT5:
        QmlFile="qml/qml_qt6/SquishSquare.qml"
    else:
        QmlFile="qml/qml_qt5/SquishSquare.qml"
        
    return {
        "tool": {
            "name": i18n_catalog.i18nc("@label", "Squish Square"),
            "description": i18n_catalog.i18nc("@info:tooltip", "Add Squish Square"),
            "icon": "tool_icon.svg",
            "tool_panel": QmlFile,
            "weight": 12
        }
    }

def register(app):
    return { "tool": SquishSquare.SquishSquare() }
