"""
@package PKD_Tools.Rigging.spine
@brief Module which creates the three spine setup
"""

from PKD_Tools.Rigging import core
from PKD_Tools.Rigging import utils
from PKD_Tools.Rigging import parts
from PKD_Tools import libUtilities, libVector, libMath
import pymel.core as pm

# TODO: SubCtrl needs have their system so that we can navigate

class IkSpine(parts.Ik):
    """This is a Spline IK System"""

    def __init__(self, *args, **kwargs):
        super(IkSpine, self).__init__(*args, **kwargs)
        self.devSpine = False

    def buildHelperJoints(self):
        # Build the help joint system
        self.helpJointSystem = self.jointSystem.replicate(side=self.side, part="%sHelpJoints" % self.part,
                                                          supportType="Help")

    def buildDevSolver(self):
        self.buildSolver()

    @property
    def ikJointSystem(self):
        # Decide which joints has the solver
        return self.jointSystem

    def buildSolver(self):
        jntSystem = self.ikJointSystem
        # Build the main single degree curve
        baseCurve = utils.createCurve(jntSystem.positions, degree=1)
        baseCurve.rename(utils.nameMe(self.side, self.part, "CtrlCurve"))
        self.controlCurve = core.MovableSystem(baseCurve.name())
        self.controlCurve.part = self.part
        self.transferPropertiesToChild(self.controlCurve, "CtrlCurve")
        self.controlCurve.resetName()

        # Build the bspline ik curve
        ikCurve, fitNode = pm.fitBspline(baseCurve,
                                         ch=1,
                                         tol=0.01,
                                         n=utils.nameMe(self.side, self.part, "BaseCurve"))
        self.ikCurve = core.MovableSystem(ikCurve.name())
        self.ikCurve.part = self.part
        self.transferPropertiesToChild(self.ikCurve, "BaseCurve")
        fitNodeMeta = core.MovableSystem(fitNode.name())
        fitNodeMeta.part = self.part
        self.ikCurve.addSupportNode(fitNodeMeta, "BaseDriver")
        self.ikCurve.transferPropertiesToChild(fitNodeMeta, "FitNode")
        fitNodeMeta.resetName()

        # Build the spline IK
        name = utils.nameMe(self.side, self.part, "IkHandle")
        startJoint = jntSystem.joints[0].shortName()
        endJoint = jntSystem.joints[-1].shortName()
        ikHandle = pm.ikHandle(name=name,
                               sj=startJoint,
                               ee=endJoint,
                               sol="ikSplineSolver",
                               curve=ikCurve,
                               createCurve=False,
                               freezeJoints=False,
                               rootOnCurve=True
                               )[0]
        ikHandleMeta = core.MovableSystem(ikHandle.name(), nodeType="IkHandle")
        self.transferPropertiesToChild(ikHandleMeta, "IkHandle")
        ikHandleMeta.part = "IkHandle"
        ikHandleMeta.v = False
        ikHandleMeta.addParent()
        self.ikHandle = ikHandleMeta

    def build_ik(self):
        self.buildHelperJoints()
        # Build a single degree curve
        if self.devSpine:
            self.build_solver_dev()
        else:
            self.buildSolver()
        # Reparent to the skin joint to the helper joint
        if self.helpJointSystem:
            # Reparent the main joints to the helperjoints
            for joint, helpJoint in zip(self.jointSystem.joints, self.helpJointSystem.joints):
                joint.setParent(helpJoint)

    def addStretch(self):
        pass

    def build(self):
        self.build_ik()
        self.buildControl()
        self.connectToControl()
        self.cleanUp()

    def buildControl(self):
        # Create the info group which does not translate
        infoGrp = core.MovableSystem(side=self.side, part=self.part, endSuffix="InfGrp")
        # Reparent the info group
        infoGrp.setParent(self)
        # Set the Meta Group
        infoGrp.inheritsTransform = False
        # Set the main grp
        self.infoGrp = infoGrp

    def connectToControl(self):
        pass

    def reparentIkJoint(self):
        # Reparent the Joint
        self.helpJointSystem.joints[0].setParent(self)

    def cleanUp(self):
        # Reparent the Joint
        self.reparentIkJoint()
        # Reparent the two curve and ik Handle
        for crv in [self.ikCurve, self.controlCurve, self.ikHandle.prnt]:
            crv.setParent(self.infoGrp)
            crv.setParent(self.infoGrp)

        # Create the control grp
        if self.mainCtrls:
            self.ctrlGrp = core.MovableSystem(side=self.side, part=self.part, endSuffix="MainCtrlGrp")
            self.ctrlGrp.rotateOrder = self.rotateOrder
            self.ctrlGrp.setParent(self)
            for ctrl in self.mainCtrls:
                ctrl.setParent(self.ctrlGrp)

    @property
    def ctrlGrp(self):
        return self.getSupportNode("CtrlGrp")

    @ctrlGrp.setter
    def ctrlGrp(self, data):
        self.addSupportNode(data, "CtrlGrp")

    @property
    def infoGrp(self):
        return self.getSupportNode("InfoGrp")

    @infoGrp.setter
    def infoGrp(self, data):
        self.addSupportNode(data, "InfoGrp")

    @property
    def controlCurve(self):
        return self.getSupportNode("ControlCurve")

    @controlCurve.setter
    def controlCurve(self, data):
        self.addSupportNode(data, "ControlCurve")

    @property
    def ikCurve(self):
        return self.getSupportNode("IkCurve")

    @ikCurve.setter
    def ikCurve(self, data):
        self.addSupportNode(data, "IkCurve")

    @property
    def mainCtrls(self):
        return self.getChildren(asMeta=self.returnNodesAsMeta, walk=True, cAttrs=["MainCtrls"])

    @mainCtrls.setter
    def mainCtrls(self, ctrlList):
        if not ctrlList:
            raise RuntimeError("Please input a list of meta Ctrls")
        self.connectChildren(ctrlList, "MainCtrls", allowIncest=True, cleanCurrent=True)

    @property
    def helpJointSystem(self):
        return self.getSupportNode("HelpJointSystem")

    @helpJointSystem.setter
    def helpJointSystem(self, data):
        self.addSupportNode(data, "HelpJointSystem")


