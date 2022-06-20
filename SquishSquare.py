#--------------------------------------------------------------------------------------------
# Initial Copyright(c) 2018 Ultimaker B.V.
# Copyright (c) 2022 5axes
#--------------------------------------------------------------------------------------------
# Based on the SupportBlocker plugin by Ultimaker B.V., and licensed under LGPLv3 or higher.
#
#  https://github.com/Ultimaker/Cura/tree/master/plugins/SupportEraser
#
# All modification 5@xes
# First release  20-06-2022  First proof of concept
#------------------------------------------------------------------------------------------------------------------
#
#------------------------------------------------------------------------------------------------------------------

VERSION_QT5 = False
try:
    from PyQt6.QtCore import Qt, QTimer
    from PyQt6.QtWidgets import QApplication
except ImportError:
    from PyQt5.QtCore import Qt, QTimer
    from PyQt5.QtWidgets import QApplication
    VERSION_QT5 = True

from cura.CuraApplication import CuraApplication

from UM.Resources import Resources
from UM.Logger import Logger
from UM.Message import Message
from UM.Math.Vector import Vector
from UM.Tool import Tool
from UM.Event import Event, MouseEvent
from UM.Mesh.MeshBuilder import MeshBuilder
from UM.Scene.Selection import Selection

from cura.PickingPass import PickingPass

from cura.CuraVersion import CuraVersion  # type: ignore
from UM.Version import Version

from UM.Operations.GroupedOperation import GroupedOperation
from UM.Operations.AddSceneNodeOperation import AddSceneNodeOperation
from UM.Operations.RemoveSceneNodeOperation import RemoveSceneNodeOperation
from cura.Operations.SetParentOperation import SetParentOperation

from UM.Settings.SettingInstance import SettingInstance

from cura.Scene.SliceableObjectDecorator import SliceableObjectDecorator
from cura.Scene.BuildPlateDecorator import BuildPlateDecorator
from cura.Scene.CuraSceneNode import CuraSceneNode
from UM.Scene.Iterator.DepthFirstIterator import DepthFirstIterator
from UM.Scene.ToolHandle import ToolHandle
from UM.Tool import Tool

from UM.Settings.SettingDefinition import SettingDefinition
from UM.Settings.DefinitionContainer import DefinitionContainer
from UM.Settings.ContainerRegistry import ContainerRegistry
from collections import OrderedDict


from UM.i18n import i18nCatalog
catalog = i18nCatalog("cura")
i18n_cura_catalog = i18nCatalog("cura")
i18n_catalog = i18nCatalog("fdmprinter.def.json")
i18n_extrud_catalog = i18nCatalog("fdmextruder.def.json")

import os
import math
import numpy

