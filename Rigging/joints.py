"""
@package PKD_Tools.Rigging.joint
@brief This deals with rig API related to joints
"""

from pymel import core as pm

from PKD_Tools import libUtilities, libJoint, libVector
from PKD_Tools.Rigging import core


# noinspection PyStatementEffect
class Joint(core.MovableSystem):
    """
    This meta class which creates a joint by default.
    """

    def __init__(self, *args, **kwargs):
        """Override the init to always create joint"""
        kwargs["nodeType"] = "joint"
        kwargs["endSuffix"] = kwargs.get("endSuffix", "Joint")
        super(Joint, self).__init__(*args, **kwargs)
        if self._build_mode:
            self.pynode.side.set(self.pynode.mirrorSide.get())
            # self.pynode.drawLabel.set(True)
            # self.pynode.otherType.set(self.part)
            #

    def buildParent(self, parentClass, side, endSuffix):
        """Add parent node for the joint node. If the parent is a joint, then set the joint orient
        @param parentClass: (metaRig) The parent class that we are trying to create
        @param side: (str) The side side for this parent
        @param endSuffix: (str) The endSuffix for this parent
        """
        prntObj = super(Joint, self).buildParent(parentClass, side, endSuffix)
        if isinstance(prntObj, Joint):
            prntObj.jointOrient = self.jointOrient
        return prntObj

    def setParent(self, targetSystem):
        """
        In case the target system is a joint then ensure their inverse scale are hooked up
        @param targetSystem (metaRig) The target system you are trying to parent to
        """
        targetNode = core.forcePyNode(targetSystem)
        super(Joint, self).setParent(targetNode)
        # Check the node type is joint
        if targetNode.nodeType() == "joint":
            connections = self.pynode.inverseScale.listConnections(plugs=True)
            inverseTarget = connections[0] if connections else None
            if inverseTarget != targetNode.scale:
                targetNode.scale >> self.pynode.inverseScale


class SkinJoint(Joint):
    @property
    def trueName(self):
        return "{0}_{1}".format(self.pynode.mirrorSide.get(asString=True)[0], self.part)


