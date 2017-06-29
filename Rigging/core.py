"""
@package PKD_Tools.Rigging.core
@brief The main core classes for the PKD rig system. All new system are created here until they can be grouped together to create new packages.
@details The PKD rig system uses the combination of the Red9 meta rig system and Pymel API as part of the core development process

Red9 comes with many development API to traversing networks, getting control nodes easily and initialising objects after you open scene.
In addition to this this makes PKD tools compatible  with the tools that comes with Red9 such as a well defined pose libary and mirroring system.

PyMel which is natively supported also comes with powerful and developer friendly API such as their easy way to make connections and OpenMaya based functionality.

However using these do come at the cost of speed however in the long run it will payoff for easier development process

The PKD tools also officially compatible with the ZV Parent Master tool which is a very refined and production tested constraint management system.

Just a small note with regards to naming convention, while other aspects of the PKD_Tools tries to keep to the Pep8 convention however in the rigging
part of the tool we use camelCase for all variable, properties and function to conform to naming standards in maya, pyside, Red9 and pymel
"""

# TODO: Try to create more meta subsystem eg for the spine, so that it is easier to navigate eg subCtrlSystem or hipSystem
# TODO: Implement using format instead of % operate for string

from collections import OrderedDict
import pymel.core as pm
from PKD_Tools import libUtilities
from PKD_Tools.Red9 import Red9_Meta
from PKD_Tools.Rigging import utils

if __name__ == '__main__':
    for module in Red9_Meta, utils, libUtilities:
        reload(module)


def _fullSide_(side):
    """
    Internal function to return the side based on the string short name
    @param side(string) The short name
    @return: The full form based on the input
    """
    side = side.upper()
    sideDict = {"L": "Left",
                "R": "Right",
                "C": "Centre"
                }
    if side not in sideDict.keys():
        raise RuntimeError("This is not supported short name for a side side: {0}".format(side))
    return sideDict[side]


_SUBCOMPONENTS_ = ["FK", "IK", "DYN"]


def forcePyNode(node):
    """Ensure to return a pynode. Critical for pynode based operation
    @param node (pynode, metaRig, string) The node that is being evaluated
    """
    # Check that the current node is not a pynode
    if not isinstance(node, pm.PyNode):
        # Is it s MetaRig
        if isinstance(node, Red9_Meta.MetaClass):
            node = pm.PyNode(node.mNode)
        else:
            # Convert the string to pynode
            try:
                node = pm.PyNode(node)
            except:
                print type(node)
                raise Exception("Failed to Convert {0}".format(node))

    return node


class MetaEnhanced(object):
    """This is a helper class which adds pynode based functionality and support. It is always used in conjunction with
    a metaRig class and never by itself"""
    # @cond DOXYGEN_SHOULD_SKIP_THIS
    _pynode_ = None
    debugMode = False
    # @endcond

    # noinspection PyPropertyAccess,PyUnreachableCode
    # Helper function to help doxgyen register python property function as attributes
    def _doxygenHelper(self):
        """
         @property pynode
         @brief Return the pynode that is associated for the node
         @property primaryAxis
         @brief Return the rotate order as string instead of numeric value
         """
        raise RuntimeError("This function cannot be used")
        self.pynode = self.primaryAxis = None

    # noinspection PyUnresolvedReferences
    def resetName(self):
        """Reset the name of the node to how should be named. Hopefully this strips away all numeric suffix"""
        self.pynode.rename(self.trueName)

    @property
    def pynode(self):
        """Return the pynode that is associated for the node"""
        if self._pynode_ is None:
            self._pynode_ = pm.PyNode(self.mNode)
        return self._pynode_


    @property
    def primaryAxis(self):
        """Return the rotate order as string instead of numeric value"""
        if hasattr(self, "rotateOrder"):
            return self.pynode.rotateOrder.get(asString=True)


