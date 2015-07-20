"""
@package PKD_Tools.libGeo
@brief This package contains utilities specifically related to geo such as wrap deformer command or create_wrap
the convert_joint_to_cluster
"""

import tempfile
import os
import json

from maya import cmds, mel
import pymel.core as pm
from pymel.internal.plogging import pymelLogger as pyLog

import libUtilities
import libFile


def get_top_node():
    """Return the first top group transform node in the scene. Ignore all top level meshes"""
    for top in pm.ls(assemblies=True, ud=True):
        if not top.getShape():
            return top


def multiple_top_nodes_exists():
    """Check if the the scene has multiple top level groups"""
    topNodes = []
    for top in pm.ls(assemblies=True, ud=True):
        if not top.getShape():
            topNodes.append(top)
    return len(topNodes) > 1


def find_heirachy_errors(topNode):
    """ Return a dictanary of lists with common heirachy errors
    @param topNode The top node of a group
    @return A dictonary of errors
    """
    duplicateTransform = []
    duplicateShapes = []
    namespaceTransform = []
    geoWithHistory = []

    for mesh in pm.listRelatives(topNode, type="mesh", ad=1, ni=True):
        meshParent = mesh.getParent()
        # Check shapes with namespace
        if ":" in mesh.name():
            namespaceTransform.append(meshParent)
        # Check duplicate shapes
        if "|" in mesh.name():
            duplicateShapes.append(mesh)

        # Check geo with history
        if pm.listHistory(meshParent, ha=1, pdo=1):
            geoWithHistory.append(meshParent)

    for transform in pm.listRelatives(topNode, type="transform", ad=1, ni=True):
        # Check duplicate transform names
        if "|" in transform.name():
            duplicateTransform.append(transform)

    return {"Namespace Transform": namespaceTransform,
            "Duplicate Shapes": duplicateShapes,
            "Duplicate Transform": duplicateTransform,
            "History Geos": geoWithHistory
            }


def fix_duplicates_shapes(duplicateShapes=None):
    """ Attempt to fix duplicate shapes by renaming based on parent dags name
    @param duplicateShapes list of pynodes with duplicated shapes
    """
    if not duplicateShapes:
        duplicateShapes = []
    for duplicateShape in duplicateShapes:
        parentName = duplicateShape.getParent().name()
        duplicateShape.rename(parentName + "Shape")


