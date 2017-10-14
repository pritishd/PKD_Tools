import pymel.core as pm

from PKD_Tools import libUtilities
from PKD_Tools.Rigging import core, joints, gui


# TODO: Annotated Nodes wichrome://extensionll have prn
# TODO: Use constrianedNode property to determine parents
# TODO: We might need to override the side with our own alias eg {"C":None: "L": "AS" }

class Info(object):
    """
    Api to deal with exportable/imported. This will have quick properties for faster access
    """

    def __init__(self, info):
        self.info = info.copy()

    @property
    def jointData(self):
        return self.info["Build"]["JointData"]

    @property
    def gimbalData(self):
        return self.info["Build"]["GimbalData"]

    @property
    def side(self):
        return self.info["Side"]

    @property
    def options(self):
        return self.info["Options"].copy()

    @property
    def parent(self):
        if self.info.has_key("Parent"):
            return self.info["Parent"]

    @property
    def part(self):
        return self.info["Part"]


class AnnotatedLocator(core.SpaceLocator):
    def __init__(self, *args, **kwargs):
        if kwargs.has_key("part"):
            kwargs["part"] = libUtilities.unique_name(kwargs["part"])
        # Set the unique name
        super(AnnotatedLocator, self).__init__(*args, **kwargs)
        if self._build_mode:
            libUtilities.lock_scale(self.pynode)
            libUtilities.lock_rotate(self.pynode)
            self.pynode.Symmetry.set(keyable=False, channelBox=False)
            self.resetName()

    # noinspection PyUnresolvedReferences
    def build(self):
        # Create the annotation
        pm.select(clear=True)
        locPosition = libUtilities.get_world_space_pos(self.pynode)

        pm.select(self.mNode)
        fakeJoint = pm.annotate(self.mNode, point=locPosition).getParent()
        fakeJoint.setParent(self.pynode)
        fakeJoint.v.set(False)
        fakeJointMeta = core.MovableSystem(fakeJoint.name())
        fakeJointMeta.template = True
        self.transferPropertiesToChild(fakeJointMeta, "FakeJoint")
        fakeJointMeta.part = self.part
        fakeJointMeta.resetName()
        self.fakeJoint = fakeJointMeta

        # Build the label annotation
        annotation = pm.annotate(self.mNode, point=locPosition, tx=self.trueName).getParent()
        annotation.displayArrow.set(False)
        annotationMeta = core.MovableSystem(annotation.name())
        annotationMeta.template = True
        self.transferPropertiesToChild(annotationMeta, "Anno")
        annotationMeta.part = self.part
        annotationMeta.resetName()
        annotationMeta.setParent(self)
        self.annotation = annotationMeta

    # noinspection PyUnresolvedReferences
    def setJointParent(self, targetSystem):
        """
        Parent the annotation to another AnnotatedLocator system. This will show the parent child relationship
        @param targetSystem (metaRig) The target AnnotatedLocator you are trying to parent
        """
        if not isinstance(targetSystem, AnnotatedLocator):
            raise RuntimeError("You can only reparent another annotated locator")

        fakeJointMeta = self.fakeJoint
        if fakeJointMeta.pynode.getParent() != targetSystem.pynode:
            fakeJointMeta.setParent(targetSystem)

            # Match the position
            fakeJointMeta.snap(targetSystem, rotate=False)
            fakeJointMeta.v = True

            # Connect attr
            targetShapeAttr = self.pynode.getShape().worldMatrix[0]
            fakeJointAttr = fakeJointMeta.pynode.getShape().dagObjectMatrix[0]

            if self.pynode not in fakeJointAttr.listConnections():
                targetShapeAttr >> fakeJointAttr

        else:
            print "Already parented to the right one"
            print "Target: {0}, FakeMeta: {1}".format(targetSystem.pynode, fakeJointMeta.pynode)

    def setParent(self, targetSystem):
        """Parent the joint system"""
        if not isinstance(targetSystem, AnnotatedLocator):
            raise RuntimeError("You can only reparent another annotated locator")

        self.setJointParent(self.constrainedNode)
        targetSystem.getParentMetaNode().prnt = self.constrainedNode

    def __bindData__(self, *args, **kwgs):
        super(AnnotatedLocator, self).__bindData__(*args, **kwgs)
        self.addAttr("Symmetry", enumName="Symmetrical:Asymmetrical:Unique", attrType='enum')

    def rename(self, newName, renameChildLinks=True):
        """

        @param newName: new name for the mNode
        @param renameChildLinks: set to True by default, this will rename connections back to the mNode
            from children who are connected directly to it, via an attr that matches the current mNode name.
            These connected Attrs will be renamed to reflect the change in node name
        """
        super(AnnotatedLocator, self).rename(newName, renameChildLinks)
        self.part = newName
        self.resetName()
        # Rename the fakeJoint
        self.fakeJoint.rename(newName, renameChildLinks)
        self.fakeJoint.part = newName
        self.fakeJoint.resetName()
        # Rename the locator
        self.annotation.rename(newName, renameChildLinks)
        self.annotation.part = newName
        self.annotation.resetName()
        self.annotation.pynode.text.set(newName)

    @property
    def constrainedNode(self):
        return self

    # noinspection PyMissingOrEmptyDocstring
    @property
    def trueName(self):
        return self.part

    # noinspection PyMissingOrEmptyDocstring
    @property
    def fakeJoint(self):
        return self.getSupportNode("FakeJoint")

    # noinspection PyMissingOrEmptyDocstring
    @fakeJoint.setter
    def fakeJoint(self, data):
        self.addSupportNode(data, "FakeJoint")

    # noinspection PyMissingOrEmptyDocstring
    @property
    def annotation(self):
        return self.getSupportNode("Annotation")

    # noinspection PyMissingOrEmptyDocstring
    @annotation.setter
    def annotation(self, data):
        self.addSupportNode(data, "Annotation")


