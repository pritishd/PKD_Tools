"""@package PKD_Tools.Rigging.core @brief The main core classes for the PKD rig system. All new system are created
here until they can be grouped together to create new packages. @details The PKD rig system uses the combination of
the Red9 meta rig system and Pymel API as part of the core development process

Red9 comes with many development API to traversing networks, getting control nodes easily and initialising objects
after you open scene. In addition to this this makes PKD tools compatible  with the tools that comes with Red9 such
as a well defined pose libary and mirroring system.

PyMel which is natively supported also comes with powerful and developer friendly API such as their easy way to make
connections and OpenMaya based functionality.

However using these do come at the cost of speed however in the long run it will payoff for easier development process

The PKD tools also officially compatible with the ZV Parent Master tool which is a very refined and production tested
constraint management system.

Just a small note with regards to naming convention, while other aspects of the PKD_Tools tries to keep to the Pep8
convention however in the rigging part of the tool we use camelCase for all variable, properties and function to
conform to naming standards in maya, pyside, Red9 and pymel """

# TODO: Try to create more meta subsystem eg for the spine, so that it is easier to navigate eg subCtrlSystem or hipSystem
# TODO: Implement using format instead of % operate for string

import traceback
from collections import OrderedDict

from pymel import core as pm
from maya import cmds

from PKD_Tools import libUtilities, libJoint
from PKD_Tools.Red9 import Red9_Meta
from PKD_Tools.Rigging import utils

if __name__ == '__main__':
    for module in Red9_Meta, utils, libUtilities, libJoint:
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


def jointOrMovable(target):
    """Return the joint class or movable class based on the target evaluated metanode
    @param target: MetaRig object
    @return: @ref joints.Joints or MovableSystem metaNode
    """

    import PKD_Tools
    # noinspection PyUnresolvedReferences
    potentialClass = getattr(PKD_Tools.Rigging.joints, "Joint")
    if not isinstance(target, potentialClass):
        potentialClass = MovableSystem
    return potentialClass


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