class MetaRig(Red9_Meta.MetaRig, MetaEnhanced):
    """
    @brief An modfied Red9 meta rig class
    @details This is overridden class from Red9 `MetaRig` object. This is a very critical component
    The MetaEnhanced is attached as parent class give access to pymel pased functionality
    """

    def __init__(self, *args, **kwargs):
        """
        There are two ways that this object is initialised.
        - Creation
        :This happens when the PKD tools is creating nodes for the various rigs. Here we always try to pass pass the side and part as key words arguements
        - Query
        :In this case Red9 is the one that initialising the class. Here we ensure that no new node are being creating

        @param args: Any arguements that is passed to the meta rig
        @param kwargs: Keyword arguements used by this function and by meta rig. If it finds
        a `side` and `part` keyword arguement then that means we are creating a PKD Rig component.
        Other optional keyword arguements are `endsuffix` and `nodetype`

        Both ways will pass on arguments to the Red9 `MetaRig`
        """
        # @cond DOXYGEN_SHOULD_SKIP_THIS

        if kwargs.has_key("side") and kwargs.has_key("part"):
            # Setup defaults
            kwargs["endSuffix"] = kwargs.get("endSuffix", "Grp")
            kwargs["nodeType"] = kwargs.get("nodeType", "transform")
            # Build the fullname
            full_name = utils.nameMe(kwargs["side"], kwargs["part"], kwargs["endSuffix"])
            # Build the red 9 meta rig with our name
            super(MetaRig, self).__init__(name=full_name, **kwargs)
            self.part = kwargs["part"]
            # Setup the mirror side
            self.mirrorSide = _fullSide_(kwargs["side"])
            # Set the rig type
            self.rigType = kwargs["endSuffix"]
            # Set this as non system root by default
            self.mSystemRoot = False
        else:
            super(MetaRig, self).__init__(*args, **kwargs)

        # For some reason we run lockState twice to register it
        # @cond DOXYGEN_SHOULD_SKIP_THIS
        self.lockState = False
        self.lockState = False

        # By default it is not sub component
        self.isSubComponent = False

        # An existing of systemType attribute means that this is a component
        if hasattr(self, "systemType"):
            if self.systemType in _SUBCOMPONENTS_:
                self.isSubComponent = True

        # Return connected as meta
        self.returnNodesAsMeta = True
        # @endcond

    # noinspection PyPropertyAccess
    def _doxygenHelper(self):
        """
        @property part
        @brief The descriptor of the component are we making eg neck, hand etc. This usually comes from the joint name
        @property mirrorSide
        @brief Which side does this component fall on
        @property rigType
        @brief What type of component are we making
        @property isSubComponent
        @brief When this component is subset of another rig syster, eg fk, ik, helper etc
        @property returnNodesAsMeta
        @brief This ensures that when we use Red9 higher level function we return them as meta
        @property systemType
        @brief What type of sub system is this, eg fk, ik etc
        @property trueName
        @brief Return the name based on attributes in the meta rig. ThiS is used to rename duplicate node or in case it was
        renamed incorrectly
        @property side
        @brief Return the current mirror side as string
        """
        super(MetaRig, self)._doxygenHelper()
        self.trueName = self.side = self.part = self.mirrorSide = self.rigType = \
            self.isSubComponent = self.returnNodesAsMeta = self.systemType = None

    def __bindData__(self, *args, **kwgs):
        """Overwrite the bind data so that we can add our own custom attributes"""
        # ensure these are added by default
        if not hasattr(self, "mClass"):
            # Need to add this otherwise the maya wrapped node do not get returned
            self.addAttr("mClass", self.__class__.__name__)
            self.pynode.mClass.lock(True)
        self.addAttr("part", "")
        self.addAttr('mirrorSide', enumName='Centre:Left:Right',
                     attrType='enum', hidden=True)
        self.addAttr('rigType', '')

    def addMetaSubSystem(self, subSystem, system="FK", **kwargs):
        """Override red 9 add function """
        if isinstance(subSystem, MovableSystem):
            # Parent the group
            subSystem.setParent(self)
        # Connect it as a child
        self.connectChild(subSystem, '{0}_System'.format(system))
        subSystem.systemType = system

    def getMetaSubSystem(self, system="FK"):
        """Return a subsystem type"""
        return (self.getChildren(walk=True,
                                 asMeta=self.returnNodesAsMeta,
                                 cAttrs=['{0}_System'.format(system)])
                or [""])[0]

    def convertToComponent(self, component="FK"):
        """
        Convert this system to a sub component.
        @param component (string) Type of subcomponent
        """
        # Add a new attr
        if not hasattr(self, "systemType"):
            self.addAttr("systemType", component)
        else:
            self.systemType = component

        hasConverted = True
        if not self.isSubComponent:
            self.isSubComponent = True
            hasConverted = False
        try:
            if not hasConverted:
                self.resetName()
                # @cond DOXYGEN_SHOULD_SKIP_THIS
                self.mNodeID = self.trueName
                # @endcond
            else:
                # Node is already converted into a subcomponent
                return
        except Exception as e:
            libUtilities.pyLog.info(str(e))
            libUtilities.pyLog.info("Rename failed on:{0}".format(self.mNode))
            self.select()
            raise RuntimeError("Rename Failed")

        libUtilities.strip_integer(self.pynode)

    def getRigCtrl(self, target):
        """
        Get the specific type of rig ctrl
        @param target (string) The type of control that is being retrieved
        @return: The meta rig
        """
        children = self.getChildren(walk=True, asMeta=self.returnNodesAsMeta,
                                    cAttrs=["%s_%s" % (self.CTRL_Prefix, target)])
        if not children:
            libUtilities.pyLog.warn("%s ctrl not found on %s" % (target, self.shortName()))
        else:
            return children[0]

    def addRigCtrl(self, target, *args, **kwargs):
        """
        Add the rig control
        @param target (metaRig) The node that is being added as a control
        @param args Arguement list
        @param kwargs The keyword argument dictionary
        """
        try:
            # TODO: add ctrls to rig controls
            assert isinstance(target, Red9_Meta.MetaClass)
            super(MetaRig, self).addRigCtrl(target.mNode, *args, **kwargs)
        except:
            raise AssertionError("Input must be MetaClass")

    def getSupportNode(self, target):
        """
        Return the type of support node that is connected to the rig system
        @param target (string) The type of support node that is being queried
        """
        children = self.getChildren(walk=True, asMeta=self.returnNodesAsMeta, cAttrs=["SUP_%s" % target])
        if not children:
            if self.debugMode:
                libUtilities.pyLog.warn("%s not support node found on %s" % (target, self.shortName()))
        else:
            if type(children[0]) == Red9_Meta.MetaClass:
                children[0] = MetaRig(children[0].mNode)

            return children[0]

    def addSupportNode(self, node, attr, boundData=None):
        """
        Add support node to the system
        @param node (metaRig, pynode, string) The node that is being
        @param attr (string) The type of support node
        @param boundData (dict) Any data that is used by the metaRig superclass
        """
        if hasattr(node, "mNode"):
            supportNode = node.mNode
        elif isinstance(node, pm.PyNode):
            supportNode = node.name()
        else:
            supportNode = node
        super(MetaRig, self).addSupportNode(supportNode, attr, boundData=boundData)
        # Test that the connection has been made

    def transferPropertiesToChild(self, childMeta, childType):
        """
        Copy essential attributes to a child meta node.
        This is usually when we convert a already existing node to a metaRig
        @param childMeta (metaRig) The child meta rig
        @param childType (string) Set a type of the meta
        """
        try:
            # TODO: add ctrls to rig controls
            assert isinstance(childMeta, Red9_Meta.MetaClass)
        except:
            raise AssertionError("ChildMeta must be MetaClass: %s. Type is %s" % (childMeta, type(childMeta)))
        childMeta.mirrorSide = self.mirrorSide
        childMeta.rigType = childType

    def convertSystemToSubSystem(self, component="FK"):
        """
        Convert a whole meta sytem to subsystem
        @param component (string) The type of component you are trying to convert tp
        """
        # Rename the component the child component
        for obj in [self] + self.getChildMetaNodes(walk=True):
            obj.convertToComponent(component)

    # @cond DOXYGEN_SHOULD_SKIP_THIS
    @property
    def trueName(self):
        # TODO: Adjust for subsystem type name
        if type(self.side) == int:
            side = self.pynode.mirrorSide.get(asString=True)[0]
        else:
            side = self.side

        if not (side and self.part and self.rigType):
            print "Side: {0}".format(side)
            print "Part: {0}".format(self.part)
            print "RigType: {0}".format(self.rigType)
            raise ValueError("One of the attribute are not defined. Cannot get true name")
        part = self.part
        if self.isSubComponent:
            part = "{0}_{1}".format(self.part, self.systemType)
        return utils.nameMe(side, part, self.rigType)

    @property
    def side(self):
        """Return the current mirror side as string"""
        return self.pynode.mirrorSide.get(asString=True)[0]
    # @endcond