class JointCollection(core.Network):
    """A template class which deals with a collection of joint. This can deal with actual physical joints or locators
    which are proxies for joints"""

    # @cond DOXYGEN_SHOULD_SKIP_THIS
    def __init__(self, *args, **kwargs):
        """
        Joint system initializer
        @param args Any arguements to be passed to the parent
        @param kwargs Any keyword arguements to be passed to the parent

        """
        super(JointCollection, self).__init__(*args, **kwargs)
        if self._build_mode:
            self.jointData = []
        self._rotateOrder = None

    # @endcond

    # noinspection PyPropertyAccess
    def _doxygenHelper(self):
        """
        @property jointData
        @brief This variable is a list of joint data which contains the following information
        - Position in world space
        - The joint orient
        - The name of the joint
        - Whether to mirror this joint
        - The type of mirror ie behaviour vs symmeterical
        @property joints
        @brief Return the list of connected @ref Joint objects
        @property jointList
        @brief Return the list of connected joint names
        @property positions
        @brief Return the positions of the joints in world space
        """
        self.positions = self.joints = self.jointList = self.jointData = None

    # noinspection PyUnresolvedReferences
    def build(self):
        """Build the joints based on data from the @ref jointData joint data"""
        # TODO: When building a mirrored joint. Remove the mirror key and mirror type
        # Iterate though all the joint list
        if self.jointData:
            # Init the metaJoint list
            metaJoints = []
            for i, joint in enumerate(self.jointData):
                # Build a joint based on the name
                metaJoint = self.jointClass(side=self.side, part=joint["Name"])
                # Set the position and joint orientation
                metaJoint.pynode.setTranslation(joint["Position"], space="world")
                if metaJoint.pynode.hasAttr("jointOrient") and joint["JointOrient"]:
                    metaJoint.pynode.jointOrient.set(joint["JointOrient"])
                    for attr in ["jointOrientX", "jointOrientY", "jointOrientZ"]:
                        metaJoint.pynode.attr(attr).setKeyable(True)
                self.setJointRotateOrder(metaJoint)
                if self.mirrorMode != "None":
                    self.mirrorJoint(metaJoint)
                metaJoints.append(metaJoint)
                if i:
                    metaJoint.pynode.setParent(metaJoints[i - 1].mNode)
            # Set the meta joints as the main joints
            self.joints = metaJoints
        else:
            libUtilities.logger.error("No Joint Data Specified")

    def mirrorJoint(self, metaJoint):
        """
        Mirror the meta joint on YZ axis
        @param metaJoint: The meta joint being mirrored
        """
        pass

    def updatePosition(self):
        """Update the position of the joints based on the joint data

        Handles all external edits
        """
        for jointInfo, joint in zip(self.jointData, self.joints):
            joint.pynode.setTranslation(jointInfo["Position"], space="world")

    def setJointRotateOrder(self, metaJoint):
        """Orient created meta joint based on the gimbal data
        @param metaJoint: (str) The joint being created
        """
        pass

    # @cond DOXYGEN_SHOULD_SKIP_THIS
    def __len__(self):
        return len(self.joints)

    def __bindData__(self, *args, **kwgs):
        """Here we are adding a joint attribute which contains the necessary information to construct a joint chain"""
        super(JointCollection, self).__bindData__()
        # ensure these are added by default
        self.addAttr("jointData", [])
        self.addAttr("gimbalData", libJoint.default_gimbal_data())
        self.addAttr("mirror", enumName='None:Behaviour:Orientation', attrType='enum')

    @property
    def joints(self):
        jointAttr = "SUP_Joints"
        if not self.metaCache.setdefault(jointAttr, None):
            self.metaCache[jointAttr] = self.getChildren(asMeta=self.returnNodesAsMeta, cAttrs=[jointAttr])
        return self.metaCache[jointAttr]

    @joints.setter
    def joints(self, jointList):
        if not isinstance(jointList[0], basestring):
            jointList = [joint.mNode for joint in jointList]
        jointAttr = "SUP_Joints"
        self.connectChildren(jointList, jointAttr, cleanCurrent=True)
        if isinstance(jointList[0], core.MetaRig):
            self.metaCache[jointAttr] = jointList
        else:
            self.metaCache[jointAttr] = [core.MetaRig(joint) for joint in jointList]

    @property
    def pyJoints(self):
        key = "pyJoints"
        if not self.metaCache.setdefault(key, []):
            self.metaCache[key] = [joint.pynode for joint in self.joints]
        return self.metaCache[key]

    @property
    def jointList(self):
        key = "jointList"
        if not self.metaCache.setdefault(key, []):
            self.metaCache[key] = [joint.shortName() for joint in self.joints]
        return self.metaCache[key]

    @property
    def positions(self):
        key = "positions"
        if not self.metaCache.setdefault(key, []):
            if self.jointData:
                self.metaCache[key] = [joint["Position"] for joint in self.jointData]
            else:
                libUtilities.logger.error("No joint data found")
        return self.metaCache[key]

    @property
    def midPoint(self):
        key = "midPoint"
        if not self.metaCache.setdefault(key, None):
            self.metaCache[key] = libVector.average(self.positions)
        return self.metaCache[key]

    @property
    def lengths(self):
        key = "lengths"
        if not self.metaCache.setdefault(key, []):
            lengths = []
            for i, position in enumerate(self.positions[:-1]):
                lengths.append(round(libVector.distanceBetween(position, self.positions[i + 1]), 3))
            self.metaCache[key] = lengths
        return self.metaCache[key]

    @property
    def jointClass(self):
        return object
        # @endcond

    @property
    def buildData(self):
        return {"GimbalData": self.gimbalData, "JointData": self.jointData}

    @buildData.setter
    def buildData(self, buildData):
        self.gimbalData = buildData["GimbalData"]
        self.jointData = buildData["JointData"]

    @property
    def rotateOrder(self):
        if not self._rotateOrder:
            self._rotateOrder = libJoint.get_rotate_order(self.gimbalData)
        return self._rotateOrder

    @property
    def mirrorMode(self):
        return self.pynode.mirror.get(asString=True)

    @property
    def jointDict(self):
        key = "jointDict"
        if not self.metaCache.setdefault(key, {}):
            for joint in self.joints:
                self.metaCache[key][joint.part] = joint
        return self.metaCache[key]