# noinspection PyUnresolvedReferences
class MetaEnhanced(object):
    """This is a helper class which adds pynode based functionality and support. It is always used in conjunction with
    a metaRig class and never by itself"""
    # @cond DOXYGEN_SHOULD_SKIP_THIS
    _pynode_ = None
    debugMode = False
    haltProcess = False

    # @endcond

    # noinspection PyPropertyAccess,PyUnreachableCode
    # Helper function to help doxgyen register python property function as attributes
    def _doxygenHelper(self):
        """
         @property pynode
         @brief Return the pynode that is associated for the node
         @property primaryAxis
         @brief Return the rotate order as string instead of numeric value
         @property debugMode
         @brief At various point in the code we want to give helpful statement to the developer. This will enable those
         """
        raise RuntimeError("This function cannot be used")
        self.pynode = self.primaryAxis = self.debugMode = None

    # noinspection PyUnresolvedReferences
    def resetName(self):
        """Reset the name of the node to how should be named. Hopefully this strips away all numeric suffix"""
        self.pynode.rename(self.trueName)

    @staticmethod
    def breakpoint(message=""):
        """Stop any process to debug an issue
        @param message: Message to to be displayed if any
        """
        if message:
            print message
        traceback.print_stack()
        raise RuntimeError("Stopping to debug an issue")

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
            self._build_mode = True
            self.part = kwargs["part"]
            # Setup the mirror side
            self.mirrorSide = _fullSide_(kwargs["side"])
            # Set the rig type
            self.rigType = kwargs["endSuffix"]
            # Set this as non system root by default
            self.mSystemRoot = False
        else:
            super(MetaRig, self).__init__(*args, **kwargs)
            self._build_mode = False

        # For some reason we run lockState twice to register it
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

        # Initialise the meta cache dict
        self.metaCache = {}
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
        # Initialise the meta cache dict
        self.metaCache = {}
        # Return connected as meta
        self.returnNodesAsMeta = True

    def addMetaSubSystem(self, subSystem, system="FK", **kwargs):
        """Override red 9 add function """
        if isinstance(subSystem, MovableSystem):
            # Parent the group
            subSystem.setParent(self)
        # Connect it as a child
        sys_attr = '{0}_System'.format(system)
        self.connectChild(subSystem, sys_attr)
        subSystem.systemType = system
        self.metaCache[sys_attr] = subSystem

    def getMetaSubSystem(self, sys_attr="FK"):
        """Return a subsystem type"""
        sys_attr = '{0}_System'.format(sys_attr)
        if not self.metaCache.setdefault(sys_attr, None):
            self.metaCache[sys_attr] = (self.getChildren(asMeta=self.returnNodesAsMeta, cAttrs=[sys_attr])
                                        or [""])[0]
        return self.metaCache[sys_attr]

    def convertToComponent(self, component="FK"):
        """
        Convert this system to a sub component.
        @param component (string) Type of subcomponent
        """
        if component is None:
            raise RuntimeError('Component type is set to "None". This is a big problem')

        # Add a new attr
        if not hasattr(self, "systemType"):
            try:
                self.addAttr("systemType", component)
            except:
                traceback.print_stack()
                raise RuntimeError('Unable to add "systemType" to node: {0}'.format(self.mNode))
        else:
            # noinspection PyAttributeOutsideInit
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
            libUtilities.logger.info(str(e))
            libUtilities.logger.info("Rename failed on:{0}".format(self.mNode))
            self.select()
            raise RuntimeError("Rename Failed")

        libUtilities.strip_integer(self.pynode)

    def getRigCtrl(self, target):
        """
        Get the specific type of rig ctrl
        @param target (string) The type of control that is being retrieved
        @return: The meta rig
        """
        targetAttr = "{}_{}".format(self.CTRL_Prefix, target)
        if not self.metaCache.setdefault(targetAttr, None):
            children = self.getChildren(walk=False, asMeta=self.returnNodesAsMeta, cAttrs=[targetAttr])
            if children:
                self.metaCache[targetAttr] = children[0]

        return self.metaCache[targetAttr]

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
            targetAttr = "{}_{}".format(self.CTRL_Prefix, kwargs.get("ctrType") or args[0])
            self.metaCache[targetAttr] = target
        except:
            raise AssertionError("Input must be MetaClass")

    def getSupportNode(self, target):
        """
        Return the type of support node that is connected to the rig system
        @param target (string) The type of support node that is being queried
        """
        targetSupport = "SUP_{}".format(target)

        if not self.metaCache.setdefault(targetSupport, None):
            children = self.getChildren(walk=False, asMeta=self.returnNodesAsMeta, cAttrs=[targetSupport])
            if not children:
                if self.debugMode:
                    libUtilities.logger.warn("%s not support node found on %s" % (target, self.shortName()))
            else:
                if type(children[0]) == Red9_Meta.MetaClass:
                    children[0] = MetaRig(children[0].mNode)
                self.metaCache[targetSupport] = children[0]

        return self.metaCache[targetSupport]

    def addSupportNode(self, node, attr, boundData=None):
        """
        Add support node to the system
        @param node (metaRig, pynode, string) The node that is being
        @param attr (string) The type of support node
        @param boundData (dict) Any data that is used by the metaRig superclass
        """
        metaSupport = None
        if hasattr(node, "mNode"):
            supportNode = node.mNode
            metaSupport = node
        elif isinstance(node, pm.PyNode):
            supportNode = node.name()
        else:
            supportNode = node

        super(MetaRig, self).addSupportNode(supportNode, attr, boundData=boundData)
        if not metaSupport:
            metaSupport = MetaRig(supportNode)
        targetSupport = "SUP_{}".format(attr)
        self.metaCache[targetSupport] = metaSupport
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

    @property
    def mirSide(self):
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

    def __init__(self, *args, **kwargs):
        super(MovableSystem, self).__init__(*args, **kwargs)
        if self._build_mode:
            libUtilities.lock_attr(self.pynode.v)

    # noinspection PyPropertyAccess
    def _doxygenHelper(self):
        """
        @property constrainedNode
        @brief By default the movable node is the one that will be constrained
        @property constrainedNodePy
        @brief The pynode of the constraint object
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
        @property prntPy
        @brief Get the parent node as as PyNode
        @property globalMatrix
        @brief Get the rounded matrix value in world space
        @property isZeroOut
        @brief Are all the rotation and transform values set to zero
        @property zeroGrp
        @brief The transform node which will zero out the rotation and transform value
        """
        super(MovableSystem, self)._doxygenHelper()
        self.constrainedNode = self.constrainedNode = self.orientConstraint = self.pointConstraint = \
            self.aimConstraint = self.parentConstraint = self.scaleConstraint = self.poleVectorConstraint = \
            self.prnt = self.globalMatrix = self.isZeroOut = self.prntPy = self.zeroPrnt

    def setParent(self, targetSystem):
        """
        Parent the rig system to another target system. By default if has parent we would parent that first other wise
        We will try to parent the transform
        @param targetSystem (metaRig) The target system you are trying to parent
        """
        targetNode = forcePyNode(targetSystem)
        # Does it has parent. Then we we reparent that
        if targetNode in [self.zeroPrntPy, self.prntPy]:
            return
        if hasattr(self, 'SUP_ZeroPrnt'):
            self.zeroPrntPy.setParent(targetNode)
        elif hasattr(self, "SUP_Prnt"):
            self.prnt.pynode.setParent(targetNode)
        elif self.pynode.type() in ["transform", "joint"]:
            self.pynode.setParent(targetNode)
        else:
            libUtilities.logger.error("{0} is not a transform/joint node. Unable to parent".format(self.pynode))

    def buildParent(self, parentClass, side, endSuffix):
        """Build a parent meta system. This should inherit rotate order
        @param parentClass: (metaRig) The parent class that we are trying to create
        @param side: (str) The side side for this parent
        @param endSuffix: (str) The endSuffix for this parent
        @return MetaRig
        """
        prnt = parentClass(part=self.part, side=side, endSuffix=endSuffix)
        return prnt

    def addParent(self, **kwargs):
        """Add parent node for the transform node"""
        pm.select(clear=True)
        snap = kwargs.get("snap", True)
        endSuffix = kwargs.get("endSuffix", "Prnt")
        side = self.pynode.mirrorSide.get(asString=True)[0]
        if not (self.part and side):
            raise ValueError("Part or Side is not defined: %s" % self.shortName())
        parentClass = kwargs.get("parentSystem", MovableSystem)
        self.prnt = self.buildParent(parentClass, side, endSuffix)
        if snap:
            libUtilities.snap(self.prntPy, self.pynode)
        self.pynode.setParent(self.prnt.pynode)

    def addZeroPrnt(self):
        """Add the zero group for this parent"""
        pm.select(clear=True)
        parentClass = jointOrMovable(self)
        self.zeroPrnt = self.buildParent(parentClass, self.mirSide, "ZeroPrnt")

        if self.zeroPrnt.pynode.nodeType() == "joint":
            self.zeroPrnt.rigType = "ZeroJointPrnt"
            self.zeroPrnt.resetName()

        node = self.prnt or self.constrainedNode
        self.zeroPrnt.snap(node)
        parentPy = node.pynode.getParent()
        # This ensures that if it is a joint then a joint inverse scale are set
        node.setParent(self.zeroPrnt)
        if node.pynode.getParent() != self.zeroPrntPy:
            node.pynode.setParent(self.zeroPrntPy)
        if parentPy:
            self.zeroPrntPy.setParent(parentPy)

    def setupAimHelper(self, target, aimKwargs=None, part=None, constraint=False):
        """
        Setup a aim helper.

        Aim helper don't play well with maintain offset. We will create a setup without a aim helper and then create a
        offset node which we will

        Hear we will use the following setup

        AimHelperZero - Zero out the aim helper
        AimHelper - This has the aim helper

        @param constraint:
        @param part: (str) The name of the aim helper part
        @param target (metaRig/pynode) Tbe node that will aim constraint this metaRig
        @param aimKwargs: Any aimp constraint kwargs that will be used by the aim constrain command
        @return: The aim helper
        """
        aimKwargs = aimKwargs or {}
        if aimKwargs.has_key("maintainOffset"):
            aimKwargs["mo"] = aimKwargs["maintainOffset"]
            del aimKwargs["maintainOffset"]
        aimKwargs["mo"] = False

        defaultAimKwargs = dict(worldUpType="scene",
                                aimVector=(1, 0, 0),
                                upVector=(0, 1, 0),
                                weight=1,
                                offset=(0, 0, 0))
        defaultAimKwargs.update(aimKwargs)
        part = part or "{}AimHelper".format(self.part)
        part += "Offset"
        aimClass = jointOrMovable(target)
        newTarget = aimClass(part=part, side=self.mirSide)
        newTarget.addParent()
        newTarget.snap(self)
        newTarget.setParent(self.pynode.getParent())
        pm.delete(pm.aimConstraint(target.pynode, newTarget.prnt.pynode, **defaultAimKwargs))

        aimCon = newTarget.addConstraint(target, "aim", False, **defaultAimKwargs)
        self.constraintToMetaConstraint(pm.PyNode(aimCon), "{0}AimCon".format(self.rigType), "AimConstraint")
        self.addSupportNode(newTarget, "AimHelper")
        if constraint:
            self.addConstraint(newTarget, "orient")
        return newTarget

    def addConstraint(self, target, conType="parent", zeroOut=True, **kwargs):
        """
        Add constaint to the movable node and attach as support node
        @param target (metaRig/pynode) The node that will constraint this metaRig
        @param conType (string) The constraint type eg rotate, parent, point etc
        @param zeroOut (bool) Whether to zero out the dag node before applying a constraint
        @param kwargs (dict) Any keywords arguments to pass on the default maya function
        @return: name of the constraint node
        """
        if kwargs.has_key("maintainOffset"):
            kwargs["mo"] = kwargs["maintainOffset"]
            del kwargs["maintainOffset"]
        else:
            kwargs["mo"] = kwargs.get("mo", True)

        # Ensure that we are dealing with a pynode
        targetPy = forcePyNode(target)

        # Debug statement
        if self.debugMode:
            libUtilities.logger.warning("%sConstrainting %s to %s. Maintain offset is %s "
                                        % (conType, self.constrainedNodePy, targetPy, kwargs["mo"]))

        # Get the constraint function from the library
        consFunc = getattr(pm, "%sConstraint" % conType)

        # Check the constraint type
        if self.constrainedNodePy.nodeType() not in ["transform", "joint"]:
            libUtilities.logger.error(
                "%s is not a transform/joint node. Unable to add constraint" % self.constrainedNodePy)

        # Delete the weightAlias keywords from the kwargs list before passing it to Maya
        weightAlias = kwargs.get("weightAlias")
        if weightAlias:
            del kwargs["weightAlias"]

        # Set the constraint

        target = MovableSystem(target.shortName())
        if self.globalMatrix != target.globalMatrix:
            print("Matrix different: {} {}".format(self.shortName(), targetPy.shortName()))
            offsetClass = jointOrMovable(target)
            part = self.part
            if weightAlias:
                part += weightAlias
            else:
                part += target.part
            part += "Offset"
            newTarget = offsetClass(part=part, side=self.mirSide)
            newTarget.addParent()
            newTarget.snap(self)
            newTarget.setParent(target)
            targetPy = newTarget.pynode

            # Zero out the transform
        if not self.constrainedNode.isZeroOut and zeroOut:
            self.addZeroPrnt()

        constraintNodeName = consFunc(targetPy, self.constrainedNodePy, **kwargs).name()
        supportNodeType = "%sConstraint" % conType.title()
        if not eval("self.%sConstraint" % conType):
            constraintMeta = ConstraintSystem(constraintNodeName)
            constraintMeta.rigType = "{0}{1}Con".format(self.rigType, libUtilities.capitalize(conType))
            constraintMeta.mirrorSide = self.mirrorSide
            constraintMeta.part = self.part
            constraintMeta.resetName()
            constraintNodeName = constraintMeta.trueName
            self.addSupportNode(constraintMeta, supportNodeType)

        # Store information about multi targeted aliases
        if weightAlias:
            constraintMeta = self.getSupportNode(supportNodeType)
            constraintMeta.weightAliasInfo = weightAlias
        return constraintNodeName

    def snap(self, target, rotate=True, translate=True):
        """
        Match the position of the system to the target node
        @param translate:
        @param target (pynode/string) Self descriptive
        @param rotate (bool) Whether to match rotation
        """
        # Check that we are only applying to joint/transform
        target = forcePyNode(target)
        if all(pm.objectType(node) in ["transform", "joint"] for node in [self.pynode, target]):
            snapTarget = self.zeroPrnt or self.prnt or self
            libUtilities.snap(snapTarget.pynode, target, rotate=rotate, translate=translate)

    def lockTranslate(self):
        """Lock all the translate channels"""
        libUtilities.lock_translate(self.pynode)

    def lockRotate(self):
        """Lock all the rotate channels"""
        libUtilities.lock_rotate(self.pynode)

    def lockScale(self):
        """Lock all the scale channels"""
        libUtilities.lock_scale(self.pynode)

    def lockDefaultAttributes(self):
        """Lock all the default maya attributes channels"""
        libUtilities.lock_default_attribute(self.pynode)

    def constraintToMetaConstraint(self, pyConstraint, endSuffix, supportType):
        """
        Convert a pynode constraint to meta constraint

        @param pyConstraint: (pynode) The constraint node as a pymel object
        @param endSuffix: (str) The rigtype for this meta node
        @param supportType: (str) The support type for this node
        """
        constraintMeta = ConstraintSystem(pyConstraint.name())
        self.transferPropertiesToChild(constraintMeta, endSuffix)
        constraintMeta.part = self.part
        constraintMeta.resetName()
        self.addSupportNode(constraintMeta, supportType)

    # @cond DOXYGEN_SHOULD_SKIP_THIS
    @property
    def constrainedNode(self):
        return self

    @property
    def constrainedNodePy(self):
        return self.constrainedNode.pynode

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
        self.addSupportNode(data, "Prnt")

    @property
    def prntPy(self):
        return self.prnt.pynode if self.prnt else None

    @property
    def globalMatrix(self):
        return [round(value, 6) for value in cmds.xform(self.mNode, query=True, worldSpace=True, matrix=True)]

    @property
    def isZeroOut(self):
        trans = cmds.xform(self.mNode, query=True, translation=True)
        rotate = cmds.xform(self.mNode, query=True, rotation=True)

        return all(not round(value, 4) for value in (trans + rotate))

    @property
    def zeroPrnt(self):
        return self.getSupportNode("ZeroPrnt")

    @zeroPrnt.setter
    def zeroPrnt(self, data):
        self.addSupportNode(data, "ZeroPrnt")

    @property
    def zeroPrntPy(self):
        return self.zeroPrnt.pynode if self.zeroPrnt else None
        # @endcond


