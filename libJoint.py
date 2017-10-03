# coding=utf-8
"""
@package PKD_Tools.libJoint
This package contains joint orientation based tools
"""
import libUtilities

reload(libUtilities)
import pymel.core as pm
from maya import cmds


def _get_joint_orient_info():
    """Internal function to retrieve the ideal settings for the joint orient function.
    @return: Tuple of dictionary.
    """
    detailed_info = dict()
    reverse_lookup = dict()

    # up forward
    detailed_info["yzx"] = {"Pitch/Bend Forward": "X",
                            "Yaw/Twist": "Y",
                            "Forward": "Z",
                            "Up": "Y"}
    reverse_lookup["yz"] = "yzx"
    detailed_info["yxz"] = {"Pitch/Bend Forward": "Z",
                            "Yaw/Twist": "Y",
                            "Forward": "X",
                            "Up": "Y"}
    reverse_lookup["yx"] = "yxz"
    detailed_info["xyz"] = {"Pitch/Bend Forward": "Y",
                            "Yaw/Twist": "X",
                            "Forward": "Z",
                            "Up": "X"}
    reverse_lookup["xz"] = "xyz"
    detailed_info["xzy"] = {"Pitch/Bend Forward": "Z",
                            "Yaw/Twist": "X",
                            "Forward": "Y",
                            "Up": "X"}
    reverse_lookup["xy"] = "xzy"
    detailed_info["zyx"] = {"Pitch/Bend Forward": "X",
                            "Yaw/Twist": "Z",
                            "Forward": "Y",
                            "Up": "Z"}
    reverse_lookup["zy"] = "zyx"
    detailed_info["zxy"] = {"Pitch/Bend Forward": "Y",
                            "Yaw/Twist": "Z",
                            "Forward": "X",
                            "Up": "Z"}
    reverse_lookup["zx"] = "zxy"

    rotate_secondary_axis = {'yzx': 'zup', 'yxz': 'zup', 'xyz': 'xup', 'xzy': 'xup', 'zyx': 'yup', 'zxy': 'yup'}

    return reverse_lookup, rotate_secondary_axis, detailed_info


def get_joint_children(joint):
    """
    Return all the descendants in a hierarchical order
    @param joint: (str/pynode) The target joint
    @return: List of pynode of children
    """
    joint = str(joint)
    return libUtilities.pyList(sorted(cmds.listRelatives(joint, allDescendents=True, fullPath=True) or []))


def set_rotate_order(rotate_order, joint_list=None):
    """
    Set the rotate order for the list of joints
    @param rotate_order: 
    @param joint_list: 
    """
    if not joint_list:
        selection = pm.selected()
        if selection:
            joint_list = selection[0] + get_joint_children(selection[0])
        else:
            raise RuntimeError("Joint list not defined and nothing is selected")
    # Set the rotate order
    for joint in joint_list:
        if joint.rotateOrder.get(asString=True) != rotate_order:
            joint.rotateOrder.set(rotate_order)