class PalmAnnotatedLocator(AnnotatedLocator):
    @property
    def constrainedNode(self):
        return self.getParentMetaNode().prnt.Joints[0]


class HoofAnnotatedLocator(AnnotatedLocator):
    @property
    def constrainedNode(self):
        return self.getParentMetaNode().prnt.Joints[-1]


class FootAnnotatedLocator(AnnotatedLocator):
    @property
    def constrainedNode(self):
        return self.getParentMetaNode().prnt.Joints[1]


class BuilderJointSystem(joints.JointCollection):
    _annotatedLocator = AnnotatedLocator

    def buildNewJoints(self, templateNames, currentPos=None):
        """
        Build a new template system
        @param templateNames: List of names of templates
        @param currentPos: (vector) The initial position
        """
        if currentPos is None:
            currentPos = [0, 1, 0]
        metaLocators = []
        for count, locName in enumerate(templateNames):
            jointData = {"Name": locName,
                         "Position": [currentPos[0], currentPos[1] + count, currentPos[2]],
                         "JointOrient": []}
            metaLocators.append(self.buildLocator(jointData, metaLocators[count - 1] if count else None))
            self.jointData += [jointData]

        self.joints = metaLocators

    def updatePositionData(self):
        jointData = self.jointData
        for jointInfo, joint in zip(jointData, self.joints):
            jointInfo["Position"] = list(joint.pynode.getTranslation(space="world"))
        self.jointData = jointData

    # noinspection PyCallingNonCallable
    def buildLocator(self, jointData, parent=None):
        """
        Build locator and set joint parent if possible
        @param jointData: Joint data which contains information on how to build this locator
        @param parent: An annotated  locator
        @return: The build meta locator
        """
        metaLocator = self.jointClass(side="L", part=jointData["Name"])
        jointData["Name"] = metaLocator.part
        metaLocator.build()
        metaLocator.translate = jointData["Position"]
        if parent:
            metaLocator.setJointParent(parent)
        return metaLocator

    def mirrorJoint(self, metaJoint):
        """
        Mirror the meta locator on YZ axis
        @param metaJoint: The meta joint being mirrored
        """
        metaJoint.tx = metaJoint.tx * -1

    @property
    def jointClass(self):
        return self._annotatedLocator

    # noinspection PyMethodOverriding
    @jointClass.setter
    def jointClass(self, locatorSystemType):
        if not isinstance(locatorSystemType, AnnotatedLocator):
            raise TypeError("Target system must be a type of 'Annotated Locator'")
        self._annotatedLocator = locatorSystemType

    @property
    def hasJointOrientData(self):
        if self.jointData:
            return bool(self.jointData[0]["JointOrient"])
        else:
            return False