class SimpleSpine(IkSpine):
    @property
    def ikJointSystem(self):
        # The help joint systerm has the solver
        return self.helpJointSystem

    def buildControl(self):
        super(SimpleSpine, self).buildControl()
        ctrls = []
        for joint, pos in zip(self.jointSystem.joint_data,
                              range(len(self.jointSystem))):
            # Create the control
            spineCtrl = self.createCtrlObj(joint["Name"])
            # Add the space locator
            spineCtrl.addSpaceLocator(parent=True)
            spineCtrl.locator.v = False
            libUtilities.lock_default_attribute(spineCtrl.locator.pynode)

            # Align based on the control
            spineCtrl.setParent(self)
            ctrls.append(spineCtrl)

            # Snap to position
            spineCtrl.snap(self.jointSystem.joints[pos].mNode,
                           rotate=not self.ikControlToWorld)

        # Append the control
        self.mainCtrls = ctrls

    def connectToControl(self):
        # Skiplist
        skipAxis = []
        for axis in ["x", "y", "z"]:
            if axis != self.primaryAxis[0]:
                skipAxis.append(axis)

        # Iterate through all the joints
        for pos in range(len(self.jointSystem)):
            # Cluster the CV point on the control curve
            self.mainCtrls[pos].locator.clusterCV(self.controlCurve.pynode.cv[pos])

            # OrientConstraint the Joint
            pm.orientConstraint(self.mainCtrls[pos].parentDriver.pynode, self.jointSystem.joints[pos].pynode, mo=True,
                                skip=skipAxis)

    # def test_build(self):
    #     super(SimpleSpine, self).test_build()
    #     # Make a fake parenting chain
    #     for i in range(len(self.JointSystem)):
    #         if i:
    #             self.MainCtrls[i].addConstraint(self.MainCtrls[i - 1].pynode)


