from PKD_Tools import libUtilities, libFile
from PKD_Tools.Rigging import core, utils

reload(core)
import pymel.core as pm


class AnnotatedLocator(core.SpaceLocator):
    def __init__(self, *args, **kwargs):
        super(AnnotatedLocator, self).__init__(*args, **kwargs)
        libUtilities.lock_scale(self.pynode)
        libUtilities.lock_rotate(self.pynode)
        self.pynode.Symmetry.set(keyable=False, channelBox=False)

    # noinspection PyUnresolvedReferences
    def build(self):
        # Create the annotation
        pm.select(clear=True)
        locPosition = self.pynode.getTranslation(space="world")

        pm.select(clear=True)
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
        Parent the annotation to another AnnotatedLccator system. This will show the parent child relationship
        @param targetSystem (metaRig) The target AnnotatedLccator you are trying to parent
        """
        if not isinstance(targetSystem, AnnotatedLocator):
            raise RuntimeError("You can only reparent another annotated locator")

        fakeJointMeta = self.fakeJoint
        if fakeJointMeta.pynode.getParent() != targetSystem.pynode:
            fakeJointMeta.setParent(targetSystem)

        # Match the position
        fakeJointMeta.snap(targetSystem, rotate=False)
        fakeJointMeta.v = True

    def __bindData__(self, *args, **kwgs):
        super(AnnotatedLocator, self).__bindData__(*args, **kwgs)
        self.addAttr("Symmetry", enumName="Symmetrical:Asymmetrical:Unique", attrType='enum')

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


class AnnotatedJointSystem(core.JointCollection):
    """JointCollection class which deals with a collection of joint.    """

    def build(self):
        """Build the joints based on data from the @ref jointData joint data"""
        # TODO: When building a mirrored joint. Add a prexix to the joint name
        # Iterate though all the joint list
        if self.jointData:
            # Init the metaJoint list
            metaJoints = []
            for i, joint in enumerate(self.jointData):
                # Build a joint based on the name
                metaJoint = AnnotatedLocator(side=self.side, part=joint["Name"])
                metaJoint.build()
                # Set the position and joint orientation
                metaJoint.pynode.setTranslation(joint["Position"], space="world")
                metaJoints.append(metaJoint)
                if i:
                    metaJoint.setJointParent(metaJoints[i - 1])
            # Set the meta joints as the main joints
            self.joints = metaJoints
        else:
            libUtilities.pyLog.error("No Joint Data Specified")


class BuilderJointSystem(core.JointSystem):
    def jointOrient(self):
        pass
    def flipAxis(self):
        pass

class Builder(core.MovableSystem):
    def __init__(self, *args, **kwargs):
        super(Builder, self).__init__(*args, **kwargs)
        self.componentKwargs = {}
        self.buildData = {}

    def __bindData__(self, *args, **kwgs):
        super(Builder, self).__bindData__(*args, **kwgs)
        self.addAttr("buildData", "")

    def buildTemplate(self, number=1, parent=""):
        pass

    def joint2loc(self):
        pass

    def loc2joint(self):
        pass


class SpineBuider(Builder):
    pass


class LimbBuilder(Builder):
    pass


class QuadBuilder(Builder):
    pass


if __name__ == '__main__':
    pm.newFile(f=1)
    l = AnnotatedLocator(side="L", part="Test")

    k = AnnotatedLocator(side="L", part="TestA")
    k.build()
    l.build()
    k.translate = [0, 2, 0]
    l.setJointParent(k)
