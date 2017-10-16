"""
@package PKD_Tools.libGeo
@brief This package contains utilities specifically related to geo such as wrap deformer command or create_wrap
the convert_joint_to_cluster
"""

import tempfile
import os

from maya import cmds, mel
import pymel.core as pm
from PKD_Tools import logger
from PKD_Tools.Rigging import utils

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
        if top.type() == "transform":
            if not top.getShape():
                topNodes.append(top)
    return len(topNodes) > 1


def find_hierarchy_errors(topNode):
    """ Return a dictanary of lists with common hierarchy errors
    @param topNode (pynode, string) The top node of a group
    @return A dictionary of errors
    """
    duplicateTransform = []
    duplicateShapes = []
    namespaceTransform = []
    geoWithHistory = []
    incorrectShapes = []

    for mesh in pm.listRelatives(topNode, type="mesh", ad=1, ni=True):
        meshParent = mesh.getParent()
        # Check shapes with namespace
        if ":" in mesh.name():
            namespaceTransform.append(meshParent)
        # Check duplicate shapes
        if "|" in mesh.name():
            duplicateShapes.append(mesh)

        # Check the shape name is name correctly
        if ("%sShape" % meshParent.name()) != mesh.name():
            incorrectShapes.append(mesh)

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
            "Incorrect Shape Names": incorrectShapes,
            "History Geos": geoWithHistory
            }


def fix_duplicates_shapes(duplicateShapes=None):
    """ Attempt to fix duplicate shapes by renaming based on parent dags name
    @param duplicateShapes (list) Pynodes with duplicated shapes
    """
    if not duplicateShapes:
        duplicateShapes = []
    for duplicateShape in duplicateShapes:
        parentName = duplicateShape.getParent().name()
        duplicateShape.rename(parentName + "Shape")