class TransSubSystem(MovableSystem):
    """This is a MovableSystem which can be converted to a subcomponent. Artist will not interact with this node."""

    def __bindData__(self, *args, **kwgs):
        """Ensure to add a systemType attribute is added"""
        super(TransSubSystem, self).__bindData__(*args, **kwgs)
        self.addAttr('systemType', "")


class NoInheritsTransform(TransSubSystem):
    """This transform does not inherit transform from the hierachy"""

    def __init__(self, *args, **kwargs):
        super(NoInheritsTransform, self).__init__(*args, **kwargs)
        self.inheritsTransform = False
        libUtilities.lock_attr(self.pynode.inheritsTransform)


class Network(MetaRig):
    """@brief This is a MetaRig that doesn't create a transform node.
    @details Used for organising nodes and creating subsystem"""

    def __init__(self, *args, **kwargs):
        kwargs["nodeType"] = "network"
        kwargs["endSuffix"] = kwargs.get("endSuffix", "Sys")
        super(Network, self).__init__(*args, **kwargs)


class NetSubSystem(Network):
    """An extended class of Network class where it is always going to be part of sub system, therefore it will
    always add 'systemType' attr to the node eg Cartoony system"""

    def __bindData__(self, *args, **kwgs):
        """Ensure to add a systemType attribute is added"""
        super(NetSubSystem, self).__bindData__(*args, **kwgs)
        self.addAttr('systemType', "")