def orient_joint(**kwargs):
    """
    Orient the joint
    @param kwargs: Takes the following keyword arguments
                    - joint (node): the node which will be process. It picks up the default node by default
                    - up (str): in which direction do move up and down the joint
                    - forward (str): in which direction do you want to move it forward/back
                    - flip_forward (bool): whether the joint forward direction will be reversed
                    - flip up (bool): whether the joint up and down will be reversed
                    - details (bool)
    @return the rotate order
    """
    # Get all the keyword arguements
    selection = pm.selected() or []
    try:
        target_joint = libUtilities.force_pynode(kwargs.get("joint") or pm.selected()[0])
    except IndexError:
        pm.confirmDialog(title="User Error",
                         message="{: <22}".format("Please select a joint"),
                         icon="critical")
        return
    up = kwargs.get("up", "y").lower()
    forward = kwargs.get("forward", "z").lower()
    flip_forward = kwargs.get("flip_forward", False)
    flip_up = kwargs.get("flip_up", False)
    details = kwargs.get("details", False)

    # Get the preferred rotation axis
    prefered_axis = "{}{}".format(up, forward)

    # Get the joint mapping data
    reverse_lookup, rotate_secondary_axis, detailed_info = _get_joint_orient_info()
    rotate_order = reverse_lookup[prefered_axis]
    pm.undoInfo(openChunk=True)
    children_joints = get_joint_children(target_joint)
    libUtilities.freeze_rotation([target_joint] + children_joints)
    libUtilities.freeze_scale([target_joint] + children_joints)
    secondary_orient = rotate_secondary_axis[rotate_order]
    if children_joints:
        if flip_forward:
            secondary_orient = secondary_orient.replace("up", "down")
        pm.joint(target_joint,
                 edit=True,
                 zeroScaleOrient=True,
                 children=True,
                 orientJoint=rotate_order,
                 secondaryAxisOrient=secondary_orient)

        if flip_up:
            joints = [target_joint]
            if len(children_joints) > 1:
                joints = reversed(joints + children_joints[:-1])
            for flip_joint in joints:
                childJoint = pm.listRelatives(flip_joint)[0]
                childJoint.setParent(world=True)
                flip_joint.attr('r{}'.format(forward)).set(180)
                libUtilities.freeze_rotation([flip_joint])
                libUtilities.freeze_scale([flip_joint])
                childJoint.setParent(flip_joint)
        children_joints[-1].jointOrient.set(0, 0, 0)

        if details:
            for key in ["Pitch/Bend Forward", "Yaw/Twist", "Forward", "Up"]:
                print "{} : {}".format(key, detailed_info[rotate_order][key])
            if flip_up:
                print "The joint chain was flipped up in the end"
        pm.select(selection)

    all_joints = [target_joint] + children_joints

    # Calculate the last axis to resolves
    last_axis = (set("xyz") - set(prefered_axis)).pop()
    preferred_rotate_order = "{}{}{}".format(last_axis, forward, up)

    # Set the rotate order
    set_rotate_order(preferred_rotate_order, all_joints)
    pm.undoInfo(closeChunk=True)
    return preferred_rotate_order


def zero_out_bend(**kwargs):
    """
    Zero out all the bend joint
    Here we assume it already has a optimised rotate order
        - joint_list: (list) List of joint to zero out te bend
        - axis: (str) Which axis is the joint bending
        - rotate_order: (str) What is the current rotate order
    @return the rotate order
    """
    joint_list = libUtilities.pyList(kwargs.get("joint_list") or get_joint_children(pm.selected()[0]))
    libUtilities.freeze_rotation(joint_list)
    libUtilities.freeze_scale(joint_list)
    rotate_order = kwargs.get("rotate_order") or joint_list[0].rotateOrder.get(asString=True)
    target_axis = kwargs.get("axis", rotate_order[0])
    new_rotate_order = None
    if target_axis != rotate_order[0]:
        new_rotate_order = "{}{}{}".format(target_axis, rotate_order[0], rotate_order[2])
    pm.undoInfo(openChunk=True)
    for joint in joint_list:
        for rotate_axis in rotate_order:
            if rotate_axis != target_axis:
                joint.attr("jointOrient{}".format(rotate_axis.upper())).set(0)
        if new_rotate_order:
            joint.rotateOrder.set(new_rotate_order)
    pm.undoInfo(closeChunk=True)
    return new_rotate_order


def get_gimbal_data(rotate_order):
    """
    Get detail information about the gimbal data based on the current rotate order
    @param rotate_order: (str) The current rotate order
    @return: dict of gimbal data
    """
    return {"bend": rotate_order[0], "roll": rotate_order[1], "twist": rotate_order[2]}


def get_rotate_order(gimbal_data):
    """
    Based on the gimbal generate the rotate order. Here we can decide whether the Gimbal will be on the twist or 
    on the roll
    @param gimbal_data: dict which defines what axis are on the bend, roll and twist. Also defines where the 
        gimbal will reside
    @return: The rotate order*
    """
    if gimbal_data["gimbal"] == "roll":
        return '{}{}{}'.format(gimbal_data["bend"], gimbal_data["roll"], gimbal_data["twist"])
    elif gimbal_data["gimbal"] == "twist":
        return '{}{}{}'.format(gimbal_data["bend"], gimbal_data["twist"], gimbal_data["roll"])


def freeze_rotation(joint):
    """
    Freeze the rotation and scale on the joint chain
    @param joint: The target joint
    """
    joint_list = [joint] + get_joint_children(joint)
    libUtilities.freeze_scale(joint_list)
    libUtilities.freeze_rotation(joint_list)


def default_gimbal_data():
    """
    @return: (dict) Gimbal settings data for joint created at origin
    """
    return {"twist": "y", "bend": "x", "roll": "z", 'gimbal': 'roll', 'flip_forward': False, 'flip_up': False}