class ConstraintSystem(MetaRig):
    """A constraint meta rig"""

    def _doxygenHelper(self):
        """
        @property weightAliasInfo
        @brief Contain information about what is weight alias for given constraint weight. This will be handy to produce
        dynamic space switch option where we will get the information about the name from this property
        """
        super(ConstraintSystem, self)._doxygenHelper()
        self.weightAliasInfo = None

    # @cond DOXYGEN_SHOULD_SKIP_THIS
    @property
    def weightAliasInfo(self):
        return OrderedDict(self._weightAliasInfo)

    @weightAliasInfo.setter
    def weightAliasInfo(self, newWeightAlias):
        # noinspection PyTypeChecker
        if not isinstance(newWeightAlias, basestring):
            raise AttributeError("New weight alias has be a string")
        newWeightAlias = newWeightAlias.lower()
        if not self.pynode.hasAttr("_weightAliasInfo"):
            self.addAttr("_weightAliasInfo", [(newWeightAlias, "w0")])
        else:
            weightAliasInfo = self.weightAliasInfo
            weightAliasInfo[newWeightAlias] = "w{0}".format(len(weightAliasInfo))
            # noinspection PyAttributeOutsideInit
            self._weightAliasInfo = weightAliasInfo.items()

    # @endcond

class MovableSystem(MetaRig):
    """
    This is a system which can be moved. Usually a joint or transform node
    """

    # noinspection PyPropertyAccess
    def _doxygenHelper(self):
        """
        @property constrainedNode
        @brief By default the movable node is the one that will be constrained
        @property orientConstraint
        @brief Get orient constraint metaclass
        @property pointConstraint
        @brief Get the point constraint metaclass
        @property aimConstraint
        @brief Get the aim constraint metaclass
        @property scaleConstraint
        @brief Get the scale constraint metaclass
        @property parentConstraint
        @brief Get the parent constraint metaclass
        @property poleVectorConstraint
        @brief Get the pole vector constraint metaclass
        @property prnt
        @brief Get the parent node
        """
        super(MovableSystem, self)._doxygenHelper()
        self.constrainedNode = self.orientConstraint = self.pointConstraint = self.aimConstraint = \
            self.parentConstraint = self.scaleConstraint = self.poleVectorConstraint = self.prnt = None

    def setParent(self, targetSystem):
        """
        Parent the rig system to another target system. By default if has parent we would parent that first other wise
        We will try to parent the transform
        @param targetSystem (metaRig) The target system you are trying to parent
        """
        targetNode = forcePyNode(targetSystem)
        # Does it has parent. Then we we reparent that
        if self.prnt:
            self.prnt.pynode.setParent(targetNode)
        elif self.pynode.type() in ["transform", "joint"]:
            self.pynode.setParent(targetNode)
        else:
            libUtilities.pyLog.error("{0} is not a transform/joint node. Unable to parent".format(self.pynode))

    def addParent(self, **kwargs):
        """Add parent node for the transform node"""
        snap = kwargs.get("snap", True)
        endSuffix = kwargs.get("endSuffix", "Prnt")
        if not (self.part and self.side):
            raise ValueError("Part or Side is not defined: %s" % self.shortName())
        self.prnt = MovableSystem(part=self.part, side=self.side, endSuffix=endSuffix)
        if snap:
            libUtilities.snap(self.prnt.pynode, self.pynode)
        self.pynode.setParent(self.prnt.pynode)

    def addConstraint(self, target, conType="parent", **kwargs):
        """
        Add constaint to the movable node and attach as support node
        @param target (metaRig/pynode) The node that will contraint this metaRig
        @param conType (string) The constraint type eg rotate, parent, point etc
        @param kwargs (dict) Any keywords arguments to pass on the default maya function
        @return: name of the constraint node
        """
        if kwargs.has_key("maintainOffset"):
            kwargs["mo"] = kwargs["maintainOffset"]
            del kwargs["maintainOffset"]
        else:
            kwargs["mo"] = kwargs.get("mo", True)

        # Ensure that we are dealing with a pynode
        target = forcePyNode(target)

        # Debug statement
        if self.debugMode:
            libUtilities.pyLog.warning("%sConstrainting %s to %s. Maintain offset is %s "
                                       % (conType, self.constrainedNode, target, kwargs["mo"]))

        # Get the constraint function from the library
        consFunc = getattr(pm, "%sConstraint" % conType)

        # Check the constraint type
        if self.constrainedNode.nodeType() not in ["transform", "joint"]:
            libUtilities.pyLog.error(
                "%s is not a transform/joint node. Unable to add constraint" % self.constrainedNode)

        # Delete the weightAlias keywords from the kwargs list before passing it to Maya
        weightAlias = kwargs.get("weightAlias")
        if weightAlias:
            del kwargs["weightAlias"]

        # Set the constraint
        constraintNodeName = consFunc(target, self.constrainedNode, **kwargs).name()
        supportNodeType = "%sConstraint" % conType.title()
        if not eval("self.%sConstraint" % conType):
            constraintMeta = ConstraintSystem(constraintNodeName)
            constraintMeta.rigType = "{0}{1}Con".format(self.rigType, libUtilities.capitalize(conType))
            constraintMeta.mirrorSide = self.mirrorSide
            constraintMeta.part = self.part
            self.addSupportNode(constraintMeta, supportNodeType)

        # Store information about multi targeted weights
        if weightAlias:
            constraintMeta = self.getSupportNode(supportNodeType)
            constraintMeta.weightAliasInfo = weightAlias
        return constraintNodeName

    def snap(self, target, rotate=True):
        """
        Match the position of the system to the target node
        @param target (pynode/string) Self descriptive
        @param rotate (bool) Whether to match rotation
        """
        # Check that we are only applying to joint/transform
        if all(pm.objectType(node) in ["transform", "joint"] for node in [self.pynode, target]):
            if self.prnt:
                libUtilities.snap(self.prnt.pynode, target, rotate=rotate)
            else:
                libUtilities.snap(self.pynode, target, rotate=rotate)

    # @cond DOXYGEN_SHOULD_SKIP_THIS
    @property
    def constrainedNode(self):
        return self.pynode

    @property
    def orientConstraint(self):
        return self.getSupportNode("OrientConstraint")

    @property
    def pointConstraint(self):
        return self.getSupportNode("PointConstraint")

    @property
    def aimConstraint(self):
        return self.getSupportNode("AimConstraint")

    @property
    def scaleConstraint(self):
        return self.getSupportNode("ScaleConstraint")

    @property
    def parentConstraint(self):
        return self.getSupportNode("ParentConstraint")

    @property
    def poleVectorConstraint(self):
        return self.getSupportNode("PoleVectorConstraint")

    @property
    def prnt(self):
        return self.getSupportNode("Prnt")

    @prnt.setter
    def prnt(self, data):
        """
        Set the parent node
        @param data (metaRig) The parent meta class
        """
        self.addSupportNode(data, "Prnt")
    # @endcond