# noinspection PyMissingOrEmptyDocstring


# noinspection PyUnresolvedReferences
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
            # Transfer the locator shape to the main node
            libUtilities.transfer_shape(tempLoc, self.mNode, fix_name=True)
            # Delete the temp loc
            pm.delete(tempLoc)

    # @endcond

    def clusterCV(self, cv):
        """
        Cluster a CV without using a cluster deformer. More faster
        @param cv: (pynode/string) The cv that is being clustered
        """
        cv = forcePyNode(cv)
        self.snap(cv.name(), rotate=False)
        libUtilities.cheap_point_constraint(self.pynode, cv)


class MetaShape(MovableSystem):
    """A class with shape centric functions such as rolling, scaling etc"""

    def clusterShape(self, shapeCentric=True):
        cluster = pm.cluster(self.pynode)[1]
        transform = pm.createNode("transform", name="tempTransform")
        transform.rotateOrder.set(self.rotateOrder)
        translateSnap = True
        if shapeCentric:
            libUtilities.snap(transform, cluster, rotate=False)
            translateSnap = False
        libUtilities.snap(transform, self.pynode, translate=translateSnap)
        cluster.setParent(transform)
        prnt = libUtilities.parZero(transform)
        prnt.rotateOrder.set(self.rotateOrder)
        return transform

    def cleanShapeHistory(self, transform=None):
        pm.delete(self.pynode, constructionHistory=True)
        if transform:
            pm.delete(transform.getParent())

    def scaleShape(self, scaleAmount, shapeCentric=True):
        cluster = self.clusterShape(shapeCentric)
        cluster.scale.set([scaleAmount, scaleAmount, scaleAmount])
        self.cleanShapeHistory(cluster)

    def twistShape(self, degrees, shapeCentric=True):
        cluster = self.clusterShape(shapeCentric)
        gimbal_data = libJoint.get_gimbal_data(self.primaryAxis)
        cluster.attr("r{}".format(gimbal_data["twist"])).set(degrees)
        self.cleanShapeHistory(cluster)

    def rollShape(self, degrees, shapeCentric=True):
        cluster = self.clusterShape(shapeCentric)
        gimbal_data = libJoint.get_gimbal_data(self.primaryAxis)
        cluster.attr("r{}".format(gimbal_data["roll"])).set(degrees)
        self.cleanShapeHistory(cluster)

    def bendShape(self, degrees, shapeCentric=True):
        cluster = self.clusterShape(shapeCentric)
        gimbal_data = libJoint.get_gimbal_data(self.primaryAxis)
        cluster.attr("r{}".format(gimbal_data["bend"])).set(degrees)
        self.cleanShapeHistory(cluster)

    def transferShape(self, target):
        target = forcePyNode(target)
        libUtilities.transfer_shape(target, self.pynode, fix_name=True)
        pm.delete(target)