class ObjManager(object):
    def __init__(self):
        super(ObjManager, self).__init__()
        self._top_node_ = None
        self._export_dir_ = None
        self._geo_list_ = []
        # Load the objExport
        cmds.loadPlugin("objExport.mll")
        self.new_scene = False
        self.cleansing_mode = False

    def write_heirachy_data(self):
        """Write the current scale and rotate pivots of all the transform in the heirachy to a json file"""
        # Get heirachy data

        hierachy = []
        pivots = {}
        for transform in pm.listRelatives(self.top_node, type="transform", ad=1, ni=True) + [pm.PyNode(self.top_node)]:
            # Get the long name to build a proper heirachy
            hierachy.append(transform.longName())
            pivots[transform.name()] = {
                "RotatePivot": list(transform.getRotatePivot()),
                "ScalePivot": list(transform.getScalePivot())
            }

        # Sort the heirachy by string size
        hierachy.sort(key=len)
        info = {"heirachy": hierachy, "pivots": pivots}
        self.heirachy_file_info = info

    def export_heirachy_obj(self):
        fileInfo = {}
        # Reverse the geo list so that the deepest geo is deleted first in case there is a geo inside geo
        geo_list = self.geo_list
        geo_list.reverse()
        for geo in geo_list:
            pm.delete(geo, ch=1)
            parent = pm.listRelatives(geo, parent=True)
            pm.parent(geo, w=True)
            pm.select(geo)
            path = libFile.linux_path(libFile.join(self.export_dir, geo + ".obj"))
            # Load the obj plugin
            cmds.file(path,
                      pr=1,
                      typ="OBJexport",
                      force=1,
                      options="groups=0;ptgroups=0;materials=0;smoothing=0;normals=0",
                      es=1)
            fileInfo[geo] = path
            pyLog.info("Exporting\n%s" % fileInfo[geo])
            if not self.new_scene and self.cleansing_mode:
                pm.delete(geo)
                pm.refresh()
            else:
                pm.parent(geo, parent)

        # Write the geo file_info
        self.geo_file_info = fileInfo

    def import_heirachy_geo(self):
        """Import all the obj objects"""
        fileInfo = self.geo_file_info
        for geo in fileInfo.keys():
            cmds.file(fileInfo[geo],
                      rpr="PKD_Temp",
                      i=1,
                      type="OBJ",
                      loadReferenceDepth="all",
                      ra=True,
                      mergeNamespacesOnClash=False,
                      options="mo=1")
            # Delete Existing geo if it exists
            if not self.cleansing_mode:
                if pm.objExists(geo):
                    pm.delete(geo)
            pyLog.info("Importing\n%s" % fileInfo[geo])
            if self.cleansing_mode:
                os.remove(fileInfo[geo])
            for top in pm.ls(assemblies=True, ud=True):
                if top.getShape():
                    if top.getShape().type() == "mesh" and top.name()== "PKD_Temp_Mesh":
                        # pm.parent(top, self.top_node)
                        top.rename(geo)
                        pm.select(geo)
                        mel.eval("polySoftEdge -a 180 " + geo)
                        mel.eval("polySetToFaceNormal")
                        pm.delete(geo, ch=1)
                        pm.refresh()

    def rebuild_heirachy(self):
        # Rebuild the heirachy by reading the scene info file
        read_info = self.heirachy_file_info

        # Rebuild the heirachy
        for transform in read_info["heirachy"]:
            # Split the names
            splitNames = transform.split("|")

            # Get the current transform name
            target = splitNames[-1]

            if not pm.objExists(target):
                # If does not exist create a empty group
                target = pm.createNode("transform", name=target)
            else:
                # Otherwise convert to pynode
                target = pm.PyNode(target)

            # Does it have parents?
            if len(splitNames) > 2:
                # Get the parent name
                parent = pm.PyNode("|".join(splitNames[:-1]))

                # Set the parent name
                target.setParent(parent)

            # Set the heirachy
            pm.setAttr(target.scalePivot, read_info["pivots"][target.name()]["ScalePivot"])
            pm.setAttr(target.rotatePivot, read_info["pivots"][target.name()]["RotatePivot"])

    def cleanse_geo(self):
        """Cleanse the model of all issues with the help of obj"""
        self.export_all()
        if self.new_scene:
            cmds.file(new=1, f=1)

        libUtilities.set_persp()
        if self.new_scene:
            pm.createNode("transform", n=self.top_node)

        # Reset the top node
        topNode = pm.PyNode(self.top_node)
        topNode.scale.unlock()
        topNode.translate.unlock()

        self.import_all()
        pyLog.info("Geo Is Cleansed")

    def export_all(self):
        # Export All Geo and heirachy info
        libUtilities.freeze_transform(self.top_node)
        self.write_heirachy_data()
        self.export_heirachy_obj()

    def import_all(self):
        # Import All Geo and heirachy info
        self.import_heirachy_geo()
        pm.select(cl=1)
        mel.eval("FrameAll;")
        self.rebuild_heirachy()

        return self._geo_list_
    #
    # def freeze_heirachy(self):
    #     """
    #     Freeze all the transform node in the heirachy
    #     """
    #     for transform in pm.listRelatives(self.top_node, type="transform", ad=1, ni=True) + [self.top_node]:
    #         try:
    #             pm.makeIdentity(transform, n=0, s=1, r=1, t=1, apply=True, pn=1)
    #         except:
    #             raise Exception("Unable to freeze transforms on: %s" % transform.name())

    @property
    def top_node(self):
        """Get the top node"""
        if not self._top_node_:
            self._top_node_ = str(get_top_node())
        return self._top_node_

    @top_node.setter
    def top_node(self, node):
        # Recieve data about the top node. Make sure it is a string
        self._top_node_ = str(node)

    @property
    def geo_list(self):
        """Get a string list of geos"""
        if not self._geo_list_:
            self._geo_list_ = [geo.getParent().name() for geo in
                               pm.listRelatives(self.top_node, type="mesh", ad=1, ni=True)]
        return self._geo_list_

    @property
    def export_dir(self):
        """Export Directory """
        if self._export_dir_ is None:
            self._export_dir_ = tempfile.gettempdir()
        return self._export_dir_

    @export_dir.setter
    def export_dir(self, path):
        self._export_dir_ = libFile.linux_path(path)

    @property
    def datapath(self):
        """File path to the json file which contains the heirachy info."""
        return libFile.linux_path(libFile.join(self.export_dir, "heirachy_info.json"))

    @property
    def geoListPath(self):
        """File path which contains information of exported geometery and the associated path."""
        return libFile.linux_path(libFile.join(self.export_dir, "geo_list.json"))

    @property
    def geo_file_info(self):
        """Read the geo path info"""
        if not libFile.exists(self.geoListPath):
            raise Exception("No geo has been exported to this path")
        with open(self.geoListPath, 'r') as f:
            return json.load(f)

    @geo_file_info.setter
    def geo_file_info(self, path_info):
        # Write JSON data
        with open(self.geoListPath, 'w') as f:
            json.dump(path_info, f)

    @property
    def heirachy_file_info(self):
        """Read the heirachy info"""
        if not libFile.exists(self.datapath):
            raise Exception("No geo has been exported to this path")
        with open(self.datapath, 'r') as f:
            return json.load(f)

    @heirachy_file_info.setter
    def heirachy_file_info(self, heirachy_info):
        # Write JSON data
        with open(self.datapath, 'w') as f:
            json.dump(heirachy_info, f)