class JointSystem(JointCollection):
    """JointCollection class which deals with a collection of joint.

    TODO: it might be more useful to make the JointSystem aware to ignore the last joint instead of making the other
    systems take care of that. Perhaps they can pass on this information to the joint system so that it prunes the last
    joint information when something queries it. It need be it can always be switched to
    """

    def convertJointsToMetaJoints(self):
        """Convert an existing joint chain into a meta joint."""
        # Build the joint data map
        jointData = []
        # Create the temporary pyjoint to retrieve joint orient value
        pyJoints = []
        # Iterate through the existing joints
        for joint in self.joints:
            # Move the joint in world space
            joint = core.forcePyNode(joint)
            joint.setParent(w=1)
            # Freeze all transform information to get the joint orient
            libUtilities.freeze_transform(joint)
            # TODO: Need to refactorise this when using for anno
            jointData.append({
                "Name": joint.shortName(),
                "JointOrient": list(joint.jointOrient.get()),
                "Position": list(joint.getTranslation(space="world"))
            })
            pyJoints.append(joint)

        # Set the new joint data
        self.jointData = jointData

        # Build the data
        self.build()
        # Delete the old joints
        pm.delete(pyJoints)

    def rebuild_joint_data(self):
        """Rebuild the joint data"""
        jointData = []
        # Iterate through all joint
        for joint in self.joints:
            # Select the joint
            joint.pynode.select()
            # Create a joint
            newJoint = pm.joint(rotationOrder=self.rotateOrder)
            # Set it to world space
            newJoint.setParent(w=1)
            # Read the new joint infomrmation
            jointData.append({
                "Name": joint.part,
                "JointOrient": list(newJoint.jointOrient.get()),
                "Position": list(newJoint.getTranslation(space="world"))
            })
            # Delete joint
            pm.delete(newJoint)
        # Set the joint data
        self.jointData = jointData

    def build(self):
        """Rebuild the joint data if it is orientated"""
        super(JointSystem, self).build()
        if self.mirrorMode != "None":
            if self.mirrorMode == "Orientation":
                libJoint.orient_joint(joint=self.joints[0].pynode,
                                      up=self.gimbalData["twist"],
                                      forward=self.gimbalData["roll"],
                                      **self.gimbalData
                                      )
            self.rebuild_joint_data()

    def setParent(self, targetSystem):
        """
        Always parent the first joint to the the transform/pynode
        @param targetSystem (metaRig,pynode,string) The target transform node
        """
        # get the target node
        self.joints[0].setParent(targetSystem)

    def setRotateOrder(self, rotateOrder):
        """Set the rotate order
        @param rotateOrder: (str) The rotate order that is to be set
        """
        for joint in self.joints:
            joint.rotateOrder = rotateOrder

    def replicate(self, *args, **kwargs):
        """
        Create a new joint system object based on existing one. This can be customised to have new suffix or partial
        chain.

        The easiest way to have customised suffix is to give an keyword argument
        """
        if self.jointData:
            supportType = kwargs.get("supportType")
            if supportType == "Skin":
                replicateJointSystem = SkinJointSystem(*args, **kwargs)
            else:
                # New joint system option
                replicateJointSystem = JointSystem(*args, **kwargs)
            # Here we have a customised joint system where it acts as a support system
            if supportType:
                # Change the system name
                newSuffix = kwargs["supportType"] + "Sys"
                replicateJointSystem.rigType = newSuffix
                # Set the start position
                startPosition = kwargs.get("startPosition", 0)
                # Get the end position
                endPosition = kwargs.get("endPosition", None)
                # Copy the joint data
                joint_data = self.jointData[startPosition:endPosition]
                # Add the suffix to the name for support type
                if supportType != "Skin":
                    for jointInfo in joint_data:
                        jointInfo["Name"] = jointInfo["Name"] + kwargs["supportType"]
                # Set the joint data
                replicateJointSystem.jointData = joint_data

            # Get the gimbal data
            replicateJointSystem.gimbalData = self.gimbalData

            # Set the rotate order
            replicateJointSystem.setRotateOrder(self.joints[0].rotateOrder)

            # Build the joints
            if kwargs.get("build", True):
                # Copy the data across
                replicateJointSystem.jointData = replicateJointSystem.jointData or self.jointData
                replicateJointSystem.build()

            # Return the joint system
            return replicateJointSystem
        else:
            libUtilities.logger.error("Unable to replicate as there is no existing joint data")

    def setJointRotateOrder(self, metaJoint):
        """Orient created meta joint based on the gimbal data
        @param metaJoint: (MetaJoint) the target joint
        """
        metaJoint.rotateOrder = self.rotateOrder

    def mirrorJoint(self, metaJoint):
        """
        Mirror the meta joint on YZ axis
        @param metaJoint: The meta joint being mirrored
        """
        mirrorKwargs = {"mirrorYZ": True}
        if self.mirrorMode == "Behaviour":
            mirrorKwargs["mirrorBehavior"] = True
        mirroredJoint = pm.mirrorJoint(metaJoint.pynode, **mirrorKwargs)[0]
        metaJoint.snap(mirroredJoint)
        libUtilities.freeze_rotation(metaJoint.pynode)
        pm.delete(mirroredJoint)


    @property
    def jointClass(self):
        return Joint


class SkinJointSystem(JointSystem):
    def build(self):
        super(SkinJointSystem, self).build()
        for joint in self.joints:
            joint.resetName()

    @property
    def jointClass(self):
        return SkinJoint


core.Red9_Meta.registerMClassInheritanceMapping()