class SimpleCtrl(MetaShape):
    """Meta rig to create a simple nurbs shape"""

    # @cond DOXYGEN_SHOULD_SKIP_THIS
    def __init__(self, *args, **kwargs):
        kwargs["endSuffix"] = "Ctrl"
        super(SimpleCtrl, self).__init__(*args, **kwargs)
        # Define the control shape
        self.ctrlShape = kwargs.get("shape", "Ball")
        # Define the mirrorside
        self.mirrorData = {'side': self.mirrorSide, 'slot': 1}
        # @endcond

    def build(self):
        """Get the preset shape and build the ctrl"""
        tempCtrlShape = utils.buildCtrlShape(self.ctrlShape)
        self.transferShape(tempCtrlShape)


class Ctrl(SimpleCtrl):
    """The meta rig for a control system.
    @details A typical control will have the following setup
    <ul>
    <li>Prnt = The main parent control</li>
        <li>Xtra = An extra transform where the animator can push constraints or set driven keys<l/i>
            <li>Ctrl - The actual control that is exposed to the animator<l/i>
                <li>Gimbal - An extra controller to take handle gimbal lock issues</li>
    </ul>
    Depending on the rig requirement some controls may also have an additional ZV parent master setup to work with the
    tool. It might be ideal to disable the extra transform for a lighter hierarchy
    """

    # @cond DOXYGEN_SHOULD_SKIP_THIS
    def __init__(self, *args, **kwargs):
        super(Ctrl, self).__init__(*args, **kwargs)
        self.createXtra = kwargs.get("createXtra", True)
        # Whether this is parent master system
        self.hasParentMaster = kwargs.get("parentMaster", False)
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
        super(Ctrl, self).build()
        # Create the xtra grp
        if self.createXtra:
            self.xtra = MovableSystem(part=self.part, side=self.side, endSuffix="Xtra")
        # Create the Parent
        self.prnt = MovableSystem(part=self.part, side=self.side, endSuffix="Prnt")
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
        self.gimbal = SimpleCtrl(name=utils.nameMe(self.side, self.part, "Gimbal"),
                                 nodeType="transform",
                                 shape="Spike")
        self.gimbal.part = self.part
        self.gimbal.mirrorSide = self.mirrorSide
        self.gimbal.rigType = "gimbalHelper"
        self.gimbal.pynode.setParent(self.mNode)
        self.gimbal.build()
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

    # noinspection PyStatementEffect
    def addPivot(self):
        """Add animatable pivot to a control. Most useful in a @ref limb.Foot setup"""
        # @cond DOXYGEN_SHOULD_SKIP_THIS
        self.pivot = SimpleCtrl(name=utils.nameMe(self.side, self.part, "Pivot"),
                                nodeType="transform",
                                shape="Locator")
        self.pivot.part = self.part
        self.pivot.mirrorSide = self.mirrorSide
        self.pivot.rigType = "pivot"
        self.pivot.pynode.setParent(self.mNode)
        self.pivot.build()
        # Snap ctrl
        libUtilities.snap(self.pivot.mNode, self.mNode)

        self.pivot.pynode.setParent(self.mNode)

        self.pivot.pynode.translate >> self.pynode.rotatePivot
        self.pivot.pynode.translate >> self.pynode.scalePivot

        # Add Attribute control the visibility
        self.addDivAttr("Show", "pivotVis")
        self.addBoolAttr("Pivot")
        self.pynode.Pivot >> self.pivot.pynode.getShape().v
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
        """Overwritten function to ensure that the @ref zeroPrnt #ref prnt is always parented instead of the control node itself"""
        if self.zeroPrnt:
            self.zeroPrnt.setParent(targetSystem)
        else:
            self.prnt.setParent(targetSystem)

    def setRotateOrder(self, rotateOrder):
        """Set the rotate order of the various controls"""
        for node in self.createdNodes:
            node.rotateOrder = rotateOrder

    def addDivAttr(self, label, ln=""):
        """Add a divider label"""
        if not ln:
            ln = label[0].lower() + label[1:]
        libUtilities.addDivAttr(self.mNode, label=label, ln=ln)

    def addBoolAttr(self, label, sn=""):
        """Add a boolean atrbiture"""
        libUtilities.addBoolAttr(self.mNode, label=label, sn=sn)

    def addFloatAttr(self, attrName="", attrMax=1, attrMin=0, SV=0, sn="", dv=0):
        """
        Add a float attribute. Same arguments as @ref libUtilities.addFloatAttr "addFloatAttr"
        """
        libUtilities.addFloatAttr(self.mNode, attrName=attrName, attrMax=attrMax, attrMin=attrMin, softValue=SV,
                                  shortName=sn, defaultValue=dv)

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

    def _createSpecialDrivers_(self, nodeType, supportType):
        """Internal function to create special XYZ node drivers

        This adds a special attr to track connected axis
        @param nodeType: (str) The type of node you want
        @param supportType: (str) The suffix name and support type
        """

        metaNode = MetaRig(side=self.side,
                           part=self.part,
                           nodeType=nodeType,
                           endSuffix=supportType)

        metaNode.addAttr("connectedAxis", {"X": False, "Y": False, "Z": False})
        self.addSupportNode(metaNode, supportType)
        return metaNode

    def _connectAxisRotateDriver_(self, axis):
        """Internal function to connect rotate driver"""
        pmaMeta = self.getSupportNode("RotateDriver")
        if not pmaMeta:
            pmaMeta = self._createSpecialDrivers_("plusMinusAverage", "RotateDriver")

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

    def addCounterTwist(self):
        """Internal function to get a negative twist value. This is important when the behaviour of a joint is
        mirrored and maya is twisting the other way eg IKHandle

        This node must be explicitly created by the other rig part
        """
        self._createSpecialDrivers_("multiplyDivide", "CounterTwist")

    def getTwistDriver(self, axis):
        """
        Get the twist driver
        @param axis: (string) Which XYZ axis that is being driven
        @return: Pynode attribute that needs to be connected
        """
        rotateDriverAttr = self.getRotateDriver(axis)
        counterTwistNode = self.getSupportNode("CounterTwist")
        if counterTwistNode:
            counterTwistStatus = counterTwistNode.connectedAxis
            if not counterTwistStatus[axis]:
                rotateDriverAttr >> counterTwistNode.pynode.attr("input1{}".format(axis))
                counterTwistNode.pynode.attr("input2{}".format(axis)).set(-1)
            return counterTwistNode.pynode.attr("output{}".format(axis))
        else:
            return rotateDriverAttr

    def getRotateDriver(self, axis):
        """
        A rotate driver is where instead of using direct connections we use plus minus average
        This will allows us to add rotation value from gimbal node and the control
        @param axis: (string) Which XYZ axis that is being driven
        @return: Pynode attribute that needs to be connected
        """
        pynode = self.pynode
        attr = "r"
        if self.hasGimbal:
            pmaMeta = self._connectAxisRotateDriver_(axis)
            pynode = pmaMeta.pynode
            attr = "output3D"
        return pynode.attr("{0}{1}".format(attr, axis.lower()))

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
        return self.prnt

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
        return self.getRigCtrl("Gimbal")

    @gimbal.setter
    def gimbal(self, data):
        self.addRigCtrl(data, "Gimbal")

    @property
    def hasGimbal(self):
        return self.gimbal is not None

    @property
    def pivot(self):
        data = self.getRigCtrl("Pivot")
        return data

    @pivot.setter
    def pivot(self, data):
        self.addRigCtrl(data, "Pivot")

    @property
    def hasPivot(self):
        return self.pivot is not None

    @property
    def locator(self):
        data = self.getSupportNode("Locator")
        return data

    @locator.setter
    def locator(self, data):
        self.addSupportNode(data, "Locator")

    @property
    def hasLocator(self):
        return self.locator is not None

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


