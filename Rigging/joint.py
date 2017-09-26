# Put all the joint API here. Maybe this is Util


# @cond DOXYGEN_SHOULD_SKIP_THIS
__author__ = 'pritish.dogra'

# pm.joint(zso=1, ch=1, e=1, oj='yzx', secondaryAxisOrient='ydown')
# pm.joint(zso=1, ch=1, e=1, oj='yzx', secondaryAxisOrient='yup')

# pm.joint(zso=1, ch=1, e=1, oj='yxz', secondaryAxisOrient='ydown')
# pm.joint(zso=1, ch=1, e=1, oj='yxz', secondaryAxisOrient='yup')


# l = pm.PyNode("joint8")

# pm.selected()[0].rotateOrder.set("zxy")


# @endcond

from collections import OrderedDict

detailedInfo = dict()
detailedInfo["yzx"] = {"Pitch/Bend Forward": "X",
                       "Yaw/Twist": "Y",
                       "Forward": "Z",
                       "Up": "Y"}
detailedInfo["yxz"] = {"Pitch/Bend Forward": "Z",
                       "Yaw/Twist": "Y",
                       "Forward": "X",
                       "Up": "Y"}
detailedInfo["xyz"] = {"Pitch/Bend Forward": "Y",
                       "Yaw/Twist": "X",
                       "Forward": "Z",
                       "Up": "X"}
detailedInfo["xzy"] = {"Pitch/Bend Forward": "Z",
                       "Yaw/Twist": "X",
                       "Forward": "Y",
                       "Up": "X"}
detailedInfo["zyx"] = {"Pitch/Bend Forward": "X",
                       "Yaw/Twist": "Z",
                       "Forward": "Y",
                       "Up": "Z"}
detailedInfo["zxy"] = {"Pitch/Bend Forward": "Y",
                       "Yaw/Twist": "Z",
                       "Forward": "X",
                       "Up": "Z"}

rotateSecondaryAxis = {'yzx': 'zup', 'yxz': 'zup', 'xyz': 'xup', 'xzy': 'xup', 'zyx': 'yup', 'zxy': 'yup'}
rotateOrder = 'yzx'
pm.joint(edit=True, zeroScaleOrient=True, children=True, orientJoint=rotateOrder,
         secondaryAxisOrient=rotateSecondaryAxis[rotateOrder])

for key in ["Pitch/Bend Forward","Yaw/Twist","Forward","Up"]:
    print "{} : {}".format(key, detailedInfo[rotateOrder][key])
print detailedInfo[rotateOrder]["Pitch/Bend Forward"]
print detailedInfo[rotateOrder]["Yaw/Twist"]
print detailedInfo[rotateOrder]["Forward"]
print detailedInfo[rotateOrder]["Up"]


detailedInfo["yzx"] = {"Pitch/Bend Forward": "X",
                       "Yaw/Twist": "Y",
                       "Forward": "Z",
                       "Up": "Y"}
# pm.joint(edit=True, zeroScaleOrient=True, children=True,  orientJoint='yzx', secondaryAxisOrient='yup')
pm.joint(edit=True, zeroScaleOrient=True, children=True, orientJoint='yzx', secondaryAxisOrient='zup')

detailedInfo["yzx"] = {"Pitch/Bend Forward": "Z",
                       "Yaw/Twist": "Y",
                       "Forward": "X",
                       "Up": "Y"}
# pm.joint(edit=True, zeroScaleOrient=True, children=True,  orientJoint='yxz', secondaryAxisOrient='yup')
pm.joint(edit=True, zeroScaleOrient=True, children=True, orientJoint='yxz', secondaryAxisOrient='xup')

detailedInfo["xyz"] = {"Pitch/Bend Forward": "Y",
                       "Yaw/Twist": "X",
                       "Forward": "Z",
                       "Up": "X"}
pm.joint(edit=True, zeroScaleOrient=True, children=True, orientJoint='xyz', secondaryAxisOrient='xup')

detailedInfo["xzy"] = {"Pitch/Bend Forward": "Z",
                       "Yaw/Twist": "X",
                       "Forward": "Y",
                       "Up": "X"}
pm.joint(edit=True, zeroScaleOrient=True, children=True, orientJoint='xzy', secondaryAxisOrient='xup')

detailedInfo["zyx"] = {"Pitch/Bend Forward": "X",
                       "Yaw/Twist": "Z",
                       "Forward": "Y",
                       "Up": "Z"}

pm.joint(edit=True, zeroScaleOrient=True, children=True, orientJoint='zyx', secondaryAxisOrient='zup')
pm.joint(edit=True, zeroScaleOrient=True, children=True, orientJoint='zyx', secondaryAxisOrient='zdown')

detailedInfo["zxy"] = {"Pitch/Bend Forward": "Y",
                       "Yaw/Twist": "Z",
                       "Forward": "X",
                       "Up": "Z"}
pm.joint(edit=True, zeroScaleOrient=True, children=True, orientJoint='zxy', secondaryAxisOrient='zup')
pm.joint(edit=True, zeroScaleOrient=True, children=True, orientJoint='zxy', secondaryAxisOrient='zdown')