class Builder(core.MovableSystem):
    """TODO: Build templates from data"""
    def __init__(self, *args, **kwargs):
        super(Builder, self).__init__(*args, **kwargs)
        self.jointWin = None
        self.options = {"symType": "sym", "mirror": "Orientation"}
        self.importData = None

    def __bindData__(self, *args, **kwargs):
        super(Builder, self).__bindData__(*args, **kwargs)
        self.addAttr("options", {})

    def rebuild(self):
        info = self.importData
        # Create the Build system
        builderJointsSystem = BuilderJointSystem(part=info.part, side=info.side, endSuffix="BuildSys")
        builderJointsSystem.jointData = info.jointData
        builderJointsSystem.gimbalData = info.gimbalData
        builderJointsSystem.build()


        for i, loc in enumerate(builderJointsSystem.joints):
            pm.select(cl=True)
            loc.build()
            loc.pynode.setParent(self.pynode)
            if i:
                loc.setJointParent(builderJointsSystem.joints[i - 1])
        self.options = info.options


        # Build the joint system
        self.builderJointSystem = builderJointsSystem
        self.buildJointSystem()
        self.jointSystem.joints[0].v = False

        return info

    def buildTemplate(self):
        builderJointsSystem = BuilderJointSystem(part=self.part, side=self.side, endSuffix="BuildSys")
        builderJointsSystem.buildNewJoints(self.templateNames)
        for loc in builderJointsSystem.joints:
            loc.pynode.setParent(self.pynode)

        self.builderJointSystem = builderJointsSystem

    def buildJointSystem(self):
        if not self.builderJointSystem:
            raise ValueError("No build system defined. Cannot make a joint system")
        newJointSystem = joints.JointSystem(part=self.part, side=self.side, endSuffix="JntSys")
        newJointSystem.jointData = self.builderJointSystem.jointData
        newJointSystem.gimbalData = self.builderJointSystem.gimbalData
        newJointSystem.build()
        newJointSystem.joints[0].setParent(self)
        self.jointSystem = newJointSystem

    def loc2joint(self):
        self.builderJointSystem.updatePositionData()
        if not self.jointSystem:
            self.buildJointSystem()
        else:
            if self.builderJointSystem.jointData != self.jointSystem.jointData:
                self.jointSystem.jointData = self.builderJointSystem.jointData
                self.jointSystem.updatePosition()

        self.jointSystem.joints[0].v = True
        pyJoints = [joint.pynode for joint in self.builderJointSystem.joints]
        for shape in pm.listRelatives(pyJoints, allDescendents=True, shapes=True):
            shape.visibility.set(False)

    def jointOrientWin(self):
        if self.jointSystem:
            jointWin = gui.JointOrientWindow([self.jointSystem.pynode.gimbalData,
                                              self.builderJointSystem.pynode.gimbalData],
                                             self.joint2loc)
            jointWin.show()
            jointWin.joint_widget.gimbal_data = self.jointSystem.gimbalData
            jointWin.joint_widget.joint = self.jointSystem.joints[0].pynode
            jointWin.joint_widget.set_ui_from_gimbal_data()
            self.jointWin = jointWin

    def joint2loc(self):
        self.jointSystem.rebuild_joint_data()
        self.jointSystem.joints[0].v = False
        pyJoints = [joint.pynode for joint in self.jointSystem.joints]
        libUtilities.freeze_rotation(pyJoints)
        pyLocs = [joint.pynode for joint in self.builderJointSystem.joints]
        self.builderJointSystem.jointData = self.jointSystem.jointData
        self.builderJointSystem.updatePosition()
        for shape in pm.listRelatives(pyLocs, allDescendents=True, shapes=True):
            shape.visibility.set(True)

    def setBuildParent(self, target):
        if not isinstance(target, AnnotatedLocator):
            raise TypeError("Target system must be a type of 'Annotated Locator'")
        self.buildJoints[0].setJointParent(target)
        self.prnt = target

    @property
    def buildJoints(self):
        return self.builderJointSystem.joints

    @property
    def bindJoints(self):
        return self.jointSystem.joints

    @property
    def templateNames(self):
        return ["{}0".format(self.part), "{}1".format(self.part)]

    @property
    def jointSystem(self):
        return self.getSupportNode("JointSystem")

    @jointSystem.setter
    def jointSystem(self, data):
        self.addSupportNode(data, "JointSystem")

    @property
    def builderJointSystem(self):
        return self.getSupportNode("BuilderJointSystem")

    @builderJointSystem.setter
    def builderJointSystem(self, data):
        self.addSupportNode(data, "BuilderJointSystem")

    @property
    def buildData(self):
        return {"Builder": self.builderJointSystem.buildData, "Joint": self.jointSystem.buildData}

    @property
    def exportData(self):
        """
        @return: Exportable build data
        """
        info = {"Part": self.part, "Build": self.builderJointSystem.buildData}
        if self.prnt:
            info["Parent"] = self.prnt.part
        position = round(info["Build"]["JointData"][0]["Position"][0], 3)
        side = "C"
        if position > 0.0:
            side = "L"
        elif position < 0.0:
            side = "R"
        info["Side"] = side
        info["Options"] = self.options
        return info