# noinspection PyStatementEffect
class StretchSystem(Network):
    def build(self):
        supportNodes = dict()
        # Create the initialiser
        triggerCondition = MetaRig(part=self.part, side=self.side, endSuffix="TriggerCondition",
                                   nodeType="multiplyDivide")
        triggerCondition.operation = 2
        supportNodes["Trigger"] = triggerCondition

        # Remove the difference from 1
        remainder = MetaRig(part=self.part, side=self.side, endSuffix="Remainder", nodeType="addDoubleLinear")
        supportNodes["Remainder"] = remainder

        # Muliply that effect from factor
        factor = MetaRig(part=self.part, side=self.side, endSuffix="Factor", nodeType="multiplyDivide")
        supportNodes["Factor"] = factor

        # Add that back in the final connection
        finalOutput = MetaRig(part=self.part, side=self.side, endSuffix="FinalOutput", nodeType="addDoubleLinear")
        supportNodes["FinalOutput"] = finalOutput

        # Add Global inverse MD
        inverseMD = MetaRig(part=self.part, side=self.side, endSuffix="GlobalInverse", nodeType="multiplyDivide")
        supportNodes["GlobalInverse"] = inverseMD

        # Global remainder
        globRemainder = MetaRig(part=self.part, side=self.side, endSuffix="GlobalRemainder", nodeType="addDoubleLinear")
        supportNodes["GlobalRemainder"] = globRemainder

        # Global remainder
        globRemove = MetaRig(part=self.part, side=self.side, endSuffix="GlobalRemove", nodeType="addDoubleLinear")
        supportNodes["GlobalRemove"] = globRemove

        # Connect all the node as support nodes
        for supportType in supportNodes:
            self.addSupportNode(supportNodes[supportType], supportType)

        # Set initial value
        finalOutput.input2 = 1
        remainder.input1 = -1
        finalOutput.input2X = -1
        globRemainder.input1 = 1
        inverseMD.input1X = 1
        inverseMD.input2X = -1

        # Connect
        inverseMD.pynode.outputX >> globRemainder.pynode.input2
        globRemainder.pynode.output >> globRemove.pynode.input1
        triggerCondition.pynode.outputX >> remainder.pynode.input2
        remainder.pynode.output >> globRemove.pynode.input2
        globRemove.pynode.output >> factor.pynode.input2X
        factor.pynode.outputX >> finalOutput.pynode.input1

    def setInitialValue(self, value):
        """Set initial value
        @param value: (float) The intiFal value
        """
        self.trigger.input2X = value

    def connectTrigger(self, attr):
        """Connect the trigger attribute
        @param attr (pyattr) The incoming attribute
        """
        attr >> self.trigger.pynode.input1X

    def connectAmount(self, attr):
        attr >> self.factor.pynode.input1X

    def connectGlobalScale(self, attr):
        attr >> self.globalOffset.pynode.input1X

    def connectOutput(self, attr):
        """Connect the output scale attribute
         @param attr (pyattr) The target attribute
         """
        self.finalOutput.pynode.output >> attr

    @property
    def globalOffset(self):
        return self.getSupportNode("GlobalInverse")

    @property
    def trigger(self):
        return self.getSupportNode("Trigger")

    @property
    def factor(self):
        return self.getSupportNode("Factor")

    @property
    def finalOutput(self):
        return self.getSupportNode("FinalOutput")