class SubControlSpine(IkSpine):
    def __init__(self, *args, **kwargs):
        super(SubControlSpine, self).__init__(*args, **kwargs)
        # List of weights [CV][JOINT]
        self.addAttr("ikSkinWeightMap", "")
        self.addAttr("preNormalisedMap", "")
        self.addAttr("fallOffMethod", "Distance")
        self.currentWeightMap = []
        if not hasattr(self, "numHighLevelCtrls"):
            self.numHighLevelCtrls = 3

    def reparentIkJoint(self):
        # Reparent the Joint
        self.jointSystem.joints[0].setParent(self)

    def buildHelperJoints(self):
        pass

    def buildSolver(self):
        # Make the default spline
        super(SubControlSpine, self).buildSolver()
        # Delete the history on the main curve
        pm.delete(self.ikCurve.mNode, constructionHistory=True)
        # Delete the shape under the Ik curve
        pm.delete(self.controlCurve.pynode.getShape())
        # Duplicate the bspline
        tempBSpline = pm.duplicate(self.ikCurve.mNode)[0]
        # Transfer the shape
        libUtilities.transfer_shape(tempBSpline, self.ikDriveCurve)
        # Delete the temp node
        pm.delete(tempBSpline)
        # Rename the shape
        libUtilities.fix_shape_name(self.ikDriveCurve)

    def buildDevSolver(self):
        super(SubControlSpine, self).buildSolver()
        # Blendshape
        self.controlCurve.select()
        self.ikCurve.select(add=True)
        # Give a temporary name as this interferes with the metaConnections
        currentName = self.controlCurve.shortName()
        self.ikDriveCurve.rename("SpineDriver")
        # Blendshape
        blendShape = pm.blendShape(name=utils.nameMe(self.side, self.part, "BlendShape"))[0]
        blendShape.setWeight(0, 1)
        # Rename the control back
        self.ikDriveCurve.rename(currentName)
        # Convert a blendnode to meta
        blendNodeMeta = core.MetaRig(blendShape.name())
        self.controlCurve.addSupportNode(blendNodeMeta, "baseDriver")
        self.controlCurve.transferPropertiesToChild(blendNodeMeta, "BlendShape")

    def skinCtrlCurve(self):
        crvSkinJnts = []
        # Iterate through main controls
        for ctrl in self.mainCtrls:
            # Create Joint and snap and parent to the control
            curveJoint = core.Joint(side=ctrl.side, part=ctrl.part, endSuffix="CurveJoint")
            curveJoint.rotateOrder = self.rotateOrder
            curveJoint.snap(ctrl.mNode)
            ctrl.addChild(curveJoint.mNode)
            ctrl.addSupportNode(curveJoint, "IkSkinJoint")
            # Connect as support joint
            crvSkinJnts.append(curveJoint)

        joints = [jnt.pynode for jnt in crvSkinJnts]

        skinCluster = libUtilities.skinGeo(self.ikDriveCurve, joints)
        skinClusterMeta = core.MetaRig(skinCluster.name())
        skinClusterMeta.part = self.part
        self.addSupportNode(skinClusterMeta, "IkSkin")
        self.transferPropertiesToChild(skinClusterMeta, "IkSkin")
        skinClusterMeta.resetName()

        # Help Joint system
        self.driveJointSystem = core.JointSystem(side=self.side, part="%sHelpJoints" % self.part)
        self.driveJointSystem.rigType = "Help"
        self.driveJointSystem.joints = joints
        self.driveJointSystem.rebuild_joint_data()

    def _calcPositionFallOff_(self, center, overRideJoints=None):
        """
        Calculate the falloff for the joints where the position becomes a new centre
        eg for the first position the weight will [1,.75,.25,0]
        for the second position the weights will [.5,1,.5,0]
        @return: The current position
        """

        if center < 1:
            raise ValueError('Centre must be positive')
        # Is there a overide of the joints
        if overRideJoints:
            joints = overRideJoints
        else:
            # Get the number of joints
            joints = float(len(self.jointSystem))

        # Init the weight list
        falloff = []
        # Will the fall off be mirrored if it goes beyond the centre
        mirrorFallOff = False
        if center / joints <= 0.5:
            center = (joints - center) + 1
            mirrorFallOff = True
        # Iterate thought all the joints
        for i in range(1, int(joints) + 1):
            val = round((center - (float(abs(center - i)))) / center, 3)

            falloff.append(round(val, 3))
        if mirrorFallOff:
            falloff.reverse()
        return falloff

    def positionFallOff(self, overRideJoints=None, transpose=True):
        if overRideJoints:
            joints = overRideJoints
        else:
            joints = float(len(self.jointSystem))
        spreadPosition = list(libMath.spread(1, joints, self.numHighLevelCtrls - 1))

        # Build [joint][CV] weightmap
        weightMap = []
        for sub in range(self.numHighLevelCtrls):
            weightMap.append(self._calcPositionFallOff_(spreadPosition[sub], overRideJoints))

        if transpose:
            # Transpose the weightmap to [CV][joint]
            self.currentWeightMap = map(list, zip(*weightMap))
        else:
            self.currentWeightMap = weightMap

    def distanceFallOff(self):
        weightMap = []
        # Zero out weights
        # zeroWeights = [1.0] + ([0] * (self.numHighLevelCtrls - 1))
        # Add to the first zero
        # self.currentWeightMap.append(list(zeroWeights))

        # For each CV calculate weights
        for cv in range(len(self.jointSystem)):
            # Init the skinDataCV
            skinDataCV = []
            # Get the distance from CV
            for joint in range(self.numHighLevelCtrls):
                jointPos = libUtilities.get_world_space_pos(self.ikSkinJoints[joint])
                skinDataCV.append(libVector.distanceBetween(jointPos, self.ikDriveCurve.getCVs()[cv]))
            # Get the max position
            maxDistance = max(skinDataCV)
            # Calculate weight
            currentWeightMap = [round(((maxDistance - position) / maxDistance), 3) for position in skinDataCV]
            weightMap.append(currentWeightMap)

        self.currentWeightMap = weightMap
        # Reverse zero
        # zeroWeights.reverse()
        # # Append the list last zero weights
        # self.currentWeightMap.append(zeroWeights)

    def calculateIkSkinFallOff(self):
        if self.fallOffMethod == "Position":
            # Calculate Positional Based weights
            self.positionFallOff()
        else:
            # Calculate Distance Based
            self.distanceFallOff()
        self.preNormalisedMap = self.currentWeightMap
        pm.select(cl=1)

    def calculateHeatPoints(self):
        currentSkinMap = self.preNormalisedMap
        # Iterate through all the weight maps for all the CV
        for weights in currentSkinMap:
            # Get the maximum value
            maxWeight = max(weights)
            # Index of this maximum value
            index = weights.index(maxWeight)
            # New weightList
            newWeights = []
            # Is weight above the threshold of .98
            if maxWeight > .98:
                # Set the weight to maximum of 1
                weights[index] = 1.0
                # Is the sum total = 1.0. If not reset other weights
                if sum(weights) != 1.0:
                    newWeights = [0] * self.numHighLevelCtrls
            else:
                # What is the difference between the weights
                diffWeight = 1.0 - maxWeight
                # copy the weight
                newWeights = list(weights)
                # Set the maxWeight to zero in the new list
                newWeights[index] = 0
                # Redistribute the difference in the proporation of the other weights
                # This way all the weight will add to 1
                newWeights = libMath.calculate_proportions(newWeights, diffWeight)

            # Set the new weights
            if newWeights:
                for i in range(self.numHighLevelCtrls):
                    if i != index:
                        weights[i] = newWeights[i]

        self.ikSkinWeightMap = currentSkinMap

    def setIkWeights(self):
        # Set to post Normalisation
        self.ikSkin.normalizeWeights.set(2)
        for i in range(len(self.ikSkinWeightMap)):
            jointWeights = zip(self.ikSkinJoints, self.ikSkinWeightMap[i])
            pm.skinPercent(self.ikSkin, self.ikDriveCurve.cv[i], transformValue=jointWeights, normalize=False)
        # Pruneweights
        # Set weight to post interactive weight
        pm.skinPercent(self.ikSkin, self.ikDriveCurve, pruneWeights=.075)
        # Normalise the weights
        self.ikSkin.forceNormalizeWeights()
        # Pruneweights
        self.ikSkin.normalizeWeights.set(1)

    def connectToMainControl(self):
        self.skinCtrlCurve()
        self.calculateIkSkinFallOff()
        self.calculateHeatPoints()
        self.setIkWeights()

    def connectToControl(self):
        self.connectToMainControl()
        self.connectTwist()
        self.build_sub_controls()

    def connectTwist(self):
        pass

    def build_sub_controls(self):
        if self.devSpine:
            return
        subCtrls = []
        # Create nearest point curve
        npc = pm.createNode("nearestPointOnCurve")
        # Connect the curve shape to input curve
        self.ikDriveCurve.worldSpace[0] >> npc.inputCurve

        # Initialise the groups that will stay at the base and metaise them
        subCtrlGrp = rideOnLocGrp = None

        for newGrp in ["subCtrlGrp", "rideOnLocGrp"]:
            newGrpMeta = core.MovableSystem(side=self.side, part=self.part, endSuffix=newGrp.capitalize())
            newGrpMeta.rotateOrder = self.rotateOrder
            self.addSupportNode(newGrpMeta, newGrp.capitalize())
            newGrpMeta.setParent(self.infoGrp)
            exec ("%s = newGrpMeta" % newGrp)

        # Iterate through all the control curve
        for i in range(self.ikDriveCurve.numCVs()):
            ikCV = self.ikCurve.pynode.cv[i]
            # Set the subpart name
            SubPart = "Sub%i" % i
            # Get the CV position
            joint = self.jointSystem.joints[i].pynode
            npc.inPosition.set(libUtilities.get_world_space_pos(joint))
            # Create a new control object
            subCtrl = self.createCtrlObj(SubPart, "Ball", False)
            subCtrls.append(subCtrl)
            # Add a ctrl locator
            subCtrl.addSpaceLocator(parent=True)
            subCtrl.locator.v = False
            # Create a helper space locator

            rideOnloc = core.SpaceLocator(part=SubPart, side=self.side, endSuffix="RideOnLocGrp")
            subCtrl.addSupportNode(rideOnloc, "RideOnLoc")
            rideOnloc.setParent(rideOnLocGrp)
            rideOnloc.v = False

            # Create the main motion path
            mp = pm.PyNode(pm.pathAnimation(rideOnloc.pynode,
                                            fractionMode=False,
                                            follow=True,
                                            curve=self.ikDriveCurve,
                                            upAxis=self.upAxis,
                                            worldUpType="objectrotation",
                                            worldUpVector=self.upVector,
                                            worldUpObject=self.pynode
                                            ))

            mpMeta = core.MetaRig(mp.name())
            mpMeta.part = SubPart
            subCtrl.addSupportNode(mpMeta, "MotionPath")
            subCtrl.transferPropertiesToChild(mpMeta, "MotionPath")
            mpMeta.resetName()

            mp.uValue.set(npc.parameter.get())
            pm.delete(mp.listConnections(type="animCurve"))

            # Control to the CV
            libUtilities.snap(rideOnloc.pynode, rideOnloc.pynode, rotate=False)

            # Apply a cheap point constraint
            libUtilities.cheap_point_constraint(rideOnloc.pynode, subCtrl.prnt.pynode)

            # Get the rotation value
            subCtrl.addConstraint(rideOnloc.pynode, "orient")

            # Connect the space locator to the IK Curve
            libUtilities.snap(subCtrl.locator.pynode, ikCV, rotate=False)
            libUtilities.cheap_point_constraint(subCtrl.locator.pynode, ikCV)

            # Lock the rotate and scale
            subCtrl.lockRotate()
            subCtrl.lockScale()
            # Add to parent
            subCtrl.prnt.setParent(subCtrlGrp)

        # Delete the nearest point on curve
        pm.delete(npc)
        # Append the control
        self.SubCtrls = subCtrls

        # Disable the cycle check warning
        pm.cycleCheck(e=False)

    @property
    def SubCtrls(self):
        return self.getChildren(asMeta=self.returnNodesAsMeta, walk=True, cAttrs=["SUP_SubCtrls"])

    @SubCtrls.setter
    def SubCtrls(self, ctrlList):
        if ctrlList is None:
            return
        self.connectChildren(ctrlList, "SubCtrls", allowIncest=True, cleanCurrent=True)

    @property
    def upVector(self):
        return [int(self.primaryAxis[2] == "x"),
                int(self.primaryAxis[2] == "y"),
                int(self.primaryAxis[2] == "z")]

    @property
    def forwardAxis(self):
        return str(self.primaryAxis)[0].upper()

    @property
    def upAxis(self):
        return str(self.primaryAxis)[2].upper()

    @property
    def ikSkin(self):
        return self.getSupportNode("IkSkin").pynode

    @property
    def ikSkinJoints(self):
        return self.ikSkin.influenceObjects()

    @property
    def ikDriveCurve(self):
        return self.controlCurve.pynode

    @property
    def driveJointSystem(self):
        return self.getSupportNode("DriveJointSystem")

    @driveJointSystem.setter
    def driveJointSystem(self, data):
        self.addSupportNode(data, "DriveJointSystem")

    @property
    def ikCurrentWeights(self):
        return list(self.ikSkin.getWeights(self.ikDriveCurve))