class Extendable(Builder):
    jointCount = 2

    @property
    def templateNames(self):
        width = 1
        if self.jointCount >= 8:
            width = 2
        return ["{self.part}{i:0{width}}".format(**locals()) for i in range(1, self.jointCount + 2)]


class Finger(Extendable):
    pass


class Eyes(Extendable):
    pass


APPENDAGE = {"Hoof": ["Hoof", "HoofEnd"],
             "Palm": ["Palm"],
             "Paw": ["Ankle", "Toe", "ToeEnd", "Heel"],
             "Foot": ["Toe", "ToeEnd", "Heel"]}


class LimbBuilder(Builder):
    appendage = ""

    @property
    def appendName(self):
        if APPENDAGE.has_key(self.appendage):
            return APPENDAGE[self.appendage]
        else:
            return []

    @property
    def templateNames(self):
        return ["HipShoulder", "KneeElbow", "AnklePalm"] + self.appendName


class QuadBuilder(LimbBuilder):
    @property
    def templateNames(self):
        return ["FemurUpper"] + super(QuadBuilder, self).templateNames


def buildTemplates(templateData):
    builderDict = {}
    for info in templateData:
        info = Info(info)
        builder = Builder(part=info.part, side=info.side)
        builder.importData = info
        builder.rebuild()
        builderDict[info.part] = builder

    for builder in builderDict.values():
        if builder.importData.parent:
            if pm.objExists(builder.importData.parent):
                metaLoc = core.MetaRig(builder.importData.parent)
                builder.setBuildParent(metaLoc)
    return builderDict


core.Red9_Meta.registerMClassInheritanceMapping()

if __name__ == '__main__':
    pm.newFile(f=1)
    extendBuilder = Extendable(part="Spine", side="C")
    extendBuilder.jointCount = 5
    extendBuilder.buildTemplate()
    extendBuilder.loc2joint()
    extendBuilder.jointOrientWin()
    li = QuadBuilder(part="Arm", side="C")
    li.appendage = "Palm"
    li.buildTemplate()