class SquishSquare(Tool):
    def __init__(self):
        super().__init__()
        
        # Stock Data  
        self._all_picked_node = []
        
        
        # variable for menu dialog        
        self._UseSize = 0.0
        self._Nb_Layer = 1
        self._SMsg = 'Remove All'
        self._nbtab = 0

        # Shortcut
        if not VERSION_QT5:
            self._shortcut_key = Qt.Key.Key_S
        else:
            self._shortcut_key = Qt.Key_S
            
        self._controller = self.getController()

        self._selection_pass = None
        self._i18n_catalog = None
        
        self._application = CuraApplication.getInstance()

        # Suggested solution from fieldOfView . in this discussion solved in Cura 4.9
        # https://github.com/5axes/Calibration-Shapes/issues/1
        # Cura are able to find the scripts from inside the plugin folder if the scripts are into a folder named resources
        Resources.addSearchPath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "resources"))        

        self.Major=1
        self.Minor=0

        # Logger.log('d', "Info Version CuraVersion --> " + str(Version(CuraVersion)))
        Logger.log('d', "Info CuraVersion --> " + str(CuraVersion))
        
        # Test version for Cura Master
        # https://github.com/smartavionics/Cura
        if "master" in CuraVersion :
            self.Major=4
            self.Minor=20
        else:
            try:
                self.Major = int(CuraVersion.split(".")[0])
                self.Minor = int(CuraVersion.split(".")[1])
            except:
                pass
        
        self.setExposedProperties("SSize", "NLayer", "SMsg" )
        
        CuraApplication.getInstance().globalContainerStackChanged.connect(self._updateEnabled)
        
         
        # Note: if the selection is cleared with this tool active, there is no way to switch to
        # another tool than to reselect an object (by clicking it) because the tool buttons in the
        # toolbar will have been disabled. That is why we need to ignore the first press event
        # after the selection has been cleared.
        Selection.selectionChanged.connect(self._onSelectionChanged)
        self._had_selection = False
        self._skip_press = False

        self._had_selection_timer = QTimer()
        self._had_selection_timer.setInterval(0)
        self._had_selection_timer.setSingleShot(True)
        self._had_selection_timer.timeout.connect(self._selectionChangeDelay)
        
        # set the preferences to store the default value
        self._preferences = CuraApplication.getInstance().getPreferences()
        self._preferences.addPreference("squishsquare/s_size", 10)
        # convert as float to avoid further issue
        self._UseSize = float(self._preferences.getValue("squishsquare/s_size"))  

        self._preferences.addPreference("squishsquare/nb_layer", 1)
        # convert as int to avoid further issue
        self._Nb_Layer = int(self._preferences.getValue("squishsquare/nb_layer"))       
     
     
        self._settings_dict = OrderedDict()
        self._settings_dict["squish_mesh"] = {
            "label": "Squish mesh",
            "description": "Mesh used as squish test element",
            "type": "bool",
            "default_value": False,
            "settable_per_mesh": True,
            "settable_per_extruder": False,
            "settable_per_meshgroup": False,
            "settable_globally": False
        }
        ContainerRegistry.getInstance().containerLoadComplete.connect(self._onContainerLoadComplete)


    def _onContainerLoadComplete(self, container_id):
        
        if not ContainerRegistry.getInstance().isLoaded(container_id):
            # skip containers that could not be loaded, or subsequent findContainers() will cause an infinite loop
            return

        try:
            container = ContainerRegistry.getInstance().findContainers(id = container_id)[0]

        except IndexError:
            # the container no longer exists
            return

        if not isinstance(container, DefinitionContainer):
            # skip containers that are not definitions
            return
        if container.getMetaDataEntry("type") == "extruder":
            # skip extruder definitions
            return

        blackmagic_category = container.findDefinitions(key="blackmagic")
        squish_mesh = container.findDefinitions(key=list(self._settings_dict.keys())[0])
                
        if blackmagic_category and not squish_mesh:            
            blackmagic_category = blackmagic_category[0]
            for setting_key, setting_dict in self._settings_dict.items():

                definition = SettingDefinition(setting_key, container, blackmagic_category, self._i18n_catalog)
                definition.deserialize(setting_dict)

                # add the setting to the already existing platform adhesion setting definition
                blackmagic_category._children.append(definition)
                container._definition_cache[setting_key] = definition
                container._updateRelations(definition)

                
    def event(self, event):
        super().event(event)
        modifiers = QApplication.keyboardModifiers()
        if not VERSION_QT5:
            ctrl_is_active = modifiers & Qt.KeyboardModifier.ControlModifier
        else:
            ctrl_is_active = modifiers & Qt.ControlModifier

        if event.type == Event.MousePressEvent and MouseEvent.LeftButton in event.buttons and self._controller.getToolsEnabled():
            if ctrl_is_active:
                self._controller.setActiveTool("TranslateTool")
                return

            if self._skip_press:
                # The selection was previously cleared, do not add/remove an support mesh but
                # use this click for selection and reactivating this tool only.
                self._skip_press = False
                return

            if self._selection_pass is None:
                # The selection renderpass is used to identify objects in the current view
                self._selection_pass = CuraApplication.getInstance().getRenderer().getRenderPass("selection")
            picked_node = self._controller.getScene().findObject(self._selection_pass.getIdAtPosition(event.x, event.y))
            if not picked_node:
                # There is no slicable object at the picked location
                return

            node_stack = picked_node.callDecoration("getStack")

            
            if node_stack:
            
                if node_stack.getProperty("squish_mesh", "value"):
                    self._removeSquishMesh(picked_node)
                    return

                elif node_stack.getProperty("anti_overhang_mesh", "value") or node_stack.getProperty("infill_mesh", "value") or node_stack.getProperty("support_mesh", "value") or node_stack.getProperty("squish_mesh", "value"):
                    # Only "normal" meshes can have support_mesh added to them
                    return

            # Create a pass for picking a world-space location from the mouse location
            # active_camera = self._controller.getScene().getActiveCamera()
            # picking_pass = PickingPass(active_camera.getViewportWidth(), active_camera.getViewportHeight())
            # picking_pass.render()

            # picked_position = picking_pass.getPickedPosition(event.x, event.y)

            # Logger.log('d', "X : {}".format(picked_position.x))
            # Logger.log('d', "Y : {}".format(picked_position.y))
                            
            # Add the support_mesh cube at the picked location
            self._nbtab += 1
            #self._createSquishMesh(picked_node, picked_position,self._nbtab)
            self._createSquishMesh(picked_node, self._nbtab)
            if self._nbtab >= 2 :
                self._nbtab = 0

    def _createSquishMesh(self, parent: CuraSceneNode, Nb: int):
        node = CuraSceneNode()

        node.setName("SquishSquare_" + str(Nb))
            
        node.setSelectable(True)
 
        node_bounds = parent.getBoundingBox()
        
        # Logger.log("d", "width= %s", str(node_bounds.width))
        # Logger.log("d", "height= %s", str(node_bounds.height))
        # Logger.log("d", "depth= %s", str(node_bounds.depth))
        # Logger.log("d", "Center X= %s", str(node_bounds.center.x))
        # Logger.log("d", "Center Y= %s", str(node_bounds.center.z))
        # Logger.log("d", "Center Z= %s", str(node_bounds.center.y))
        PosX = node_bounds.center.x - (node_bounds.width + self._UseSize)*0.5
        PosY = node_bounds.center.z + (node_bounds.depth + self._UseSize)*0.5

        # Logger.log("d", "Pos X= %s", str(PosX))
        # Logger.log("d", "Pos Y= %s", str(PosY))  
        position = Vector(PosX, 0, PosY)
        
        # This function can be triggered in the middle of a machine change, so do not proceed if the machine change
        # has not done yet.
        global_container_stack = CuraApplication.getInstance().getGlobalContainerStack()
        extruder_stack = CuraApplication.getInstance().getExtruderManager().getActiveExtruderStacks()[0]     
        # self._Extruder_count=global_container_stack.getProperty("machine_extruder_count", "value") 
        # Logger.log('d', "Info Extruder_count --> " + str(self._Extruder_count))   
        
        _layer_h_i = extruder_stack.getProperty("layer_height_0", "value")
        _layer_height = extruder_stack.getProperty("layer_height", "value")
        _layer_h = (_layer_h_i * 1.2) + (_layer_height * (self._Nb_Layer - 1))    

        # Square creation Size , layer_height_0*1.2
        mesh = self._createSquare(self._UseSize,_layer_h)
        
        node.setMeshData(mesh.build())

        active_build_plate = CuraApplication.getInstance().getMultiBuildPlateModel().activeBuildPlate
        node.addDecorator(BuildPlateDecorator(active_build_plate))
        node.addDecorator(SliceableObjectDecorator())

        stack = node.callDecoration("getStack") # created by SettingOverrideDecorator that is automatically added to CuraSceneNode
        settings = stack.getTop()
        
        # squish_mesh type
        definition = stack.getSettingDefinition("squish_mesh")
        new_instance = SettingInstance(definition, settings)
        new_instance.setProperty("value", True)
        new_instance.resetState()  # Ensure that the state is not seen as a user state.
        settings.addInstance(new_instance)
        
        if Nb==1 :
                definition = stack.getSettingDefinition("top_bottom_pattern")
                new_instance = SettingInstance(definition, settings)
                new_instance.setProperty("value", "concentric")
                new_instance.resetState()  # Ensure that the state is not seen as a user state.
                settings.addInstance(new_instance)
        
        if Nb==2 :
                definition = stack.getSettingDefinition("top_bottom_pattern")
                new_instance = SettingInstance(definition, settings)
                new_instance.setProperty("value", "lines")
                new_instance.resetState()  # Ensure that the state is not seen as a user state.
                settings.addInstance(new_instance)       
        
        op = GroupedOperation()
        # First add node to the scene at the correct position/scale, before parenting, so the support mesh does not get scaled with the parent
        op.addOperation(AddSceneNodeOperation(node, self._controller.getScene().getRoot()))
        op.addOperation(SetParentOperation(node, parent))
        op.push()
        node.setPosition(position, CuraSceneNode.TransformSpace.World)
        self._all_picked_node.append(node)
        self._SMsg = 'Remove Last'
        self.propertyChanged.emit()
        
        CuraApplication.getInstance().getController().getScene().sceneChanged.emit(node)
        # Logger.log('d', 'End of _createSquishMesh')

    def _removeSquishMesh(self, node: CuraSceneNode):
        parent = node.getParent()
        if parent == self._controller.getScene().getRoot():
            parent = None

        op = RemoveSceneNodeOperation(node)
        op.push()

        if parent and not Selection.isSelected(parent):
            Selection.add(parent)

        CuraApplication.getInstance().getController().getScene().sceneChanged.emit(node)

    def _updateEnabled(self):
        plugin_enabled = False

        global_container_stack = CuraApplication.getInstance().getGlobalContainerStack()
        if global_container_stack:
            plugin_enabled = global_container_stack.getProperty("support_mesh", "enabled")

        CuraApplication.getInstance().getController().toolEnabledChanged.emit(self._plugin_id, plugin_enabled)
    
    def _onSelectionChanged(self):
        # When selection is passed from one object to another object, first the selection is cleared
        # and then it is set to the new object. We are only interested in the change from no selection
        # to a selection or vice-versa, not in a change from one object to another. A timer is used to
        # "merge" a possible clear/select action in a single frame
        if Selection.hasSelection() != self._had_selection:
            self._had_selection_timer.start()

    def _selectionChangeDelay(self):
        has_selection = Selection.hasSelection()
        if not has_selection and self._had_selection:
            self._skip_press = True
        else:
            self._skip_press = False

        self._had_selection = has_selection
 
 
    # Cube Creation
    def _createSquare(self, size, height):
        mesh = MeshBuilder()

        # Intial Comment from Ultimaker B.V. I have never try to verify this point
        # Can't use MeshBuilder.addCube() because that does not get per-vertex normals
        # Per-vertex normals require duplication of vertices
        s = size / 2
        inf = 0
        sup = height
    
        nbv=24        
        verts = [ # 6 faces with 4 corners each
            [-s, inf,  s], [-s, sup,  s], [ s, sup,  s], [ s, inf,  s],
            [-s, sup, -s], [-s, inf, -s], [ s, inf, -s], [ s, sup, -s],
            [ s, inf, -s], [-s, inf, -s], [-s, inf,  s], [ s, inf,  s],
            [-s, sup, -s], [ s, sup, -s], [ s, sup,  s], [-s, sup,  s],
            [-s, inf,  s], [-s, inf, -s], [-s, sup, -s], [-s, sup,  s],
            [ s, inf, -s], [ s, inf,  s], [ s, sup,  s], [ s, sup, -s]
        ]
        mesh.setVertices(numpy.asarray(verts, dtype=numpy.float32))

        indices = []
        for i in range(0, nbv, 4): # All 6 quads (12 triangles)
            indices.append([i, i+2, i+1])
            indices.append([i, i+3, i+2])
        mesh.setIndices(numpy.asarray(indices, dtype=numpy.int32))

        mesh.calculateNormals()
        
        # Logger.log('d', '_createSquare')
        return mesh
        
    def removeAllSquishMesh(self):
        if self._all_picked_node:
            for node in self._all_picked_node:
                node_stack = node.callDecoration("getStack")
                if node_stack.getProperty("squish_mesh", "value"):
                    self._removeSquishMesh(node)
            self._all_picked_node = []
            self._SMsg = 'Remove All'
            self.propertyChanged.emit()
        else:        
            for node in DepthFirstIterator(self._application.getController().getScene().getRoot()):
                if node.callDecoration("isSliceable"):
                    N_Name=node.getName()
                    # Logger.log('d', 'isSliceable : ' + str(N_Name))
                    node_stack=node.callDecoration("getStack")           
                    if node_stack:        
                        if node_stack.getProperty("squish_mesh", "value"):
                            # N_Name=node.getName()
                            # Logger.log('d', 'support_mesh : ' + str(N_Name)) 
                            self._removeSquishMesh(node)
            
    def addAutoSquishMesh(self) -> int:
        nb_Tab=0
        
        for node in DepthFirstIterator(self._application.getController().getScene().getRoot()):
            if node.callDecoration("isSliceable"):
                # Logger.log('d', "isSliceable : {}".format(node.getName()))
                node_stack=node.callDecoration("getStack")           
                if node_stack: 
                    type_infill_mesh = node_stack.getProperty("infill_mesh", "value")
                    type_cutting_mesh = node_stack.getProperty("cutting_mesh", "value")
                    type_support_mesh = node_stack.getProperty("support_mesh", "value")
                    type_anti_overhang_mesh = node_stack.getProperty("anti_overhang_mesh", "value") 
                    type_identification_mesh = node_stack.getProperty("identification_mesh", "value")
                    type_squish_mesh = node_stack.getProperty("squish_mesh", "value")
                    
                    nb_Tab=0
                    if not type_infill_mesh and not type_support_mesh and not type_anti_overhang_mesh and not type_cutting_mesh and not type_identification_mesh and not type_squish_mesh :
                        # and Selection.isSelected(node)
                        Logger.log('d', "Mesh : {}".format(node.getName()))

                        nb_Tab+=1
                        self._createSquishMesh(node ,nb_Tab)
                        nb_Tab+=1
                        self._createSquishMesh(node ,nb_Tab)
                            
                             
        return nb_Tab

    def getSMsg(self) -> bool:
        """ 
            return: golabl _SMsg  as text paramater.
        """ 
        return self._SMsg
    
    def setSMsg(self, SMsg: str) -> None:
        """
        param SType: SMsg as text paramater.
        """
        self._SMsg = SMsg
        
    def getSSize(self) -> float:
        """ 
            return: golabl _UseSize  in mm.
        """           
        return self._UseSize
  
    def setSSize(self, SSize: str) -> None:
        """
        param SSize: Size in mm.
        """
 
        try:
            s_value = float(SSize)
        except ValueError:
            return

        if s_value <= 0:
            return
        
        #Logger.log('d', 's_value : ' + str(s_value))        
        self._UseSize = s_value
        self._preferences.setValue("squishsquare/s_size", s_value)
 
    def getNLayer(self) -> int:
        """ 
            return: golabl _Nb_Layer
        """           
        return self._Nb_Layer
  
    def setNLayer(self, NLayer: str) -> None:
        """
        param NLayer: NLayer as integer >1
        """
 
        try:
            i_value = int(NLayer)
            
        except ValueError:
            return
 
        if i_value < 1:
            return
        
        #Logger.log('d', 'i_value : ' + str(i_value))        
        self._Nb_Layer = i_value
        self._preferences.setValue("squishsquare/nb_layer", i_value)
                
 