class TransSubSystem(MovableSystem):
    """This is a MovableSystem which can be converted to a subcomponent. Artist will not interact with this node."""

    def __bindData__(self, *args, **kwgs):
        """Ensure to add a systemType attribute is added"""
        super(TransSubSystem, self).__bindData__(*args, **kwgs)
        self.addAttr('systemType', "")


class Network(MetaRig):
    """@brief This is a MetaRig that doesn't create a transform node.
    @details Used for organising nodes and creating subsystem"""

    def __init__(self, *args, **kwargs):
        kwargs["nodeType"] = "network"
        kwargs["endSuffix"] = "Sys"
        super(Network, self).__init__(*args, **kwargs)


class NetSubSystem(Network):
    """An extended class of Network class where it is always going to be part of sub system, therefore it will
    always add 'systemType' attr to the node eg Cartoony system"""

    def __bindData__(self, *args, **kwgs):
        """Ensure to add a systemType attribute is added"""
        super(NetSubSystem, self).__bindData__(*args, **kwgs)
        self.addAttr('systemType', "")


class Joint(MovableSystem):
    """
    This meta class which creates a joint by default.
    """

    def __init__(self, *args, **kwargs):
        """Override the init to always create joint"""
        kwargs["nodeType"] = "joint"
        kwargs["endSuffix"] = kwargs.get("endSuffix", "Joint")
        super(Joint, self).__init__(*args, **kwargs)
        self.pynode.side.set(self.pynode.mirrorSide.get())

    def setParent(self, targetSystem):
        """
        In case the target system is a joint then ensure their inverse scale are hooked up
        @param targetSystem (metaRig) The target system you are trying to parent to
        """
        targetNode = forcePyNode(targetSystem)
        super(Joint, self).setParent(targetNode)
        # Check the node type is joint
        if targetNode.nodeType() == "joint":
            connections = self.pynode.inverseScale.listConnections(plugs=True)
            inverseTarget = connections[0] if connections else None
            if inverseTarget != targetNode.scale:
                targetNode.scale >> self.pynode.inverseScale


class JointSystem(Network):
    """Network class which deals with a collection of joint.

    TODO: it might be more useful to make the JointSystem aware to ignore the last joint instead of making the other systems
    take care of that. Perhaps they can pass on this information to the joint system so that it prunes the last joint information
    when something queries it. It need be it can always be switched to
   """

    # @cond DOXYGEN_SHOULD_SKIP_THIS
    def __init__(self, *args, **kwargs):
        """
        Joint system initializer
        @param args Any arguements to be passed to the parent
        @param kwargs Any keyword arguements to be passed to the parent

        """
        super(JointSystem, self).__init__(*args, **kwargs)
        self.jointData = None

    def __len__(self):
        return len(self.joints)

    def __bindData__(self, *args, **kwgs):
        """Here we are adding a joint attribute which contains the necessary information to construct a joint chain"""
        super(JointSystem, self).__bindData__()
        # ensure these are added by default
        self.addAttr("jointData", "")

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

    def build(self):
        """Build the joints based on data from the @ref jointData joint data"""
        # TODO: When building a mirrored joint. Remove the mirror key and mirror type
        # Iterate though all the joint list
        if self.jointData:
            # Init the metaJoint list
            metaJoints = []
            for i, joint in enumerate(self.jointData):
                # Build a joint based on the name
                metaJoint = Joint(side=self.side, part=joint["Name"])
                # Set the position and joint orientation
                metaJoint.pynode.setTranslation(joint["Position"], space="world")
                metaJoint.pynode.jointOrient.set(joint["JointOrient"])
                for attr in ["jointOrientX", "jointOrientY", "jointOrientZ"]:
                    metaJoint.pynode.attr(attr).setKeyable(True)
                metaJoints.append(metaJoint)
                if i:
                    metaJoint.pynode.setParent(metaJoints[i - 1].mNode)
            # Set the meta joints as the main joints
            self.joints = metaJoints
        else:
            libUtilities.pyLog.error("No Joint Data Specified")

    def convertJointsToMetaJoints(self):
        """Convert an existing joint chain into a meta joint."""
        # Build the joint data map
        jointData = []
        # Create the temporary pyjoint to retrieve joint orient value
        pyJoints = []
        # Iterate through the existing joints
        for joint in self.joints:
            # Move the joint in world space
            joint = forcePyNode(joint)
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
            newJoint = pm.joint()
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
            # New joint system option
            replicateJointSystem = JointSystem(*args, **kwargs)
            # Here we have a customised joint system where it acts as a support system
            if kwargs.has_key("supportType"):
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
                for jointInfo in joint_data:
                    jointInfo["Name"] = jointInfo["Name"] + kwargs["supportType"]
                # Set the joint data
                replicateJointSystem.jointData = joint_data
            else:
                # Copy the data across
                replicateJointSystem.jointData = self.jointData

            # Set the rotate order
            replicateJointSystem.setRotateOrder(self.joints[0].rotateOrder)

            # Build the joints
            if kwargs.get("build", True):
                replicateJointSystem.build()

            # Return the joint system
            return replicateJointSystem
        else:
            libUtilities.pyLog.error("Unable to replicate as there is no existing joint data")

    # @cond DOXYGEN_SHOULD_SKIP_THIS
    @property
    def joints(self):
        return self.getChildren(asMeta=self.returnNodesAsMeta, walk=True, cAttrs=["SUP_Joints"])

    @joints.setter
    def joints(self, jointList):
        jointList = [joint.shortName() for joint in jointList]
        self.connectChildren(jointList, "SUP_Joints", allowIncest=True, cleanCurrent=True)

    @property
    def jointList(self):
        return [joint.shortName() for joint in self.joints]

    @property
    def positions(self):
        positionList = []
        if self.jointData:
            for joint in self.jointData:
                positionList.append(joint["Position"])
        else:
            libUtilities.pyLog.error("No joint data found")
        return positionList
    # @endcond


