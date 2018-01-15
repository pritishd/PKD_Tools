"""
@package PKD_Tools.Rigging.spine
@brief Module which creates the three spine setup
"""

import operator

import pymel.core as pm

from PKD_Tools import libUtilities, libVector, libMath
from PKD_Tools.Rigging import core, joints, parts, utils
from PKD_Tools.libUtilities import output_window


# TODO: SubCtrl needs have their system so that we can navigate

class IkSpine(parts.Ik):
    """This is a Spline IK System"""

    def __init__(self, *args, **kwargs):
        super(IkSpine, self).__init__(*args, **kwargs)
        self.devSpine = False
        self.bSpline = True

    def buildHelperJoints(self):
        # Build the help joint system
        self.helpJointSystem = self.jointSystem.replicate(side=self.side, part="%sHelpJoints" % self.part,
                                                          supportType="Help")

    def buildDevSolver(self):
        self.buildSolver()

    def connectScale(self, attr):
        attr >> self.ctrlGrp.pynode.scale
        attr >> self.jointGrp.pynode.scale
        if self.stretchSystem:
            self.stretchSystem.connectGlobalScale(attr)

    def addStretch(self):
        super(IkSpine, self).addStretch()
        """
        arcMainNode = mc.rename(mc.arclen(IKCrvLenMain, ch=1), self.name + "_" + self.sfx + "_arcLenMain")
        mc.connectAttr(arcMainNode + ".arcLength", stMD + ".input2X")
        """
        arcLen = pm.arclen(self.mainCurve.pynode, constructionHistory=True)
        arcLenMeta = core.MetaRig(arcLen)
        arcLenMeta.part = self.part
        self.transferPropertiesToChild(arcLenMeta, "ArcLen")
        arcLenMeta.resetName()
        self.stretchSystem.setInitialValue(arcLenMeta.pynode.arcLength.get())
        self.stretchSystem.connectTrigger(arcLenMeta.pynode.arcLength)

        # Connect Stretch Joint
        self.connectStretchJoints()

        self.mainCtrls[0].addDivAttr("stretch", "strDiv")
        self.mainCtrls[0].addFloatAttr("Amount", sn="amount")
        amountAttr = self.mainCtrls[0].pynode.amount
        self.stretchSystem.connectAmount(amountAttr)
        amountAttr.set(1)

    def connectStretchJoints(self):
        scaleAxis = "s{}".format(self.twistAxis.lower())
        ikJoints = self.ikJointSystem.joints[1:(-1 - int(self.evaluateLastJointBool))]
        for joint in ikJoints:
            self.stretchSystem.connectOutput(joint.pynode.attr(scaleAxis))

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
        curve_name = utils.nameMe(self.side, self.part, "BaseCurve")
        # Sometimes bSpline might generate less CVs as the source....Investigate
        ikCurve, fitNode = pm.fitBspline(baseCurve,
                                         ch=1,
                                         tol=0.01,
                                         n=curve_name)
        if len(ikCurve.getCVs()) != len(jntSystem.positions):
            pm.delete(ikCurve)
            ikCurve = utils.createCurve(jntSystem.positions)
            ikCurve.rename(curve_name)
            self.bSpline = False
        self.ikCurve = core.MovableSystem(ikCurve.name())
        self.ikCurve.part = self.part
        self.transferPropertiesToChild(self.ikCurve, "BaseCurve")
        if self.bSpline:
            fitNodeMeta = core.MetaRig(fitNode.name())
            fitNodeMeta.part = self.part
            self.ikCurve.addSupportNode(fitNodeMeta, "BaseDriver")
            self.ikCurve.transferPropertiesToChild(fitNodeMeta, "FitNode")
            fitNodeMeta.resetName()
        # Build the spline IK
        name = utils.nameMe(self.side, self.part, "IkHandle")
        startJoint = jntSystem.joints[0].shortName()
        endJoint = jntSystem.joints[-1].shortName()
        # noinspection PyArgumentList
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
            self.buildDevSolver()
        else:
            self.buildSolver()
        # Reparent to the skin joint to the helper joint
        if self.helpJointSystem:
            # Reparent the main joints to the helperjoints
            for joint, helpJoint in zip(self.jointSystem.joints, self.helpJointSystem.joints):
                joint.setParent(helpJoint)

    def build(self):
        super(IkSpine, self).build()
        output_window("Building IK")
        self.build_ik()
        output_window("Building Controls")
        self.buildControl()
        output_window("Connecting Controls")
        self.connectToControl()
        output_window("Cleaning up")
        self.cleanUp()

    def buildControl(self):
        # Create the info group which does not translate
        infoGrp = core.NoInheritsTransform(side=self.side, part=self.part, endSuffix="InfGrp")
        # Reparent the info group
        infoGrp.setParent(self)
        # Set the main grp
        self.infoGrp = infoGrp

    def connectToControl(self):
        pass

    def reparentIkJoint(self, jointParent):
        targetJoint = self.helpJointSystem.joints[0]
        jointParent.snap(targetJoint)

        # Reparent the Joint
        targetJoint.setParent(jointParent)

    def cleanUp(self):
        # joint Grp
        jointGrp = core.MovableSystem(side=self.side, part=self.part, endSuffix="JointGrp")
        jointGrp.setParent(self)
        self.jointGrp = jointGrp
        # Reparent the Joint
        self.reparentIkJoint(jointGrp)
        # Reparent the two curve and ik Handle
        for crv in [self.ikCurve, self.controlCurve, self.ikHandle.prnt]:
            if crv:
                crv.setParent(self.infoGrp)
                crv.setParent(self.infoGrp)

        # Create the control grp
        mainCtrls = self.mainCtrls
        if mainCtrls:
            ctrlGrp = core.MovableSystem(side=self.side, part=self.part, endSuffix="MainCtrlGrp")
            ctrlGrp.rotateOrder = self.rotateOrder
            ctrlGrp.snap(mainCtrls[0])
            ctrlGrp.setParent(self)
            for ctrl in mainCtrls:
                ctrl.setParent(ctrlGrp)
            self.ctrlGrp = ctrlGrp

    @property
    def ikJointSystem(self):
        # Decide which joints has the solver
        return self.jointSystem

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
        key = "mainCtrls"
        if not self.metaCache.setdefault(key, None):
            self.metaCache[key] = self.getChildren(asMeta=self.returnNodesAsMeta,
                                                   walk=True,
                                                   cAttrs=["MainCtrls"])
        return self.metaCache[key]

    @mainCtrls.setter
    def mainCtrls(self, ctrlList):
        if not ctrlList:
            raise RuntimeError("Please input a list of meta Ctrls")
        self.connectChildren(ctrlList, "MainCtrls", allowIncest=True, cleanCurrent=True)
        self.metaCache["mainCtrls"] = ctrlList

    @property
    def helpJointSystem(self):
        return self.getSupportNode("HelpJointSystem")

    @helpJointSystem.setter
    def helpJointSystem(self, data):
        self.addSupportNode(data, "HelpJointSystem")

    @property
    def mainCurve(self):
        if self.bSpline:
            return self.controlCurve
        else:
            return self.ikCurve

    @property
    def jointGrp(self):
        return self.getSupportNode("JointGrp")

    @jointGrp.setter
    def jointGrp(self, data):
        self.addSupportNode(data, "JointGrp")