# noinspection PyStatementEffect
class CartoonySystem(Network):
    """@brief A setup which simulates the squash and stretch effect through joints
    @details The effect that can be driven by the scale value on the joints
    It needs a trigger attribute whose value can range from 0.001 to infinity. This can come from a joint or length value

    TODO: Document the property
    """

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


# noinspection PyStatementEffect
class MeasureSystem(Network):
    """System to measure items"""

    def __init__(self, *args, **kwargs):
        super(MeasureSystem, self).__init__(*args, **kwargs)
        if self._build_mode:
            dbNode = MetaRig(part=self.part,
                             side=self.side,
                             endSuffix="distanceBetween",
                             nodeType="distanceBetween")
            locStart = SpaceLocator(part="{}compressStart".format(self.part),
                                    side=self.side,
                                    endSuffix="loc")
            locEnd = SpaceLocator(part="{}compressEnd".format(self.part),
                                  side=self.side,
                                  endSuffix="loc")
            locStart.pynode.getShape().worldPosition >> dbNode.pynode.point1
            locEnd.pynode.getShape().worldPosition >> dbNode.pynode.point2

            self.addSupportNode(locStart, "Point1")
            self.addSupportNode(locEnd, "Point2")
            self.addSupportNode(dbNode, "Distance")

    @property
    def point1(self):
        return self.getSupportNode("Point1")

    @property
    def point2(self):
        return self.getSupportNode("Point2")

    @property
    def distance(self):
        return self.getSupportNode("Distance").distance

    @property
    def distanceAttr(self):
        return self.getSupportNode("Distance").pynode.distance


