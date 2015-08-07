__author__ = 'admin'
import pymel.core as pm
from pymel.internal.plogging import pymelLogger as pyLog

from PKD_Tools import libFile

reload(libFile)


def nameMe(partSfx, partName, endSuffix):
    """Set the name convention of all nodes"""
    if partSfx and partName and endSuffix:
        return "%s_%s_%s" % (partSfx, partName, endSuffix)


CTRLS_INFO_INFO = libFile.join(libFile.current_working_directory(), "Rigging/Data/Ctrl.json")


def export_ctrl_shapes():
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
    pyLog.info("Curve information written to: %s" % CTRLS_INFO_INFO)


def build_ctrl_shape(type=""):
    """Create a curve from the json"""
    curvesData = libFile.load_json(CTRLS_INFO_INFO)

    if curvesData.has_key(type):
        detailedInfo = curvesData[type]
        return pm.curve(name=type,
                        point=detailedInfo["cvs"],
                        per=detailedInfo["form"],
                        k=range(detailedInfo["knots"]),
                        degree=detailedInfo["degree"])

    else:
        pyLog.warning("%s not found in exported curve information file" % type)


def build_all_ctrls_shapes():
    """Build all curves from the json file"""
    curvesData = libFile.load_json(CTRLS_INFO_INFO)
    for crv in curvesData.keys():
        build_ctrl_shape(crv)


TEST_JOINTS_INFO = libFile.join(libFile.current_working_directory(), "Rigging/Data/Joints.json")


def save_test_joint(parentJoint, systemType):
    """
    @param parentJoint: the parent joint
    @param systemType: The test joint associated with the class
    """
    # joint -e  -oj yzx -secondaryAxisOrient zup -ch -zso;
    joint_info = {}
    if libFile.exists(TEST_JOINTS_INFO):
        joint_info = libFile.load_json(TEST_JOINTS_INFO)

    current_joint_data = []

    parentJoint = pm.PyNode(parentJoint)
    for joint in [parentJoint] + pm.listRelatives(parentJoint, ad=1, type="joint"):
        info = {"orient": list(joint.jointOrient.get()),
                "position": list(joint.getTranslation(space="world"))}
        current_joint_data.append(info)

    joint_info[systemType] = current_joint_data
    libFile.write_json(TEST_JOINTS_INFO, joint_info)


def create_test_joint(systemType):
    """
    @param parentJoint: the parent joint
    @param systemType: The test joint associated with the class
    joint -e -zso -oj yzx -sao zup joint1;
    """
    current_joint_data = libFile.load_json(TEST_JOINTS_INFO)["ik"]
    joints = []
    for joint, index in zip(current_joint_data, range(len(current_joint_data))):
        pm.select(cl=1)
        jnt = pm.joint(p=joint["position"])
        jnt.jointOrient.set(joint["orient"])
        if index:
            jnt.setParent(joints[index - 1])
        joints.append(jnt)
    return joints
