"""
@package PKD_Tools.Rigging.utils
@brief Basic rigging based utilty functions
"""

import pymel.core as pm
from PKD_Tools import logger

from PKD_Tools import libFile, libUtilities, libMath

# if __name__ == '__main__':
#     for module in libFile, libUtilities, libMath:
#         reload(module)

CTRLS_INFO_INFO = libFile.join(libFile.current_working_directory(), "Rigging/Data/Ctrl.json")


def nameMe(partSfx, partName, endSuffix):
    """Set the name convention of all nodes eg L_Main_Ctrl"""
    if partSfx and partName and endSuffix:
        return "%s_%s_%s" % (partSfx, partName, endSuffix)


def exportCrlShapes():
    """Export curve data from the existing curve to a json file"""
    curvesData = {}
    for top in pm.ls(assemblies=True, ud=True):
        if top.getShape().type() == "nurbsCurve":
            detailedInfo = {"cvs": [list(cv) for cv in top.getCVs()],
                            "form": top.f.get(),
                            "degree": top.degree(),
                            "knots": top.numKnots()}
            curvesData[top.name()] = detailedInfo

    libFile.write_json(CTRLS_INFO_INFO, curvesData)
    logger.info("Curve information written to: %s" % CTRLS_INFO_INFO)


def buildCtrlShape(type=""):
    """Create a curve from the json file"""
    curvesData = libFile.load_json(CTRLS_INFO_INFO)

    if curvesData.has_key(type):
        detailedInfo = curvesData[type]
        return pm.curve(name=type,
                        point=detailedInfo["cvs"],
                        per=detailedInfo["form"],
                        k=range(detailedInfo["knots"]),
                        degree=detailedInfo["degree"])

    else:
        logger.error("%s not found in exported curve information file" % type)


def buildAllCtrlsShapes():
    """Build all curves from the json file"""
    curvesData = libFile.load_json(CTRLS_INFO_INFO)
    for crv in curvesData.keys():
        buildCtrlShape(crv)


TEST_JOINTS_INFO = libFile.join(libFile.current_working_directory(), "Rigging/Data/Joints.json")


def saveTestJoint(parentJoint, systemType):
    """
    @param parentJoint: the parent joint
    @param systemType: The test joint associated with the class
    """
    # joint -e  -oj yzx -secondaryAxisOrient zup -ch -zso;
    joint_info = {}
    if libFile.exists(TEST_JOINTS_INFO):
        joint_info = libFile.load_json(TEST_JOINTS_INFO)

    currentJointData = []

    parentJoint = pm.PyNode(parentJoint)

    childJoints = parentJoint.listRelatives(ad=1, type="joint")
    childJoints.reverse()
    childJoints.insert(0, parentJoint)

    for joint in childJoints:
        if not joint.getChildren():
            joint.jointOrient.set(0, 0, 0)
        parent = joint.getParent()
        pm.makeIdentity(joint, normal=False, scale=False, rotate=True,
                        translate=False, apply=True, preserveNormals=True)
        joint.setParent(w=1)
        info = {"name": joint.shortName(),
                "orient": list(joint.jointOrient.get()),
                "position": list(joint.getTranslation(space="world"))}
        currentJointData.append(info)
        if parent:
            joint.setParent(parent)

    joint_info[systemType] = currentJointData

    libFile.write_json(TEST_JOINTS_INFO, joint_info)


def createTestJoint(systemType):
    """
    @param systemType: The test joint associated with the class;
    """
    current_joint_data = libFile.load_json(TEST_JOINTS_INFO)[systemType]
    testJoints = []
    for joint, index in zip(current_joint_data, range(len(current_joint_data))):
        pm.select(cl=1)
        jnt = pm.joint(name=joint["name"], p=joint["position"])
        jnt.jointOrient.set(joint["orient"])
        if index:
            jnt.setParent(testJoints[index - 1])
        testJoints.append(jnt)
    return testJoints


def orientJoint(target):
    """Convenience function to orient the joint"""
    pm.joint(target, zso=1, ch=1, e=1, oj='yxz', secondaryAxisOrient='yup')


def createCurve(positions=[], degree=2):
    """
    @param positions: Point positions
    @param degree: The degree of the curve that should be
    @return: The curve pynode
    """
    if len(positions) < degree:
        # Force the degree to least number of points required
        degree = min(degree - 1, len(positions) - 1)
    curve = pm.curve(d=degree, p=positions[0])
    for i in range(1, len(positions)):
        pm.curve(curve, a=1, p=positions[i])
    return curve