class SpaceLocator(MovableSystem):
    """
    Space locator meta. Allow to create fast cluster
    """

    # @cond DOXYGEN_SHOULD_SKIP_THIS
    def __init__(self, *args, **kwargs):
        super(SpaceLocator, self).__init__(*args, **kwargs)
        # Is it being called by an PKD rig node
        if not self.pynode.getShape():
            # Create a new temp locator
            tempLoc = pm.spaceLocator()
            # Tranfer the locator shape to the main node
            libUtilities.transfer_shape(tempLoc, self.mNode)
            # Rename the shape node
            libUtilities.fix_shape_name(self.pynode)
            # Delete the temp loc
            pm.delete(tempLoc)
    # @endcond

    def clusterCV(self, cv):
        """
        Cluster a CV without using a cluster deformer. More faster
        @param cv (pynode/string): The cv that is being clustered
        """
        cv = forcePyNode(cv)
        self.snap(cv.name(), rotate=False)
        libUtilities.cheap_point_constraint(self.pynode, cv)


class Ctrl(MovableSystem):
    """The meta rig for a control system.
    @details A typical control will have the following setup
    <ul>
    <li>Prnt = The main parent control</li>
        <li>Xtra = An extra transform where the animator can push contraints or set driven keys<l/i>
            <li>Ctrl - The actual control that is exposed to the animator<l/i>
                <li>Gimbal - An extra controller to take handle gimbal lock issues</li>
    </ul>
    Depending on the rig requirement some controls may also have an additional ZV parent master setup to work with the
    tool. It might be ideal to disable the extra transform for a lighter hierarchy
    """

    # @cond DOXYGEN_SHOULD_SKIP_THIS
    def __init__(self, *args, **kwargs):
        kwargs["endSuffix"] = "Ctrl"
        super(Ctrl, self).__init__(*args, **kwargs)
        self.createXtra = kwargs.get("createXtra", True)
        # Define the control shape
        self.ctrlShape = kwargs.get("shape", "Ball")
        # Whether this is parent master system
        self.hasParentMaster = kwargs.get("parentMaster", False)
        # Set the mirror data
        self.mirrorData = {'side': self.mirrorSide, 'slot': 1}
        # @endcond

    # noinspection PyPropertyAccess
    def _doxygenHelper(self):
        """
        @property constrainedNode
        @brief User defined folder where the weight and data file are saved
        @property createdNodes
        @brief Get the list of nodes that are already created
        @property constrainedNode
        @brief Get the list of all created transform meta nodes.
        @property parentDriver
        @brief Return the gimbal node or the control
        @property xtra
        @brief The node right above the control. Useful for doing things like set driven keys or alternative constraint setup
        @property prnt
        @brief The top most node in the hierarchy. This what get the constraint
        @property gimbal
        @brief The node right underneath the control. This allows us to take of rotation where it
        @property hasGimbal
        @brief Convenience bool function to see if there is a gimbal node.
        @property pivot
        @brief Allow to change the pivot of the control. This is parented underneath the control.
        sed mostly in a foot setup
        @property hasPivot
        @brief Convenience bool function to see if there is a pivot node
        @property locator
        @brief A locator that is connected to this control
        @property parentMasterSN
        @brief Node for the parent master setup
        @property parentMasterPH
        @brief Node for the parent master setup
        @property createXtra
        @brief Whether to create a extra node in between the parent and ctrl
        @property ctrlShape
        @brief Defines the shape of the control. Default is ball control
        @property hasParentMaster
        @brief Determine if this control has a parent master setup. Default is `False`
        @property mirrorData
        @brief Use the mirror data as used by Red9 mirror tool
        """
        super(Ctrl, self)._doxygenHelper()
        self.constrainedNode = self.hasPivot = self.createdNodes = self.parentDriver = self.hasGimbal = self.pivot = \
            self.hasPivot = self.locator = self.parentMasterPH = self.parentMasterSN = self.xtra = self.prnt = \
            self.gimbal = self.hasParentMaster = self.mirrorData = self.ctrlShape = self.createXtra = None

    def build(self):
        """The core command that creates the control based on the parameter defined in the init"""
        # Create the xtra grp
        if self.createXtra:
            self.xtra = MovableSystem(part=self.part, side=self.side, endSuffix="Xtra")
        # Create the Parent
        self.prnt = MovableSystem(part=self.part, side=self.side, endSuffix="Prnt")
        tempCtrlShape = utils.buildCtrlShape(self.ctrlShape)
        libUtilities.transfer_shape(tempCtrlShape, self.mNode)
        libUtilities.fix_shape_name(self.pynode)
        pm.delete(tempCtrlShape)
        if self.createXtra:
            # Parent the ctrl to the xtra
            self.pynode.setParent(self.xtra.mNode)
            # Parent the xtra to prnt
            self.xtra.pynode.setParent(self.prnt.mNode)
        else:
            # Parent the ctrl to prnt
            self.pynode.setParent(self.prnt.mNode)
        # Transform Nodes
        node = [self.pynode, self.prnt.pynode]
        if self.createXtra:
            node.append(self.xtra.pynode)
        # lock and hide the visibility attributes
        for item in [self, self.xtra, self.prnt]:
            if item:
                node = item.pynode
                libUtilities.set_lock_status(node, {"v": True})
                node.v.showInChannelBox(True)
                node.v.showInChannelBox(False)

        # Limit the scale to 0.01. Zero is never any animaton scenario
        pm.transformLimits(self.pynode, sx=(0.01, 1), esx=(1, 0))
        pm.transformLimits(self.pynode, sy=(0.01, 1), esy=(1, 0))
        pm.transformLimits(self.pynode, sz=(0.01, 1), esz=(1, 0))

    def addParentMaster(self):
        """Creating the necessary parent master setup to work with ZV parent master"""
        # Create the parent master group if need be
        self.parentMasterSN = MovableSystem(name="%s_SN" % self.trueName, nodeType="transform")
        self.parentMasterSN.rigType = "SN"
        self.parentMasterPH = MovableSystem(name="%s_PH" % self.trueName, nodeType="transform")
        self.parentMasterPH.rigType = "PH"
        # Setup the parenting
        self.pynode.setParent(self.parentMasterSN.mNode)
        self.parentMasterSN.pynode.setParent(self.parentMasterPH.mNode)
        self.parentMasterPH.pynode.setParent(self.xtra.mNode)
        # set the parts
        self.parentMasterSN.part = self.part
        self.parentMasterPH.part = self.part

    def addGimbalMode(self):
        """Add a extra gimbal controller under the main ctrl."""
        self.gimbal = MovableSystem(name=utils.nameMe(self.side, self.part, "Gimbal"), nodeType="transform")
        self.gimbal.part = self.part
        self.gimbal.rigType = "gimbalHelper"
        self.gimbal.pynode.setParent(self.mNode)
        # Set the shape
        tempCtrlShape = utils.buildCtrlShape("Spike")
        libUtilities.transfer_shape(tempCtrlShape, self.gimbal.pynode)
        libUtilities.fix_shape_name(self.gimbal.pynode)
        pm.delete(tempCtrlShape)
        # Add Attribute control the visibility
        self.addDivAttr("Show", "gimbVis")
        self.addBoolAttr("Gimbal")
        self.pynode.Gimbal >> self.gimbal.pynode.getShape().visibility

    def addSpaceLocator(self, parent=False):
        """Add a space locator that is attached with this control"""
        # spaceLocator -p 0 0 0;
        self.locator = SpaceLocator(side=self.side, part=self.part, endSuffix="Loc")
        if parent:
            if self.hasGimbal:
                self.locator.pynode.setParent(self.gimbal.pynode)
            else:
                self.locator.pynode.setParent(self.pynode)

    def addPivot(self):
        """Add animatable pivot to a control. Most useful in a @ref limb.Foot setup"""
        # @cond DOXYGEN_SHOULD_SKIP_THIS
        self.pivot = MovableSystem(name=utils.nameMe(self.side, self.part, "Pivot"), nodeType="transform")
        self.pivot.part = self.part
        self.pivot.rigType = "pivot"
        self.pivot.pynode.setParent(self.mNode)
        # Set the shape
        tempCtrlShape = utils.buildCtrlShape("Locator")
        libUtilities.transfer_shape(tempCtrlShape, self.pivot.pynode)
        libUtilities.fix_shape_name(self.pivot.pynode)
        pm.delete(tempCtrlShape)
        # Snap ctrl
        libUtilities.snap(self.pivot.mNode, self.mNode)

        self.pivot.pynode.setParent(self.mNode)

        self.pivot.pynode.translate >> self.pynode.rotatePivot
        self.pivot.pynode.translate >> self.pynode.scalePivot

        # Add Attribute control the visibility
        self.addDivAttr("Show", "pivotVis")
        self.addBoolAttr("Pivot")
        self.pynode.Pivot >> self.pivot.pynode.v
        # @endcond

    def addChild(self, targetNode):
        """In case we have gimbal we will add children to that other we will add to the ctrl itself"""
        targetNode = forcePyNode(targetNode)
        # TODO: Investigate why it does not work in certain scenarios
        if self.hasGimbal:
            pm.parent(targetNode, self.gimbal.mNode)
        else:
            pm.parent(targetNode, self.mNode)

    def setParent(self, targetSystem):
        """Overwritten function to ensure that the @ref prnt is always parented instead of the control node itself"""
        self.prnt.setParent(targetSystem)

    def setRotateOrder(self, rotateOrder):
        """Set the rotate order of the various controls"""
        for node in self.createdNodes:
            node.rotateOrder = rotateOrder

    def addDivAttr(self, label, ln):
        """Add a divider label"""
        libUtilities.addDivAttr(self.mNode, label=label, ln=ln)

    def addBoolAttr(self, label, sn=""):
        """Add a boolean atrbiture"""
        libUtilities.addBoolAttr(self.mNode, label=label, sn=sn)

    def addFloatAttr(self, attrName="", attrMax=1, attrMin=0, SV=0, sn="", df=0):
        """
        Add a float attribute. Same arguments as @ref libUtilities.addFloatAttr "addFloatAttr"
        """
        libUtilities.addFloatAttr(self.mNode, attrName=attrName, attrMax=attrMax, attrMin=attrMin, softValue=SV,
                                  shortName=sn, defaultValue=df)

    def lockTranslate(self):
        """Lock all the translate channels"""
        for item in self.createdNodes:
            libUtilities.lock_translate(item.pynode)

    def lockRotate(self):
        """Lock all the rotate channels"""
        for item in self.createdNodes:
            libUtilities.lock_rotate(item.pynode)

    def lockScale(self):
        """Lock all the scale channels"""
        for item in self.createdNodes:
            libUtilities.lock_scale(item.pynode)

    def _createRotateDriver_(self):
        """Internal function to create a rotate driver"""
        pmaMeta = MetaRig(side=self.side,
                          part=self.part,
                          endSuffix="RotateDriver",
                          nodeType="plusMinusAverage")

        pmaMeta.addAttr("connectedAxis", {"X": False, "Y": False, "Z": False})
        self.addSupportNode(pmaMeta, "RotateDriver")
        return pmaMeta

    def _connectAxisRotateDriver_(self, axis):
        """Internal function to connect rotate driver"""
        pmaMeta = self.getSupportNode("RotateDriver")
        if not pmaMeta:
            pmaMeta = self._createRotateDriver_()

        # Is the rotate axis connected
        rotateStatus = pmaMeta.connectedAxis
        if not rotateStatus[axis.upper()]:
            # Connect the rotate axis to PMA
            nodes = [self.pynode]
            if self.hasGimbal:
                nodes.append(self.gimbal.pynode)

            for i, node in zip(range(len(nodes)), nodes):
                node.attr("rotate%s" % axis.upper()) >> pmaMeta.pynode.input3D[i].attr("input3D%s" % axis.lower())

            # Set the rotate axis
            rotateStatus[axis.upper()] = True
            pmaMeta.connectedAxis = rotateStatus
        return pmaMeta

    def getRotateDriver(self, axis):
        """
        A rotate driver is where instead of using direct connections we use plus minus average
        This will allows us to add rotation value from gimbal node and the control
        @param axis (string) Which XYZ axis that is being driven
        @return Pynode attribute that needs to be connected
        """
        if self.hasGimbal:
            pmaMeta = self._connectAxisRotateDriver_(axis)
            if axis == "X":
                return pmaMeta.pynode.output3Dx
            elif axis == "Y":
                return pmaMeta.pynode.output3Dy
            else:
                return pmaMeta.pynode.output3Dz
        else:
            self.pynode.attr("rotate{0}".format(axis))

    # @cond DOXYGEN_SHOULD_SKIP_THIS
    @property
    def createdNodes(self):
        metaNodes = [self, self.prnt]
        if self.xtra:
            metaNodes.append(self.xtra)
        if self.hasGimbal:
            metaNodes.append(self.gimbal)
        if self.hasParentMaster:
            metaNodes += [self.parentMasterPH, self.parentMasterSN]
        return metaNodes

    @property
    def constrainedNode(self):
        return self.prnt.pynode

    @property
    def parentDriver(self):
        # Is the driver going to be the gimbal or the control itself. Useful for skinning, correct constraint target
        if self.hasGimbal:
            return self.gimbal
        else:
            return self

    @property
    def xtra(self):
        return self.getSupportNode("Xtra")

    @xtra.setter
    def xtra(self, data):
        self.addSupportNode(data, "Xtra")

    @property
    def gimbal(self):
        return self.getSupportNode("Gimbal")

    @gimbal.setter
    def gimbal(self, data):
        self.addSupportNode(data, "Gimbal")

    @property
    def hasGimbal(self):
        return self.gimbal is not None

    @property
    def pivot(self):
        data = self.getSupportNode("Pivot")
        return data

    @pivot.setter
    def pivot(self, data):
        self.addSupportNode(data, "Pivot")

    @property
    def hasPivot(self):
        return self.getSupportNode("Pivot") is not None

    @property
    def locator(self):
        data = self.getSupportNode("Locator")
        return data

    @locator.setter
    def locator(self, data):
        self.addSupportNode(data, "Locator")

    @property
    def hasLocator(self):
        return self.getSupportNode("Locator") is not None

    @property
    def parentMasterPH(self):
        data = self.getSupportNode("ParentMasterPH")
        if data is not None:
            self.hasParentMaster = True
        return data

    @parentMasterPH.setter
    def parentMasterPH(self, data):
        # TODO: Pass the slot number before and axis data
        self.addSupportNode(data, "ParentMasterPH")
        if data is not None:
            self.hasParentMaster = True

    @property
    def parentMasterSN(self):
        return self.getSupportNode("ParentMasterSN")

    @parentMasterSN.setter
    def parentMasterSN(self, data):
        # TODO: Pass the slot number before and axis data
        self.addSupportNode(data, "ParentMasterSN")