class ObjManager(object):
    """Class to manage obj import/export. This class also maintains hierarchy and pivot information. However the 
    hierarchy must be clean of any common issues such as duplicate transform name.
    @attention The obj plugin is loaded by default for safety whenever this class is initialised"""

    def __init__(self):
        """@property new_scene
        @brief Is the obj hierarchy being imported into a new scene. Useful if you want to start from scratch
        @property cleansing_mode
        @brief In cleansing the mode the original geometery is deleted as soon as it is exported. This way any
        shader information is not lost
        @property hierarchy_file_info
        @brief The file which contains all the hierarchy information such as structure and pivots
        @property geo_file_info
        @brief The file which contains information about all geo that was exported and it's current path
        @property progress_tracker
        @brief The PyQt object which updates

        """
        self._top_node_ = None
        self._export_dir_ = None
        self._geo_list_ = []
        # Load the objExport
        cmds.loadPlugin("objExport.mll", quiet=True)
        self.new_scene = False
        self.cleansing_mode = False
        self.progress_tracker = None
        self.current_target = None
        self.current_mode = ""

    def write_hierarchy_data(self):
        """Write the current scale and rotate pivots of all the transform in the hierarchy to a json file"""
        # Get hierarchy data
        hierarchy = []
        pivots = {}
        for transform in pm.listRelatives(self.top_node, type="transform", ad=1, ni=True) + [pm.PyNode(self.top_node)]:
            # Get the long name to build a proper hierarchy
            hierarchy.append(transform.longName())
            pivots[transform.name()] = {
                "RotatePivot": list(transform.getRotatePivot()),
                "ScalePivot": list(transform.getScalePivot())
            }

        # Sort the hierarchy by string size
        hierarchy.sort(key=len)
        info = {"hierarchy": hierarchy, "pivots": pivots}
        self.hierarchy_file_info = info

    def export_hierarchy_obj(self):
        """Export the individual meshes in the hierarchy"""
        file_info = {}
        # Reverse the geo list so that the deepest geo is deleted first in case there is a geo inside geo
        geo_list = self.geo_list
        geo_list.reverse()
        for self.current_target in geo_list:
            pm.delete(self.current_target, ch=1)
            parent = pm.listRelatives(self.current_target, parent=True)
            pm.parent(self.current_target, w=True)
            pm.select(self.current_target)
            path = libFile.linux_path(libFile.join(self.export_dir, self.current_target + ".obj"))
            # Load the obj plugin
            cmds.file(path,
                      pr=1,
                      typ="OBJexport",
                      force=1,
                      options="groups=0;ptgroups=0;materials=0;smoothing=0;normals=0",
                      es=1)
            file_info[self.current_target] = path
            logger.info("Exporting\n%s" % file_info[self.current_target])
            if not self.new_scene and self.cleansing_mode:
                pm.delete(self.current_target)
                pm.refresh()
            else:
                pm.parent(self.current_target, parent)

            self.update_progress()

        # Write the geo file_info
        self.geo_file_info = file_info

    def import_hierarchy_geo(self):
        """Import all the obj objects"""
        file_info = self.geo_file_info
        for self.current_target in file_info.keys():
            cmds.file(file_info[self.current_target],
                      rpr="PKD_Temp",
                      i=1,
                      type="OBJ",
                      loadReferenceDepth="all",
                      ra=True,
                      mergeNamespacesOnClash=False,
                      options="mo=1")
            # Delete Existing geo if it exists
            if not self.cleansing_mode:
                if pm.objExists(self.current_target):
                    pm.delete(self.current_target)
            logger.info("Importing\n%s" % file_info[self.current_target])
            if self.cleansing_mode:
                os.remove(file_info[self.current_target])
            for top in pm.ls(assemblies=True, ud=True):
                if top.getShape():
                    if top.getShape().type() == "mesh" and top.name() == "PKD_Temp_Mesh":
                        top.rename(self.current_target)
                        pm.select(self.current_target)
                        mel.eval("polySetToFaceNormal")
                        mel.eval("polySoftEdge -a 180 -ch 1 %s" % self.current_target)
                        pm.delete(self.current_target, ch=1)
                        pm.refresh()
            self.update_progress()

    def rebuild_hierarchy(self):
        """ Rebuild the hierarchy by reading the hierarchy info file"""
        read_info = self.hierarchy_file_info

        # Rebuild the hierarchy
        for transform in read_info["hierarchy"]:
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

            # Set the hierarchy
            pm.setAttr(target.scalePivot, read_info["pivots"][target.name()]["ScalePivot"])
            pm.setAttr(target.rotatePivot, read_info["pivots"][target.name()]["RotatePivot"])

    def cleanse_geo(self):
        """Cleanse the model of all issues with the help of obj"""
        self.export_all()
        self.setup_cleanse_scene()
        self.import_all()
        logger.info("Scene Is Cleansed")

    def setup_cleanse_scene(self):
        if self.new_scene:
            cmds.file(new=1, f=1)
        libUtilities.set_persp()
        if self.new_scene:
            pm.createNode("transform", n=self.top_node)

        # Reset the top node
        topNode = pm.PyNode(self.top_node)
        topNode.scale.unlock()
        topNode.translate.unlock()

    def export_all(self):
        """Export All Geo and hierarchy info"""
        libUtilities.freeze_transform(self.top_node)
        self.current_mode = "Export"
        self.write_hierarchy_data()
        self.export_hierarchy_obj()

    def import_all(self):
        """Import All Geo and hierarchy info"""
        self.current_mode = "Import"
        self.import_hierarchy_geo()
        pm.select(cl=1)
        mel.eval("FrameAll;")
        self.rebuild_hierarchy()
        return self._geo_list_

    def update_progress(self):
        # Update the progress tracker
        if self.progress_tracker is not None:
            # self.progress_tracker.set_current_status()
            self.progress_tracker.currentTarget = self.current_target
            self.progress_tracker.update()

    # @cond DOXYGEN_SHOULD_SKIP_THIS

    @property
    def top_node(self):
        """Get the top node name. If it is defined then find it by searching the top group"""
        if not self._top_node_:
            self._top_node_ = str(get_top_node())
        return self._top_node_

    @top_node.setter
    def top_node(self, node):
        """Set the top node name as string"""
        # Recieve data about the top node. Make sure it is a string
        self._top_node_ = str(node)

    @property
    def geo_list(self):
        """Get a string list of geos"""
        if not self._geo_list_:
            if self.current_mode == "Export":
                self._geo_list_ = [geo.getParent().name() for geo in
                                   pm.listRelatives(self.top_node, type="mesh", ad=1, ni=True)]
            else:
                self._geo_list_ = self.geo_file_info.keys()
        return self._geo_list_

    @property
    def export_dir(self):
        """Get the Export Directory """
        if self._export_dir_ is None:
            self._export_dir_ = tempfile.gettempdir()
        return self._export_dir_

    @export_dir.setter
    def export_dir(self, path):
        """Set the Export Directory """
        self._export_dir_ = libFile.folder_check_advanced(path)

    @property
    def datapath(self):
        """File path to the json file which contains the hierarchy info."""
        return libFile.linux_path(libFile.join(self.export_dir, "hierarchy_info.json"))

    @property
    def geoListPath(self):
        """File path which contains information of exported geometery and the associated path."""
        return libFile.linux_path(libFile.join(self.export_dir, "geo_list.json"))

    @property
    def geo_file_info(self):
        """Read the geo path info from a json file"""
        if not libFile.exists(self.geoListPath):
            raise RuntimeError("No geo has been exported to this path")
        return libFile.load_json(self.geoListPath)

    @geo_file_info.setter
    def geo_file_info(self, path_info):
        """Write the geo path info to json file"""
        # Write JSON data
        libFile.write_json(self.geoListPath, path_info)

    @property
    def hierarchy_file_info(self):
        """Read the hierarchy info from a json file"""
        if not libFile.exists(self.datapath):
            raise RuntimeError("No geo has been exported to this path")
        return libFile.load_json(self.datapath)

    @hierarchy_file_info.setter
    def hierarchy_file_info(self, hierarchy_info):
        """Write the hierarchy info into a json file"""
        libFile.write_json(self.datapath, hierarchy_info)
        # @endcond