def convert_joint_to_cluster(targetGeo, skipList=[]):
    """
    Convert a skin cluster to a cluster based setup on a target geometery
    @param targetGeo: the geometery which has the skin cluster
    @param skipList: any joints which should not processed such as a base joint
    @return A dictonary of cluster with the name of the joints as keys

    """
    # Convert to PyNode
    targetGeo = pm.PyNode(targetGeo)
    skin = libUtilities.get_target_defomer(targetGeo, "skinCluster")

    # Create the dictionary
    clusterInfo = {}
    # Progress Info
    pm.progressWindow(title='Converting Skin To Cluster', progress=0, status='Progress: 0%')
    totalJnts = len(skin.getInfluence()) - len(skipList)
    currentJnt = 0.0

    # Go through Each Joint
    for jnt in sorted(skin.getInfluence()):
        if jnt.name() in skipList:
            continue
        # Get the vertex affected and the weight
        vertZip, weightList = skin.getPointsAffectedByInfluence(jnt)
        if not vertZip:
            raise Exception("Current Joint Has No Vertices:%s" % jnt)
        pm.select(vertZip)

        # Iterate through selection and decompress vertic group  into individual index
        vertices = libUtilities.indexize_vertice_group(pm.selected())
        # Select Vertices
        libUtilities.select_vertices(targetGeo, vertices)
        # Make a cluster
        cltr, cTransform = pm.cluster(rel=1)
        jntPos = pm.xform(jnt, q=1, ws=1, rp=1)
        pm.setAttr(cTransform.scalePivot, jntPos)
        pm.setAttr(cTransform.rotatePivot, jntPos)

        # Set the weight
        for index, weight in zip(vertices, weightList):
            cltr.weightList[0].weights[index].set(weight)

        # Add to dictionary
        clusterInfo[jnt.name()] = {"cluster": cltr, "clusterHandle": cTransform}

        # Update Progress
        currentJnt = currentJnt + 1.0
        currentProgress = (currentJnt / totalJnts) * 100
        pm.progressWindow(edit=True, progress=currentProgress, status=('Progress: ' + str(int(currentProgress)) + '%'))
        pm.refresh()
        pyLog.info("Converted: " + jnt.name())

    pm.progressWindow(endProgress=1)
    return clusterInfo