class HumanSpine(SubControlSpine):
    def buildControl(self):
        super(HumanSpine, self).buildControl()
        self.buildMainControls()

    def buildMainControls(self):
        # Build the first control at 0
        firstCtrl = self.createCtrlObj("%s1" % self.part)
        firstCtrl.lockScale()
        # Snap to position
        firstCtrl.snap(self.jointSystem.joints[0].mNode,
                       rotate=not self.ikControlToWorld)
        # Build the last control at last joint
        lastCtrl = self.createCtrlObj("%s3" % self.part)
        lastCtrl.lockScale()
        # Snap to position
        lastCtrl.snap(self.jointSystem.joints[-1].mNode,
                      rotate=not self.ikControlToWorld)
        # middle
        middleCtrl = self.createCtrlObj("%s2" % self.part)
        middleCtrl.lockScale()

        if (len(self.jointSystem) % 2):
            # Odd number
            middleCtrl.snap(self.jointSystem.joints[len(self.jointSystem) / 2].mNode,
                            rotate=not self.ikControlToWorld)
        else:
            middleJntA = self.jointSystem.joints[len(self.jointSystem) / 2].mNode
            middleJntB = self.jointSystem.joints[len(self.jointSystem) / 2 - 1].mNode
            # Align position
            middleCtrl.addConstraint(middleJntA, "point", False)
            middleCtrl.addConstraint(middleJntB, "point", False)
            if not self.ikControlToWorld:
                middleCtrl.addConstraint(middleJntA, "orient", False)
                middleCtrl.addConstraint(middleJntB, "orient", False)
            # Delete the constraints
            middleCtrl.pointConstraint.delete()
            middleCtrl.orientConstraint.delete()

        # Append the control
        self.mainCtrls = [firstCtrl, middleCtrl, lastCtrl]

    def connectTwist(self):
        self.ikHandle.rootTwistMode = True
        # Create plusMinusAverage which control the final twist
        twistPlusMinus = core.MetaRig(side=self.side,
                                      part="%sTwist" % self.part,
                                      endSuffix="PMA",
                                      nodeType="plusMinusAverage")
        twistPlusMinus.pynode.output1D >> self.ikHandle.pynode.twist

        # Create multiplyDivide which would counter twist for the top control
        multiplyDivide = core.MetaRig(side=self.side,
                                      part="%sCounterTwist" % self.part,
                                      endSuffix="MD",
                                      nodeType="multiplyDivide")
        multiplyDivide.input2X = -1

        # Connect the top control to the twist
        self.mainCtrls[2].getRotateDriver(self.forwardAxis) >> twistPlusMinus.pynode.input1D[0]

        # Connect to the bottom controller to the counter twist and roll
        self.mainCtrls[0].getRotateDriver(self.forwardAxis) >> multiplyDivide.pynode.input1X
        self.mainCtrls[0].getRotateDriver(self.forwardAxis) >> self.ikHandle.pynode.roll
        multiplyDivide.pynode.outputX >> twistPlusMinus.pynode.input1D[1]

        # Add PMA and MD as supprt node
        self.ikHandle.addSupportNode(twistPlusMinus, "Twist")
        self.ikHandle.addSupportNode(multiplyDivide, "CounterTwist")

    def connectTwistLegacy(self):
        # Setup the twist
        self.ikHandle.dTwistControlEnable = True
        self.ikHandle.rootTwistMode = True
        self.ikHandle.dWorldUpType = "Object Rotation Up (Start/End)"

        # Forward axis from the primary rotation
        self.ikHandle.dForwardAxis = "Positive %s" % self.forwardAxis
        # Some versions of Maya do that have this attribute
        if hasattr(self.ikHandle, "dWorldUpAxis"):
            # This may depend if it is positive or negative
            # Check the joint orient value
            self.ikHandle.dWorldUpAxis = "Positive %s" % self.upAxis

        # Control Vector. Might need negative for flipped
        self.ikHandle.dWorldUpVector = self.upVector
        self.ikHandle.dWorldUpVectorEnd = self.upVector

        # Set the two end controls as the main drivers for the twist
        self.mainCtrls[0].parentDriver.pynode.worldMatrix[0] >> self.ikHandle.pynode.dWorldUpMatrix
        self.mainCtrls[-1].parentDriver.pynode.worldMatrix[0] >> self.ikHandle.pynode.dWorldUpMatrixEnd

    @property
    def numHighLevelCtrls(self):
        # Make it in a read only attibute
        return 3