def convert_joint_to_cluster(targetGeo, skipList=None, info=False):
    """
    Convert a skin cluster to a cluster based setup on a target geometery
    @param info: Whether to just query the data for in case we are building it later
    @param skipList: The joints which need to be skipped
    @param targetGeo: (string/pynode) The geometry which has the skin cluster
    @param skipList: (list) Any joints which should not processed such as a base joint
    @return A dictionary of cluster with the name of the joints as keys

    """
    if skipList is None:
        skipList = []
        # Convert to PyNode
    targetGeo = libUtilities.force_pynode(targetGeo)
    skin_name = libUtilities.get_target_defomer(targetGeo, "skinCluster")
    skin = libUtilities.force_pynode(skin_name)
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
            raise RuntimeError("Current Joint Has No Vertices:%s" % jnt)
        pm.select(vertZip)

        # Iterate through selection and decompress vertix group into individual index
        vertices = libUtilities.indexize_vertice_group(pm.selected())

        joint_position = pm.xform(jnt, q=1, ws=1, rp=1)
        # Select Vertices
        if info:
            clusterInfo[jnt.name()] = {"vertices": libUtilities.stringList(vertices),
                                       "weight": weightList,
                                       "position": joint_position}
        else:
            libUtilities.select_vertices(targetGeo, vertices)
            # Make a cluster
            cluster_info = weighted_cluster(targetGeo, vertices, weightList, joint_position)

            # Add to dictionary
            clusterInfo[jnt.name()] = cluster_info

        # Update Progress
        currentJnt += 1.0
        currentProgress = (currentJnt / totalJnts) * 100
        pm.progressWindow(edit=True, progress=currentProgress, status=('Progress: ' + str(int(currentProgress)) + '%'))
        pm.refresh()
        if info:
            logger.info("Info gathered: " + jnt.name())
        else:
            logger.info("Converted: " + jnt.name())

    pm.progressWindow(endProgress=1)
    return clusterInfo


def weighted_cluster(target_geo, vertices, weight_list, joint_position):
    """
    Created a relative weighted cluster
    @param target_geo: The geo which will get the cluster
    @param vertices: The vertices which form the cluster
    @param weight_list: The weight map for the cluster
    @param joint_position: The pivot of the cluster
    @return: The created transform and cluster node
    """
    libUtilities.select_vertices(target_geo, vertices)
    # Make a cluster
    cltr, cTransform = pm.cluster(rel=1, foc=True)
    pm.setAttr(cTransform.scalePivot, joint_position)
    pm.setAttr(cTransform.rotatePivot, joint_position)

    # Set the weight
    for index, weight in zip(vertices, weight_list):
        cltr.weightList[0].weights[index].set(weight)

    # Set the weight
    for index, weight in zip(vertices, weight_list):
        cltr.weightList[0].weights[index].set(weight)

    return {"cluster": cltr, "clusterHandle": cTransform}


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