# noinspection PyStatementEffect
class MathNode(MetaRig):
    """@brief This is a MetaRig that doesn't math node node."""

    def __init__(self, *args, **kwargs):
        kwargs["nodeType"] = "asdkMathNode"
        kwargs["endSuffix"] = kwargs.get("endSuffix", "Maths")
        super(MathNode, self).__init__(*args, **kwargs)
        if self._build_mode:
            self.addAttr("output", 0.0)
            self.pynode.result >> self.pynode.output


# noinspection PyStatementEffect
class DistanceMove(MeasureSystem):
    """Move a transform object in the translate attribute based on the distance change"""

    def __init__(self, *args, **kwargs):
        super(DistanceMove, self).__init__(*args, **kwargs)
        if self._build_mode:
            self.mathNode = MathNode(part=self.part,
                                     side=self.side)
            self.mathNode.b = 1
            self.distanceAttr >> self.mathNode.pynode.a
            self.mathNode.addAttr("relativeMeasure", 0.0)
            self.mathNode.addAttr("biDirection", True)
            self.mathNode.addAttr("inverse", False)
            self.mathNode.addAttr("output", 0.0)
            self.mathNode.expr = self.formula

    def reset(self):
        self.mathNode.expr = self.formula

    def connectDisable(self, attr):
        """
        Connect the disable attribute
        @param attr (pyattr) The incoming attribute
        """
        attr >> self.mathNode.pynode.b

    def connectOutput(self, attr):
        """
         Connect the output scale attribute
         @param attr (pyattr) The target attribute
         """
        self.mathNode.pynode.output >> attr

    @property
    def mathNode(self):
        return self.getSupportNode("MathNode")

    @mathNode.setter
    def mathNode(self, data):
        self.addSupportNode(data, "MathNode")

    @property
    def formula(self):
        formula = "({0:.3f} - round(a, 3)) * b ".format(self.distance)
        if self.mathNode.relativeMeasure:
            formula += "* ({1:.3f} / {0:.3f}) ".format(self.distance, self.mathNode.relativeMeasure)
        if not self.mathNode.biDirection:
            formula += ("if round(a, 3) < {0:.3f} "
                        "else 0".format(self.distance))
        if self.mathNode.inverse:
            formula = "({}) * -1".format(formula)
        return formula


# Nodes to register
# Force load the math plugin
nodes = ['transform',
         'distanceBetween',
         'camera',
         'joint',
         'reverse',
         'plusMinusAverage',
         'multiplyDivide',
         'condition',
         'clamp',
         'addDoubleLinear']
try:
    pm.loadPlugin("asdkMathNode", quiet=True)
    nodes.append('asdkMathNode')
except RuntimeError:
    print ("MATHS NODE PLUGIN NOT FOUND")

# noinspection PyUnresolvedReferences
Red9_Meta.registerMClassInheritanceMapping()
Red9_Meta.registerMClassNodeMapping(nodeTypes=nodes)

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

    # toon = Ctrl(side="C", part="Cora", shape="Ball")
    # toon.build()
    # toon.addZeroPrnt()
    # toon2 = Ctrl(side="C", part="Cora2", shape="Ball")
    # toon2.build()
    # toon2.scaleShape(.8)
    # toon.addConstraint(toon2)

    meas = DistanceMove(side="C", part="Cora", shape="Ball")