class SimpleSpine(IkSpine):
    def buildControl(self):
        super(SimpleSpine, self).buildControl()
        ctrls = []
        # TODO: Use enumarate
        for joint, pos in zip(self.jointSystem.jointData,
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
            if axis != self.twistAxis.lower():
                skipAxis.append(axis)
        controlCurve = self.mainCurve
        # Iterate through all the joints
        totalJoints = len(self.jointSystem)
        for pos in range(totalJoints):
            # Cluster the CV point on the control curve
            self.mainCtrls[pos].locator.clusterCV(controlCurve.pynode.cv[pos])

            # OrientConstraint the Joint
            kwargs = {"mo": True, "skip": skipAxis}

            # Lock the ends orientations
            if pos == totalJoints -1:
                del kwargs["skip"]

            self.jointSystem.joints[pos].addConstraint(self.mainCtrls[pos], 'orient', False, **kwargs)
            # pm.orientConstraint(self.mainCtrls[pos].parentDriver.pynode, self.jointSystem.joints[pos].pynode, mo=True,
            #                     skip=skipAxis)

    def cleanUp(self):
        super(SimpleSpine, self).cleanUp()
        if not self.bSpline:
            self.controlCurve.delete()

    @property
    def ikJointSystem(self):
        # The help joint systerm has the solver
        return self.helpJointSystem


# noinspection PyStatementEffect
class SubControlSpine(IkSpine):
    def __init__(self, *args, **kwargs):
        super(SubControlSpine, self).__init__(*args, **kwargs)
        # List of weights [CV][JOINT]
        self.fallOffMethod = kwargs.get("fallOffMethod", "Distance")
        self.currentWeightMap = []
        self.lockHead = kwargs.get("lockHead", False)
        self.lockTail = kwargs.get("lockTail", False)

    def __bindData__(self, *args, **kwgs):
        super(SubControlSpine, self).__bindData__(*args, **kwgs)
        self.addAttr("ikSkinWeightMap", "")
        self.addAttr("preNormalisedMap", "")
        self.addAttr("fallOffMethod", "")

    def reparentIkJoint(self, jointParent):
        targetJoint = self.jointSystem.joints[0]
        jointParent.snap(targetJoint)
        # Reparent the Joint
        targetJoint.setParent(jointParent)

    def buildHelperJoints(self):
        pass

    def buildSolver(self):
        # Make the default spline
        super(SubControlSpine, self).buildSolver()
        # Delete the history on the main curve
        pm.delete(self.ikCurve.mNode, constructionHistory=True)
        # Delete the shape under the Ik curve
        pm.delete(self.controlCurve.pynode.getShape())
        # Duplicate the smooth IKCurve
        tempCurve = pm.duplicate(self.ikCurve.mNode)[0]
        # Transfer the shape
        libUtilities.transfer_shape(tempCurve, self.ikDriveCurve)
        # Delete the temp node
        pm.delete(tempCurve)
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
        if not self.mainCtrls:
            self.breakpoint("No Main controls found")
        for ctrl in self.mainCtrls:
            # Create Joint and snap and parent to the control
            curveJoint = joints.Joint(side=ctrl.side, part=ctrl.part, endSuffix="CurveJoint")
            curveJoint.rotateOrder = self.rotateOrder
            curveJoint.snap(ctrl.mNode)
            ctrl.addChild(curveJoint.mNode)
            ctrl.addSupportNode(curveJoint, "IkSkinJoint")
            # Connect as support joint
            crvSkinJnts.append(curveJoint)
        crvJoints = [jnt.pynode for jnt in crvSkinJnts]

        skinCluster = libUtilities.skinGeo(self.ikDriveCurve, crvJoints)
        skinClusterMeta = core.MetaRig(skinCluster.name())
        skinClusterMeta.part = self.part
        self.addSupportNode(skinClusterMeta, "IkSkin")
        self.transferPropertiesToChild(skinClusterMeta, "IkSkin")
        skinClusterMeta.resetName()

        # Help Joint system
        self.driveJointSystem = joints.JointSystem(side=self.side, part="%sHelpJoints" % self.part)
        self.driveJointSystem.rigType = "Help"
        self.driveJointSystem.joints = crvSkinJnts
        self.driveJointSystem.rebuild_joint_data()

    def _calcPositionFallOff_(self, center, customNumJoints=None):
        """
        Calculate the falloff for the joints where the position becomes a new centre
        eg for the first position the weight will [1,.75,.25,0]
        for the second position the weights will [.5,1,.5,0]
        @return: The current position
        """

        if center < 1:
            raise ValueError('Centre must be positive')
        # Is there a overide of the joints
        if customNumJoints:
            numJoints = customNumJoints
        else:
            # Get the number of numJoints
            numJoints = float(len(self.jointSystem))

        # Init the weight list
        falloff = []
        # Will the fall off be mirrored if it goes beyond the centre
        mirrorFallOff = False
        if center / numJoints <= 0.5:
            center = (numJoints - center) + 1
            mirrorFallOff = True
        # Iterate thought all the numJoints
        for i in range(1, int(numJoints) + 1):
            val = round((center - (float(abs(center - i)))) / center, 3)

            falloff.append(round(val, 3))
        if mirrorFallOff:
            falloff.reverse()
        return falloff

    def positionFallOff(self, overrideNumJoints=None, transpose=True):
        if overrideNumJoints:
            numJoints = overrideNumJoints
        else:
            numJoints = float(len(self.jointSystem))
        spreadPosition = list(libMath.spread(1, numJoints, self.numHighLevelCtrls - 1))

        # Build [joint][CV] weightmap
        weightMap = []
        for sub in range(self.numHighLevelCtrls):
            weightMap.append(self._calcPositionFallOff_(spreadPosition[sub], overrideNumJoints))

        if transpose:
            # Transpose the weightmap to [CV][joint]
            self.currentWeightMap = libUtilities.transpose(weightMap)
        else:
            self.currentWeightMap = weightMap

    def distanceFallOff(self):
        weightMap = []
        # Zero out weights
        # zeroWeights = [1.0] + ([0] * (self.numHighLevelCtrls - 1))
        # Add to the first zero
        # self.currentWeightMap.append(list(zeroWeights))

        # For each CV calculate weights
        if len(self.jointSystem) != len(self.ikDriveCurve.getCVs()):
            self.breakpoint("Number of Joints and ikDrive CV do not match")
        else:
            for cv in range(len(self.jointSystem)):
                # Init the skinDataCV
                skinDataCV = []
                # Get the distance from CV
                for joint in range(self.numHighLevelCtrls):
                    jointPos = libUtilities.get_world_space_pos(self.ikSkinJoints[joint])
                    try:
                        skinDataCV.append(libVector.distanceBetween(jointPos, self.ikDriveCurve.getCVs()[cv]))
                    except IndexError:
                        print cv
                        print len(self.ikDriveCurve.getCVs())
                        raise IndexError

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
                if sum(newWeights):
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
        if not self.ikSkinWeightMap:
            self.calculateIkSkinFallOff()
            self.calculateHeatPoints()
        self.setIkWeights()

    def connectToControl(self):
        self.connectToMainControl()
        self.connectTwist()
        self.buildSubControls()

    def connectTwist(self):
        pass

    def buildSubControls(self):
        if self.devSpine:
            return
        subCtrls = []

        npc = libUtilities.create_npc_node(self.ikDriveCurve)

        # Initialise the groups that will stay at the base and metaise them
        subCtrlGrp = None

        for newGrp in ["subCtrlGrp", "rideOnLocGrp"]:
            newGrpMeta = core.MovableSystem(side=self.side, part=self.part, endSuffix=newGrp.capitalize())
            newGrpMeta.rotateOrder = self.rotateOrder
            self.addSupportNode(newGrpMeta, newGrp.capitalize())
            newGrpMeta.setParent(self.infoGrp)
            exec ("{} = newGrpMeta".format(newGrp))

        # Iterate through all the control curve
        for i in range(self.ikDriveCurve.numCVs()):
            ikCV = self.ikCurve.pynode.cv[i]
            # Set the subpart name
            SubPart = "{}Sub{}".format(self.part, i)
            # Get the CV position
            joint = self.jointSystem.joints[i].pynode
            npc.inPosition.set(libUtilities.get_world_space_pos(joint))

            # Create a new control object
            subCtrl = self.createCtrlObj(SubPart, shape="Ball", createXtra=False, addGimbal=False)
            subCtrls.append(subCtrl)
            # Add a ctrl locator
            subCtrl.addSpaceLocator(parent=True)
            subCtrl.locator.v = False
            subCtrl.addZeroPrnt()

            # Create the point on curve node
            poc = core.MetaRig(part=SubPart, side=self.side, endSuffix="POC", nodeType="pointOnCurveInfo")
            subCtrl.addSupportNode(poc, "PointOnCurve")
            poc.parameter = npc.parameter.get()

            self.ikDriveCurve.worldSpace >> poc.pynode.inputCurve

            poc.pynode.position >> subCtrl.zeroPrnt.pynode.translate

            # Control to the CV
            subCtrl.zeroPrnt.snap(self.jointSystem.joints[i], True, False)
            subCtrl.prnt.snap(self.jointSystem.joints[i], False)
            # # Apply a cheap point constraint
            # libUtilities.cheap_point_constraint(rideOnloc.pynode, subCtrl.zeroPrnt.pynode)

            # Connect the space locator to the IK Curve
            libUtilities.snap(subCtrl.locator.pynode, ikCV, rotate=False)
            libUtilities.cheap_point_constraint(subCtrl.locator.pynode, ikCV)

            # Lock the rotate and scale
            subCtrl.lockRotate()
            subCtrl.lockScale()
            # Add to parent
            subCtrl.setParent(subCtrlGrp)


        # Delete the nearest point on curve
        pm.delete(npc)
        # Append the control
        self.subCtrls = subCtrls

    def cleanUp(self):
        super(SubControlSpine, self).cleanUp()
        self.controlCurve.v = False
        self.ikCurve.overrideEnabled = True
        self.ikCurve.overrideDisplayType = 2

    @property
    def subCtrls(self):
        key = "subCtrls"
        if not self.metaCache.setdefault(key, None):
            self.metaCache[key] = self.getChildren(asMeta=self.returnNodesAsMeta,
                                                   walk=True,
                                                   cAttrs=[libUtilities.capitalize(key)])
        return self.metaCache[key]

    @subCtrls.setter
    def subCtrls(self, ctrlList):
        if ctrlList is None:
            return
        self.connectChildren(ctrlList, "SubCtrls", allowIncest=True, cleanCurrent=True)
        self.metaCache["subCtrls"] = ctrlList

    @property
    def allCtrls(self):
        key = "allCtrls"
        if not self.metaCache.setdefault(key, None):
            self.metaCache[key] = self.getChildren(asMeta=True,
                                                   walk=True,
                                                   cAttrs=["MainCtrls", '%s_*' % self.CTRL_Prefix, "SubCtrls"])
        return self.metaCache[key]

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


# noinspection PyStatementEffect
class HumanSpine(SubControlSpine):
    def __init__(self, *args, **kwargs):
        super(HumanSpine, self).__init__(*args, **kwargs)

    def build(self):
        super(HumanSpine, self).build()
        output_window("Locking {} Start and End Joints".format(self.part))
        self.lockTailHead()

    def lockTailHead(self):
        firstLastGetter = operator.itemgetter(0, -1)
        jointData = firstLastGetter(self.jointSystem.jointData)
        originalNames = []
        for data in jointData:
            originalNames.append(data["Name"])
            data["Name"] = "{}Help".format(data["Name"])
        helper = joints.JointSystem(side=self.side, part="HelperJoints")
        helper.jointData = jointData
        helper.gimbalData = self.jointSystem.gimbalData
        helper.build()

        # Align and orient constraints to the control
        for helpJoint, joint, ctrl in zip(helper.joints, firstLastGetter(self.jointSystem.joints),
                                          firstLastGetter(self.mainCtrls)):
            helpJoint.snap(joint)
            helpJoint.setParent(joint)
            skipAxis = [self.twistAxis.lower()]
            helpJoint.addConstraint(ctrl.parentDriver, "orient", mo=True, skip=skipAxis)

        # Fix the name
        helpJoints = helper.joints
        for name, joint in zip(originalNames, helpJoints):
            joint.rigType = "HelpJoint"
            joint.part = name
            joint.resetName()

        helper.joints = [helpJoints[0]] + self.jointSystem.joints[1:-1] + [helpJoints[-1]]
        self.helpJointSystem = helper

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
            middleCtrl.addConstraint(middleJntA, "point", mo=False)
            middleCtrl.addConstraint(middleJntB, "point", mo=False)
            if not self.ikControlToWorld:
                middleCtrl.addConstraint(middleJntA, "orient", mo=False)
                middleCtrl.addConstraint(middleJntB, "orient", mo=False)
            # Delete the constraints
            middleCtrl.pointConstraint.delete()
            middleCtrl.orientConstraint.delete()

        # Append the control
        self.mainCtrls = [firstCtrl, middleCtrl, lastCtrl]

    def connectTwist(self):
        # Create plusMinusAverage which control the final twist
        twistPlusMinus = core.MetaRig(side=self.side,
                                      part="%sTwist" % self.part,
                                      endSuffix="PMA",
                                      nodeType="plusMinusAverage")

        # Create multiplyDivide which would counter twist for the top control
        multiplyDivide = core.MetaRig(side=self.side,
                                      part="%sCounterTwist" % self.part,
                                      endSuffix="MD",
                                      nodeType="multiplyDivide")
        multiplyDivide.input2X = -1

        if self.mirrorBehaviour:
            # This will add one extra MD. So just keep it for now
            self.mainCtrls[0].addCounterTwist()
            self.mainCtrls[2].addCounterTwist()

        # Connect the top control to the twist
        self.mainCtrls[2].getTwistDriver(self.twistAxis) >> twistPlusMinus.pynode.input1D[0]

        # Connect to the bottom controller to the counter twist and roll
        self.mainCtrls[0].getTwistDriver(self.twistAxis) >> multiplyDivide.pynode.input1X
        multiplyDivide.pynode.outputX >> twistPlusMinus.pynode.input1D[1]

        # Connect IK Handle twist and roll
        twistPlusMinus.pynode.output1D >> self.ikHandle.pynode.twist
        self.mainCtrls[0].getTwistDriver(self.twistAxis) >> self.ikHandle.pynode.roll

        # Add PMA and MD as supprt node
        self.ikHandle.rootTwistMode = True
        self.ikHandle.addSupportNode(twistPlusMinus, "Twist")
        self.ikHandle.addSupportNode(multiplyDivide, "CounterTwist")

    def connectTwistLegacy(self):
        # Setup the twist
        self.ikHandle.dTwistControlEnable = True
        self.ikHandle.rootTwistMode = True
        self.ikHandle.dWorldUpType = "Object Rotation Up (Start/End)"

        # Forward axis from the primary rotation
        self.ikHandle.dForwardAxis = "Positive %s" % self.twistAxis
        # Some versions of Maya do that have this attribute
        if hasattr(self.ikHandle, "dWorldUpAxis"):
            # This may depend if it is positive or negative
            # Check the joint orient value
            self.ikHandle.dWorldUpAxis = "Positive %s" % self.rollAxis

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

    @property
    def parenterJointSystem(self):
        return self.helpJointSystem


class ComplexSpine(SubControlSpine):
    def __init__(self, *args, **kwargs):
        super(ComplexSpine, self).__init__(*args, **kwargs)
        self.numHighLevelCtrls = kwargs.get("numHighLevelCtrls", 3)
        self._evaluateLastJoint = kwargs.get("evaluateLastJoint", False)

    def __bindData__(self, *args, **kwgs):
        super(ComplexSpine, self).__bindData__(*args, **kwgs)
        self.addAttr("twistMap", [])
        self.addAttr("prenormalisedTwistMap", [])

    def calculateIkSkinFallOff(self):
        super(ComplexSpine, self).calculateIkSkinFallOff()
        # Get prenormalised map
        self.twistMap = self.preNormalisedMap

    def buildHelperJoints(self):
        super(SubControlSpine, self).buildHelperJoints()

    def buildControl(self):
        super(ComplexSpine, self).buildControl()
        self.buildMainControls()

    def reparentIkJoint(self, jointParent):
        super(SubControlSpine, self).reparentIkJoint(jointParent)

    def buildMainControls(self):
        # Get the ctrl postion
        ctrlPosition = utils.recalculatePosition(self.jointSystem.positions, self.numHighLevelCtrls)
        metaCtrls = []
        # Iterate though all the position
        for i in range(self.numHighLevelCtrls):
            output_window("Build Main Control: {}".format(i))
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
        if not self.twistMap:
            # Position based twist as that gives the best falloff so far
            numJoints = len(self.jointSystem) - int(self.evaluateLastJointBool) - int(self.lockHead) - int(
                self.lockTail)
            self.positionFallOff(numJoints, False)

            # Get the currentMap
            prenormalisedTwistMap = self.currentWeightMap

            newRotate = prenormalisedTwistMap[0:1]
            # Zeroout the eggect
            newRotate[0] = libMath.redistribute_value(newRotate[0], -1)
            start = int(not self.lockHead)
            for rotationMap in prenormalisedTwistMap[1:-1]:
                rotationMap = libMath.redistribute_value(rotationMap, 0)
                rotationMap = libMath.redistribute_value(rotationMap, -1)
                newRotate.append(rotationMap)

            newRotate.append(prenormalisedTwistMap[-1])

            newRotate[-1] = libMath.redistribute_value(newRotate[-1], 0)
            # In case we want to lock the effect on the control like the tail start
            # Zero out the effect of the first ctrl on the last joint
            # prenormalisedTwistMap[0] = libMath.redistribute_value(prenormalisedTwistMap[0], -1)
            # Zero out the the effect of the last ctrl on the first joint
            # prenormalisedTwistMap[-1] = libMath.redistribute_value(prenormalisedTwistMap[-1], 0)

            # Transpose the weight
            self.prenormalisedTwistMap = libUtilities.transpose(newRotate)

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
                                       endSuffix="RotateAverage",
                                       nodeType="plusMinusAverage")
                jointMeta.addSupportNode(pmaHelp, "rotateAverage")
                pmaHelp.pynode.attr("output3D%s" % axis.lower()) >> jointMeta.pynode.attr("rotate%s" % axis.upper())

            currentConnect = pmaHelp.pynode.input3D.numConnectedElements()

            return pmaHelp.pynode.input3D[currentConnect].attr("input3D%s" % axis.lower())

        # Skiplist
        # skipAxis = [self.rollAxis, self.bendAxis]
        # for axis in ["x", "y", "z"]:
        #     if axis != self.primaryAxis[0]:
        #         skipAxis.append(axis)

        # Iterate through the weightMap/Joints
        for weightMap, joint in zip(self.twistMap, range(len(self.jointSystem) - int(self.evaluateLastJointBool))):
            # Do not add weight
            for singleWeight, ctrl in zip(weightMap, self.mainCtrls):
                if singleWeight == 1:
                    rotateDriver = ctrl.getRotateDriver(self.twistAxis)
                    rotateDriver >> self.jointSystem.joints[joint].pynode.attr("rotate%s" % self.twistAxis.upper())
                elif singleWeight != 0.0:
                    # Get the input PMA for the joint
                    rotateAverage = _get_joint_twist_average_(self.jointSystem.joints[joint], self.twistAxis)

                    # Get Rotate Driver
                    rotateDriver = ctrl.getRotateDriver(self.twistAxis)

                    wm_name = "WeightManager{}".format(self.twistAxis)
                    # Create a Weight MD
                    weightManager = core.MetaRig(side=ctrl.side,
                                                 part="{0}{1}".format(self.jointSystem.joints[joint].part.capitalize(),
                                                                      ctrl.part.capitalize()),
                                                 endSuffix=wm_name,
                                                 nodeType="multiplyDivide")

                    # Add it as support node to joint
                    self.jointSystem.joints[joint].getSupportNode("rotateAverage").addSupportNode(
                        weightManager, wm_name)

                    # Connect the Rotate Driver
                    rotateDriver >> weightManager.pynode.input1X

                    # Set the weight
                    weightManager.pynode.input2X.set(singleWeight)

                    # Connect to the rotateAverage
                    weightManager.pynode.outputX >> rotateAverage

    @property
    def ikJointSystem(self):
        # The help joint system has the solver
        return self.helpJointSystem


core.Red9_Meta.registerMClassInheritanceMapping()
core.Red9_Meta.registerMClassNodeMapping(nodeTypes=['pointOnCurveInfo'])


if __name__ == '__main__':
    pm.newFile(f=1)
    # mainSystem = core.TransSubSystem(side="C", part="Core")
    # ikSystem = HumanSpine(side="L", part="Core", numHighLevelCtrls=5, fallOffMethod="Position")
    ikSystem = HumanSpine(side="L", part="Core")
    ikSystem.ikControlToWorld = True
    #ikSystem.devSpine = True
    ikSystem.isStretchable = True
    ikSystem.testBuild()
    ikSystem.addStretch()

    # mainSystem.addMetaSubSystem(ikSystem, "FK")
    # ikSystem.convertSystemToSubSystem(ikSystem.systemType)