def create_follicle(position, geo=None):
    """
    Create a follice for a position on a target geometery. Converted to Pymel version of the following script
    http://www.tommasosanguigni.it/blog/function-createfollicle/
    @param position (vector) The target position
    @param geo (pynode) The target geo
    @return: follicle transform
    """
    if geo is None:
        raise RuntimeError("Please provide a geo name")
    if geo.getShape().type() not in ["nurbsSurface", "mesh"]:
        raise ValueError("Geometry must be mesh of nurbSurface")
    else:
        transform_node = pm.createNode("transform")
        transform_node.translate.set(position)

        # make vector product nodes to get correct rotation of the transform node
        vector_product = pm.createNode("vectorProduct")
        vector_product.operation.set(4)
        transform_node.worldMatrix >> vector_product.matrix
        transform_node.rotatePivot >> vector_product.input1

        # connect the correct position to a closest point on surface node created
        if geo.getShape().type() == "nurbsSurface":
            closest_position = pm.createNode("closestPointOnSurface", n=(transform_node + "_CPOS"))
            geo.ws >> closest_position.inputSurface
        else:
            closest_position = pm.createNode("closestPointOnMesh", n=(transform_node + "_CPOS"))
            geo.outMesh >> closest_position.inMesh

        vector_product.output >> closest_position.inPosition

        # create a follicle node and connect it

        follicle = pm.createNode("follicle")
        follicle_transform = follicle.getParent()

        follicle.outTranslate >> follicle_transform.translate
        follicle.outRotate >> follicle_transform.rotate

        if geo.getShape().type() == "nurbsSurface":
            geo.local >> follicle.inputSurface
        else:
            geo.outMesh >> follicle.inputMesh

        geo.worldMatrix >> follicle.inputWorldMatrix

        follicle.parameterU.set(closest_position.parameterU.get())
        follicle.parameterV.set(closest_position.parameterV.get())

        # Delete nodes
        pm.delete(transform_node)
        pm.delete(closest_position)
        return follicle_transform


# noinspection PyStatementEffect
def create_point_on_mesh(geo, position, sticky_target, free_rotation=True):
    """
    Create point on mesh setup
    @param position:
    @param geo:
    @parem sticky:
    @return:
    """

    pom = pm.createNode("closestPointOnMesh")
    pom.inPosition.set(position)

    geo.worldMatrix[0] >> pom.inputMatrix
    geo.worldMesh[0] >> pom.inMesh

    pom.position >> sticky_target.translate

    index = pom.closestVertexIndex.get()

    locator = pm.spaceLocator()
    libUtilities.snap(locator, geo.vtx[index], rotate=False)
    libUtilities.freeze_transform(locator)
    pm.pointOnPolyConstraint(geo.vtx[index], locator, maintainOffset=True)

    pm.delete(pom)
    constraint = pm.listRelatives(locator, type="constraint")[0]
    if free_rotation:
        for attr in ["rx", "rz", "ry"]:
            libUtilities.break_connection(locator, attr)
            locator.attr(attr).set(0)
    return {"constraint": constraint, "locator": locator}


def create_sticky_control(geo,
                          position,
                          name,
                          setup_type="follicle",
                          free_rotation=True):
    """
    Temp setup to create sticky control at position for given geometry
    @param setup_type:
    @param position (vector) The position in worldspace where this will created
    @param geo (pynode) The target geometry
    @param name (string) The prefix identifier given to this setup
    @param free_rotation (bool) Whether the rotation are free
    @return: A dict of control object and object which is constraining.
    TODO:

    """

    # Create space locator
    geo = libUtilities.force_pynode(geo)

    # Create the ctrl obj
    new_ctrl = libUtilities.Ctrl(name)
    tempCtrlShape = utils.buildCtrlShape("Spike")
    libUtilities.transfer_shape(tempCtrlShape, new_ctrl.ctrl,True)
    libUtilities.fix_shape_name(new_ctrl.ctrl)
    pm.delete(tempCtrlShape)

    info = {"ctrl": new_ctrl}
    if setup_type == "follicle":
        new_ctrl.prnt.translate.set(position)
        # Create the follice and point constraint
        follicle = create_follicle(position, geo)
        follicle.rename("{}_fol".format(name))
        if free_rotation:
            pm.pointConstraint(follicle, new_ctrl.prnt)
        else:
            pm.parentConstraint(follicle, new_ctrl.prnt)
        # Create a translate cycle
        info["sticky_source"] = follicle
        md = pm.createNode("multiplyDivide", name=name + "_MD")
        md.input2.set([-1, -1, -1])

        new_ctrl.ctrl.translate >> md.input1
        md.output >> new_ctrl.xtra.translate

        info["multiplyDivide"] = md
    else:
        new_info = create_point_on_mesh(geo, position, new_ctrl.prnt, free_rotation)
        info.update(new_info)
        if free_rotation:
            libUtilities.cheap_point_constraint(new_info["locator"],
                                                new_ctrl.prnt)
        else:
            pm.parentConstraint(new_info["locator"], new_ctrl.prnt)
        new_info["locator"].rename("{}_loc".format(name))
        new_info["constraint"].rename("{}_popCon".format(name))

    return info


if __name__ == '__main__':
    win = ObjManager()
    win.cleansing_mode = True
    win.cleanse_geo()