class ComplexSpine(SubControlSpine):
    def __init__(self, *args, **kwargs):
        super(ComplexSpine, self).__init__(*args, **kwargs)
        self.addAttr("twistMap", "")
        self.addAttr("prenormalisedTwistMap", [])

    def calculateIkSkinFallOff(self):
        super(ComplexSpine, self).calculateIkSkinFallOff()
        # Get prenormalised map
        self.twistMap = self.preNormalisedMap

    def buildHelperJoints(self):
        super(SubControlSpine, self).buildHelperJoints()

    @property
    def ikJointSystem(self):
        # The help joint system has the solver
        return self.helpJointSystem

    def buildControl(self):
        super(ComplexSpine, self).buildControl()
        self.buildMainControls()

    def reparentIkJoint(self):
        super(SubControlSpine, self).reparentIkJoint()

    def buildMainControls(self):
        # Get the ctrl postion
        ctrlPosition = utils.recalculatePosition(self.jointSystem.positions, self.numHighLevelCtrls)

        metaCtrls = []
        # Iterate though all the position
        for i in range(self.numHighLevelCtrls):
            # Create a control object
            ctrl = self.createCtrlObj("%s%i" % (self.part, i))
            # Set the position
            ctrl.prnt.translate = list(ctrlPosition[i])
            # Lock the scale
            ctrl.lockScale()
            metaCtrls.append(ctrl)

        # Is orientation set to world
        if not self.ikControlToWorld:
            # Get the closest joint position
            closestJoints = libMath.spread(0, len(self.jointSystem) - 1, self.numHighLevelCtrls)
            for jointPosition, i in zip(closestJoints, range(self.numHighLevelCtrls)):
                # Is a closest joint a fraction
                if jointPosition % 1:
                    # Orient between current and next
                    pm.delete(pm.orientConstraint(
                        self.jointSystem.jointList[int(jointPosition)],
                        self.jointSystem.jointList[int(jointPosition) + 1],
                        metaCtrls[i].prnt.pynode))
                else:
                    pm.delete(pm.orientConstraint(
                        self.jointSystem.jointList[int(jointPosition)],
                        metaCtrls[i].prnt.pynode))

        self.mainCtrls = metaCtrls

    def calculateTwistWeights(self):
        # If distance based falloff method then calculate the position based twist as that gives a better falloff
        # Calculate position based falloff
        self.positionFallOff(len(self.jointSystem) - 1, False)
        # Get the currentMap
        prenormalisedTwistMap = self.currentWeightMap

        # In case we want to lock the effect on the control like the tail start
        # Zero out the effect of the first ctrl on the last joint
        # prenormalisedTwistMap[0] = libMath.redistribute_value(prenormalisedTwistMap[0], -1)
        # Zero out the the effect of the last ctrl on the first joint
        # prenormalisedTwistMap[-1] = libMath.redistribute_value(prenormalisedTwistMap[-1], 0)

        # Transpose the weight
        self.prenormalisedTwistMap = map(list, zip(*prenormalisedTwistMap))

        # Normalise the weights
        normalisedTwist = []
        for weightMap in self.prenormalisedTwistMap:
            normalisedTwist.append(libMath.calculate_proportions(weightMap, 1))

        # Set the twistMap
        self.twistMap = normalisedTwist

    def connectTwist(self):
        self.calculateTwistWeights()

        # JointMeta
        def _get_joint_twist_average_(jointMeta, axis):
            pmaHelp = jointMeta.getSupportNode("rotateAverage")
            # If none are found
            if not pmaHelp:
                pmaHelp = core.MetaRig(side=self.side,
                                       part=jointMeta.part,
                                       endSuffix="RotateDriver",
                                       nodeType="plusMinusAverage")
                jointMeta.addSupportNode(pmaHelp, "rotateAverage")
                pmaHelp.pynode.attr("output3D%s" % axis.lower()) >> jointMeta.pynode.attr("rotate%s" % axis)

            currentConnect = pmaHelp.pynode.input3D.numConnectedElements()

            return pmaHelp.pynode.input3D[currentConnect].attr("input3D%s" % axis.lower())

        # Skiplist
        skipAxis = []
        for axis in ["x", "y", "z"]:
            if axis != self.primaryAxis[0]:
                skipAxis.append(axis)

        # Iterate through the weightMap/Joints
        for weightMap, joint in zip(self.twistMap, range(len(self.jointSystem) - 1)):
            # Do not add weight
            for singleWeight, ctrl in zip(weightMap, self.mainCtrls):
                if singleWeight != 0.0:
                    # Get the input PMA for the joint
                    rotateAverage = _get_joint_twist_average_(self.jointSystem.joints[joint], self.forwardAxis)

                    # Get Rotate Driver
                    rotateDriver = ctrl.getRotateDriver(self.forwardAxis)

                    # Create a Weight MD
                    weightManager = core.MetaRig(side=ctrl.side,
                                                 part="%s%s" % (self.jointSystem.joints[joint].part.capitalize(),
                                                                ctrl.part.capitalize()),
                                                 endSuffix="WeightManager%s" % self.forwardAxis,
                                                 nodeType="multiplyDivide")

                    # Add it as support node to joint
                    self.jointSystem.joints[joint].getSupportNode("rotateAverage").addSupportNode(weightManager,
                                                                                                  "WeightManage%s" % self.forwardAxis)

                    # Connect the Rotate Driver
                    rotateDriver >> weightManager.pynode.input1X

                    # Set the weight
                    weightManager.pynode.input2X.set(singleWeight)

                    # Connect to the rotateAverage
                    weightManager.pynode.outputX >> rotateAverage


if __name__ == '__main__':
    pm.newFile(f=1)

    mainSystem = core.TransSubSystem(side="C", part="Core")
    ikSystem = HumanSpine(side="L", part="Core")
    ikSystem.ikControlToWorld = False
    #ikSystem.numHighLevelCtrls = 5
    ikSystem.fallOffMethod = "Distance"
    # ikSystem.devSpine = True
    ikSystem.testBuild()

    mainSystem.addMetaSubSystem(ikSystem, "FK")
    ikSystem.convertSystemToSubSystem(ikSystem.systemType)