class Anno_Loc(SpaceLocator):
    """This is a a annoated locator"""
    pass


class MyCameraMeta(Red9_Meta.MetaClass, MetaEnhanced):
    """
    Example showing that metaData isn't limited to 'network' nodes,
    by using the 'nodeType' arg in the class __init__ you can modify
    the general behaviour such that meta creates any type of Maya node.
    '''
    def __init__(self,*args,**kwargs):
        super(MyCameraMeta, self).__init__(nodeType='camera',*args,**kwargs)
        self.item = None
    """

    def __init__(self, *args, **kwargs):
        super(MyCameraMeta, self).__init__(nodeType='camera', *args, **kwargs)
        # @endcond


class CartoonySystem(Network):
    """@brief A setup which simulates the squash and stretch effect through joints
    @details The effect that can be driven by the scale value on the joints
    It needs a trigger attribute whose value can range from 0.001 to infinity. This can come from a joint or length value

    TODO: Document the property
    """

    def __init__(self, *args, **kwargs):
        super(CartoonySystem, self).__init__(*args, **kwargs)

    # @cond DOXYGEN_SHOULD_SKIP_THIS
    def build(self):
        supportNodes = {}
        # Disable condition
        cond = MetaRig(part=self.part, side=self.side, endSuffix="DisableCondition", nodeType="condition")
        cond.colorIfTrue = [1, 1, 0]
        cond.colorIfFalse = [-50000000, 50000000, 1]
        cond.secondTerm = 1
        supportNodes["DisableCondition"] = cond

        # Disable Clamp
        disableClamp = MetaRig(part=self.part, side=self.side, endSuffix="DisableClamp", nodeType="clamp")
        supportNodes["DisableClamp"] = disableClamp

        # Elasticity remainder
        elasticityRemainder = MetaRig(part=self.part, side=self.side, endSuffix="ElasticityRemainder",
                                      nodeType="addDoubleLinear")
        # self.elasticityRemainder = elasRemADD
        elasticityRemainder.input2 = -1
        supportNodes["ElasticityRemainder"] = elasticityRemainder

        # Elasticity Mulitiplier
        elasticityMulitplier = MetaRig(part=self.part, side=self.side, endSuffix="ElastictyMultiplier",
                                       nodeType="multiplyDivide")
        elasticityMulitplier.input2X = -10
        supportNodes["ElastictyMultiplier"] = elasticityMulitplier

        # Pos Clamp
        positiveClamp = MetaRig(part=self.part, side=self.side, endSuffix="PositiveClamp", nodeType="clamp")
        supportNodes["PositiveClamp"] = positiveClamp

        # Neg Clamp
        negativeClamp = MetaRig(part=self.part, side=self.side, endSuffix="NegativeClamp", nodeType="clamp")
        supportNodes["NegativeClamp"] = negativeClamp

        # Trigger condition
        triggerCondition = MetaRig(part=self.part, side=self.side, endSuffix="TriggerCondition", nodeType="condition")
        triggerCondition.operation = 3
        triggerCondition.secondTerm = 1
        supportNodes["TriggerCondition"] = triggerCondition

        # Elasticity Adder
        finalElasticity = MetaRig(part=self.part, side=self.side, endSuffix="FinalElasticityAdder",
                                  nodeType="addDoubleLinear")
        finalElasticity.input2 = 1
        supportNodes["FinalElasticityAdder"] = finalElasticity

        # Create volumer
        finalVolume = MetaRig(part=self.part, side=self.side, endSuffix="FinalVolume", nodeType="multiplyDivide")
        finalVolume.operation = 2
        supportNodes["FinalVolume"] = finalVolume

        # Inverse Condition
        inverseCondition = MetaRig(part=self.part, side=self.side, endSuffix="InverseCondition", nodeType="condition")
        inverseCondition.secondTerm = 1
        inverseCondition.operation = 4
        supportNodes["InverseCondition"] = inverseCondition

        # Inverse Multiply
        inverseMultiply = MetaRig(part=self.part, side=self.side, endSuffix="InverseMultiply",
                                  nodeType="multiplyDivide")
        inverseMultiply.input2 = [-1, 1, 1]
        supportNodes["InverseMultiply"] = inverseMultiply

        # Connect all the node as support nodes
        for supportType in supportNodes:
            self.addSupportNode(supportNodes[supportType], supportType)

        # Connect all the initial network
        disableClamp.pynode.outputR >> finalVolume.pynode.input2X
        disableClamp.pynode.outputR >> inverseCondition.pynode.firstTerm
        finalElasticity.pynode.output >> finalVolume.pynode.input1X
        cond.pynode.outColor.outColorG >> disableClamp.pynode.maxR
        cond.pynode.outColor.outColorR >> disableClamp.pynode.minR
        elasticityRemainder.pynode.output >> elasticityMulitplier.pynode.input1X
        elasticityRemainder.pynode.output >> positiveClamp.pynode.maxR
        elasticityRemainder.pynode.output >> negativeClamp.pynode.minR
        elasticityMulitplier.pynode.outputX >> positiveClamp.pynode.minR
        elasticityMulitplier.pynode.outputX >> negativeClamp.pynode.maxR
        triggerCondition.pynode.outColorR >> finalElasticity.pynode.input1
        inverseCondition.pynode.outColor.outColorR >> negativeClamp.pynode.input.inputR
        inverseCondition.pynode.outColor.outColorR >> positiveClamp.pynode.input.inputR
        positiveClamp.pynode.outputR >> triggerCondition.pynode.colorIfTrueR
        negativeClamp.pynode.outputR >> triggerCondition.pynode.colorIfFalseR
        inverseMultiply.pynode.outputX >> inverseCondition.pynode.colorIfTrueR

    # @endcond

    def connectDisable(self, attr):
        """
        Connect the disable attribute
        @param attr (pyattr) The incoming attribute
        """
        attr >> self.disableCondition.pynode.firstTerm

    def connectTrigger(self, attr):
        """
        Connect the trigger attribute
        @param attr (pyattr) The incoming attribute
        """

        attr >> self.disableClamp.pynode.inputR
        attr >> self.triggerCondition.pynode.firstTerm
        attr >> self.elasticityRemainder.pynode.input1

    def connectElasticity(self, attr):
        """
        Connect the elasticity attribute
        @param attr (pyattr) The incoming attribute
        """
        attr >> self.inverseCondition.pynode.colorIfFalseR
        attr >> self.inverseMultiply.pynode.input1X

    def connectOutput(self, attr):
        """
         Connect the output scale attribute
         @param attr (pyattr) The target attribute
         """

        self.finalVolume.pynode.outputX >> attr

    # @cond DOXYGEN_SHOULD_SKIP_THIS
    @property
    def finalVolume(self):
        return self.getSupportNode("FinalVolume")

    @property
    def disableCondition(self):
        return self.getSupportNode("DisableCondition")

    @property
    def disableClamp(self):
        return self.getSupportNode("DisableClamp")

    @property
    def elasticityRemainder(self):
        return self.getSupportNode("ElasticityRemainder")

    @property
    def triggerCondition(self):
        return self.getSupportNode("TriggerCondition")

    @property
    def inverseCondition(self):
        return self.getSupportNode("InverseCondition")

    @property
    def inverseMultiply(self):
        return self.getSupportNode("InverseMultiply")
        # @endcond