def recalculatePosition(currentPositions, newNumberPositions, degree=2):
    """
    For a given set of position create a curve and return fewer/more a set of position that follow on that arc.
    @param currentPositions: Current list of cv position
    @param newNumberPositions: How many CV points do me require
    @param degree: What degree should be on the created curve
    @return: list of new cv positions
    """
    if len(currentPositions) < 4:
        crv = createCurve(currentPositions, 1)
    else:
        crv = createCurve(currentPositions, degree)

    newPositions = []

    pm.cycleCheck(e=False)

    for posOnCurve in libMath.spread(0, 1, newNumberPositions - 1):
        pm.select(clear=True)
        tempDag = pm.joint()
        mp = pm.PyNode(pm.pathAnimation(tempDag,
                                        fractionMode=True,
                                        follow=False,
                                        curve=crv
                                        ))
        pm.delete(mp.listConnections(type="animCurve"))
        mp.uValue.set(posOnCurve)
        newPositions.append(libUtilities.get_world_space_pos(tempDag))
        pm.delete([mp, tempDag])

    pm.delete(crv)
    return newPositions

def getCVInfo(allCtrls):
    """Generate a dictionary of Control and it's CV positions
    @param allCtrls: The current list of controls
    @return: dictionary of ctrl name and their position
    """
    ctrlInfo = {}
    for ctrl in allCtrls:
        ctrl = pm.PyNode(ctrl)
        ctrlInfo[ctrl.name()] = [list(cv) for cv in ctrl.getCVs(space="object")]
    return ctrlInfo


def setCVInfo(ctrlInfo):
    """Restore CV shapes based on the list of name and position dictionary
    @param ctrlInfo: list of dictionary with name of the node and positions of
        CVs
    """
    for ctrl in ctrlInfo:
        if pm.objExists(ctrl):
            CVs = ctrlInfo[ctrl]
            ctrl = pm.PyNode(ctrl)
            ctrl.setCVs(CVs, space="object")
            pm.cluster(ctrl)
            pm.delete(ctrl, constructionHistory = True)


if __name__ == '__main__':
    pass
    pm.newFile(f=1)
    buildAllCtrlsShapes()
    # current_joint_data = libFile.load_json(TEST_JOINTS_INFO)
    # print libFile.load_json(TEST_JOINTS_INFO).keys()
    # create_test_joint('Generic')
    # a = [u'hip',
    #      u'hipHoof',
    #      u'armHand',
    #      u'quadHoof',
    #      u'hipFoot',
    #      u'armFoot',
    #      u'ik2jnt',
    #      u'quadHand',
    #      u'armHoof',
    #      u'ik',
    #      u'quadFoot',
    #      u'quad',
    #      u'hipHand',
    #      u'quadPaw',
    #      u'arm']
    # save_test_joint("Clavicle", "armPaw")
    # save_test_joint("Clavicle", "armFoot")
    # save_test_joint("Spine01", "simpleSpine")
    # save_test_joint("Spine01", "ikSpline")
    # save_test_joint("Tail1", "Generic")

    # print libFile.load_json(TEST_JOINTS_INFO).keys()
    # myDict['hipHand'] = myDict.pop('hipArm')
    # myDict = libFile.load_json(TEST_JOINTS_INFO)
    # pos = [[0, 0, 0],
    #        [1, 1, 1],
    #        [2, 2, 2],
    #        [3, 3, 3]
    #        ]
    #
    # create_curve(pos,3)
    # build_all_ctrls_shapes()
    # export_ctrl_shapes()
    # pos = [[-4.930380657631324e-32, 0.0, 0.0],
    #  [-3.330669073875469e-16, 2.9527150925478933, -0.530540839370425],
    #  [-1.6232498099730929e-15, 5.935049728765758, -0.85562562464247],
    #  [-3.2379038868515876e-15, 8.932725316345454, -0.9736979398934958],
    #  [-5.181841149764807e-15, 11.931389814752379, -0.8841924875771195],
    #  [-7.463206577640404e-15, 14.91668644882051, -0.587537795011321],
    #  [-9.731770252717657e-15, 17.874322445016354, -0.08515416270832554]]
    # create_curve(pos, 1)
