__author__ = 'admin'

from PKD_Tools.Rigging import core

reload(core)
from PKD_Tools.Rigging import utils

reload(utils)
from PKD_Tools import libUtilities

reload(libUtilities)
import pymel.core as pm


class ikSpline(core.ik):
    """This is a Spline IK System"""

    def build_helper_joints(self):
        # Build the help joint system
        self.HelpJointSystem = self.JointSystem.replicate(side="U", part="%sHelpJoints" % self.part,supportType="Help")


    def build_solver(self):
        # Decide which joints has the solver
        if self.HelpJointSystem:
            jntSystem = self.HelpJointSystem
        else:
            jntSystem = self.JointSystem

        # Build the main single degree curve
        baseCurve = utils.create_curve(jntSystem.positions, degree=1)
        baseCurve.rename(utils.nameMe(self.side, self.part + "Base", "Curve"))
        # Build the bspline ik curve
        ikCurve, fitNode = pm.fitBspline(baseCurve,
                                         ch=1,
                                         tol=0.01,
                                         n=utils.nameMe(self.side, self.part + "IK", "Curve"))

        # Build the spline IK
        fitNode.rename(utils.nameMe(self.side, self.part + "IK", "bSpline"))
        name = utils.nameMe(self.side, self.part, "IkHandle")
        startJoint = jntSystem.Joints[0].shortName()
        endJoint = jntSystem.Joints[-1].shortName()

        # TODO Add a meta IKHandle with parent as one of the properties
        ikHandle = pm.ikHandle(name=name,
                               sj=startJoint,
                               ee=endJoint,
                               sol="ikSplineSolver",
                               curve=ikCurve,
                               createCurve=False,
                               freezeJoints=False,
                               rootOnCurve = False
                               )[0]

        ikHandleMeta = core.MetaRig(ikHandle.name(), nodeType="ikHandle")
        ikHandleMeta.part = self.part
        ikHandleMeta.mirrorSide = self.mirrorSide
        ikHandleMeta.rigType = "ikHandle"
        ikHandleMeta.v = False

        ikHandleMeta.addParent("IkHandlePrnt", snap=False)
        self.ikHandle = ikHandleMeta


    def build_ik(self):
        self.build_helper_joints()
        # Build a single degree curve
        self.build_solver()
        # Reparent the main joints to the helperjoints
        for joint, helpJoint in zip(self.JointSystem.Joints, self.HelpJointSystem.Joints):
            joint.setParent(helpJoint)

    def test_build(self):
        # Build the help joints
        self.JointSystem = core.JointSystem(side="U", part="%sJoints" % self.part)
        joints = utils.create_test_joint(self.__class__.__name__)
        self.JointSystem.Joints = joints
        self.JointSystem.convertJointsToMetaJoints()
        self.JointSystem.setRotateOrder(self.rotateOrder)
        self.build()

    @property
    def HelpJointSystem(self):
        return self.getSupportNode("HelpJointSystem")

    @HelpJointSystem.setter
    def HelpJointSystem(self, data):
        self.addSupportNode(data, "HelpJointSystem")

    def build(self):
        self.build_ik()
        self.build_control()

    def build_control(self):
        pass

    @property
    def ikHandle(self):
        return self.getSupportNode("IKHandle")

    @ikHandle.setter
    def ikHandle(self, data):
        self.addSupportNode(data, "IKHandle")


class simpleSpine(ikSpline):
    def build_control(self):
        for joint in self.JointSystem.joint_data:
            print joint


class multiSpine(ikSpline):
    pass


core.Red9_Meta.registerMClassInheritanceMapping()
core.Red9_Meta.registerMClassNodeMapping(nodeTypes=['ikHandle', 'multiplyDivide', "clamp"])

if __name__ == '__main__':
    pm.newFile(f=1)

    # subSystem = SubSystem(side="U", part="Core")
    # print "s"

    # print ikSystem

    mainSystem = core.SubSystem(side="L", part="Core")

    ikSystem = mainSystem.addMetaSubSystem(simpleSpine, "IK")
    # ikSystem.ikControlToWorld = True
    ikSystem.test_build()