Red9_Meta.registerMClassInheritanceMapping()
Red9_Meta.registerMClassNodeMapping(nodeTypes=['transform',
                                               'camera',
                                               'joint',
                                               'reverse',
                                               'plusMinusAverage',
                                               'multiplyDivide',
                                               'condition',
                                               'clamp',
                                               'addDoubleLinear'])

if __name__ == '__main__':
    pm.newFile(f=1)
    # cam = MyCameraMeta(name="MyCam")
    # cam.item = "test"
    # print cam.mNode
    # print cam.item
    #
    # filePath = pm.saveAs(r"C:\temp\testMeta.ma")
    # pm.newFile(f=1)
    # pm.openFile(filePath)
    # cam = Red9_Meta.MetaClass("MyCam")
    # print cam.mNode
    # print cam.item
    #

    # pm.newFile(f=1)
    # # cam = MyCameraMeta()
    # subSystem = SubSystem(side="L", part="Core")
    #
    # mRig = Red9_Meta.MetaRig(name='CharacterRig', nodeType="transform")
    # mRig.connectChild(subSystem, 'Arm')
    # subSystem.setParent(mRig)
    #
    # fkSystem = subSystem.addMetaSubSystem(MetaRig)
    # fkSystem = SubSystem(side="U", part="Arm")
    # fkSystem.setParent(subSystem)
    # subSystem.connectChild(fkSystem, 'FK_System')
    # # l = rig(side="L", part="Test")
    #
    # myCtrl = Ctrl(side="L", part="Hand")
    # myCtrl.build()
    # myCtrl.addGimbalMode()

    # myCtrl = Ik(side="L", part="Hand")
    #
    # myCtrl.addSpaceLocator()
    # myCtrl.setParent(fkSystem)
    #
    # myCtrl1 = Ctrl(side="U", part="FK1")
    # myCtrl1.create_ctrl()
    #
    # myCtrl1.setParent(fkSystem)
    #
    # fkCtrls = [myCtrl.mNode, myCtrl1.mNode]
    # fkCtrls = [myCtrl]
    # fkSystem.connectChildren(fkCtrls, "Ctrl")
    # fkSystem.convertToComponent("FK")
    # subSystem.connectChildren(fkCtrls, "FK")

    # jntSystem = JointSystem(side="C", part="Cora")
    # joints = utils.create_test_joint("ik2jnt")
    # jntSystem.Joints = joints
    # jntSystem.convertJointsToMetaJoints()
    # rep = jntSystem.replicate(side="L", part="CoraHelp", supportType="Help")
    #
    #
    # # Need to run this in case of opening and closing file
    #
    # from PKD_Tools.Red9 import Red9_Meta
    # reload(Red9_Meta)
    #
    # from PKD_Tools.Rigging import core
    # reload(core)
    #
    # # k = Red9_Meta.MetaClass("CharacterRig")
    # pm.newFile(f=1)
    # SpaceLocator(part="main", side="C")

    toon = CartoonySystem(side="C", part="Cora")
    toon.build()