def create_wrap(*args, **kwargs):
    """
    This is just to script out a Maya Wrap deformer as there no mel command for it. In addition to this when working
    with the default command on referenced model, it makes the hated "ShapeDeformed" node and converts the
    reference source shape into a intermediate.  This method avoids that issue

    source: http://artofrigging.com/scripting-mayas-wrap-deformer/

    @return The wrap deformer node
    """

    source = str(args[0])
    target = str(args[1])

    influenceShape = cmds.listRelatives(source, shapes=True, noIntermediate=True)[0]

    # create wrap deformer
    weightThreshold = kwargs.get('weightThreshold', 0.0)
    maxDistance = kwargs.get('maxDistance', 1.0)
    exclusiveBind = kwargs.get('exclusiveBind', False)
    autoWeightThreshold = kwargs.get('autoWeightThreshold', True)
    falloffMode = kwargs.get('falloffMode', 0)

    # Make a front of chain deformer
    wrapData = cmds.deformer(target, type='wrap', foc=True)
    wrapNode = wrapData[0]

    cmds.setAttr(wrapNode + '.weightThreshold', weightThreshold)
    cmds.setAttr(wrapNode + '.maxDistance', maxDistance)
    cmds.setAttr(wrapNode + '.exclusiveBind', exclusiveBind)
    cmds.setAttr(wrapNode + '.autoWeightThreshold', autoWeightThreshold)
    cmds.setAttr(wrapNode + '.falloffMode', falloffMode)

    cmds.connectAttr(target + '.worldMatrix[0]', wrapNode + '.geomMatrix')

    # add influence
    duplicateData = cmds.duplicate(source, name=source + 'Base')
    base = duplicateData[0]
    shapes = cmds.listRelatives(base, shapes=True)
    baseShape = shapes[0]
    cmds.hide(base)

    # create dropoff attr if it doesn't exist
    if not cmds.attributeQuery('dropoff', n=source, exists=True):
        cmds.addAttr(source, sn='dr', ln='dropoff', dv=4.0, min=0.0, max=20.0)
        cmds.setAttr(source + '.dr', k=True)

    # if type mesh
    if cmds.nodeType(influenceShape) == 'mesh':
        # create smoothness attr if it doesn't exist
        if not cmds.attributeQuery('smoothness', n=source, exists=True):
            cmds.addAttr(source, sn='smt', ln='smoothness', dv=0.0, min=0.0)
            cmds.setAttr(source + '.smt', k=True)

        # create the inflType attr if it doesn't exist
        if not cmds.attributeQuery('inflType', n=source, exists=True):
            cmds.addAttr(source, at='short', sn='ift', ln='inflType', dv=2, min=1, max=2)

        cmds.connectAttr(influenceShape + '.worldMesh', wrapNode + '.driverPoints[0]')
        cmds.connectAttr(baseShape + '.worldMesh', wrapNode + '.basePoints[0]')
        cmds.connectAttr(source + '.inflType', wrapNode + '.inflType[0]')
        cmds.connectAttr(source + '.smoothness', wrapNode + '.smoothness[0]')

    # if type nurbsCurve or nurbsSurface
    if cmds.nodeType(influenceShape) == 'nurbsCurve' or cmds.nodeType(influenceShape) == 'nurbsSurface':
        # create the wrapSamples attr if it doesn't exist
        if not cmds.attributeQuery('wrapSamples', n=source, exists=True):
            cmds.addAttr(source, at='short', sn='wsm', ln='wrapSamples', dv=10, min=1)
            cmds.setAttr(source + '.wsm', k=True)

        cmds.connectAttr(influenceShape + '.ws', wrapNode + '.driverPoints[0]')
        cmds.connectAttr(baseShape + '.ws', wrapNode + '.basePoints[0]')
        cmds.connectAttr(source + '.wsm', wrapNode + '.nurbsSamples[0]')

    cmds.connectAttr(source + '.dropoff', wrapNode + '.dropoff[0]')

    return pm.PyNode(wrapNode)
