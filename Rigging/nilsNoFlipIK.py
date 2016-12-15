#  script created by pymel.tools.mel2py from mel file:
#  H:\maya\scripts\nilsNoFlipIK.mel
#  http://Highend3d.com/maya/downloads/mel_scripts/character/4595.html

from pymel.all import *

def nilsGetLocalPos(vector, baseX, baseY, baseZ):
    """First is the input-vector given in world space. Argument 2-4 are the baseVectors in target space"""

    tMatrix = [None] * 9

    # Create transformationmatrix from base in worldspace to base in target space
    tMatrix[0] = baseX[0]
    tMatrix[3] = baseX[1]
    tMatrix[6] = baseX[2]
    tMatrix[1] = baseY[0]
    tMatrix[4] = baseY[1]
    tMatrix[7] = baseY[2]
    tMatrix[2] = baseZ[0]
    tMatrix[5] = baseZ[1]
    tMatrix[8] = baseZ[2]
    # Get determinant
    determinant = (((tMatrix[0] * tMatrix[4] * tMatrix[8]) + (tMatrix[1] * tMatrix[5] * tMatrix[6]) + (
        tMatrix[2] * tMatrix[3] * tMatrix[7])) - (
                       (tMatrix[6] * tMatrix[4] * tMatrix[2]) + (tMatrix[7] * tMatrix[5] * tMatrix[0]) + (
                           tMatrix[8] * tMatrix[3] * tMatrix[1])))
    # Multiply input-vector with theinverse of $tMatrix to get vector in target space
    localPos = [None] * 3

    if determinant != 0:
        localPos[0] = ((((tMatrix[4] * tMatrix[8]) - (tMatrix[5] * tMatrix[7])) * vector[0]) + (
            -((tMatrix[1] * tMatrix[8]) - (tMatrix[2] * tMatrix[7])) * vector[1]) + (
                           ((tMatrix[1] * tMatrix[5]) - (tMatrix[2] * tMatrix[4])) * vector[2])) / determinant
        localPos[1] = ((-((tMatrix[3] * tMatrix[8]) - (tMatrix[5] * tMatrix[6])) * vector[0]) + (
            ((tMatrix[0] * tMatrix[8]) - (tMatrix[2] * tMatrix[6])) * vector[1]) + (
                           -((tMatrix[0] * tMatrix[5]) - (tMatrix[2] * tMatrix[3])) * vector[2])) / determinant
        localPos[2] = ((((tMatrix[3] * tMatrix[7]) - (tMatrix[4] * tMatrix[6])) * vector[0]) + (
            -((tMatrix[0] * tMatrix[7]) - (tMatrix[1] * tMatrix[6])) * vector[1]) + (
                           ((tMatrix[0] * tMatrix[4]) - (tMatrix[1] * tMatrix[3])) * vector[2])) / determinant

    return localPos


def nilsNoFlipIKProc(newPVX, newPVY, newPVZ, ikHandle):
    startJoint = ""
    # Name of startJoint for the ikChain
    sourceWorld = []
    # The vector in world space of the input vector
    sourceLocal = []
    # The vector in local space of the input vector
    targetWorld = []
    # The vector in world space of the previous input vector, which is the target vector for the twist
    # Base vectors for ikHandles local space
    baseX = []
    # Vector pointing in the direction of the previous pole Vector
    baseY = []
    # Vector pointing in the direction of ikHandle to startJoint
    baseZ = []
    # Vector pointing in a direction that is perpendicular both of the above vectors
    twist = 0.0
    # The calculated twist
    sourceWorld = [newPVX, newPVY, newPVZ]
    tempStrArr = []
    # A temporary stringarray to get strings from
    # Get startjoint
    tempStrArr = listConnections((ikHandle + ".startJoint"),
                                 s=True, d=False)
    startJoint = tempStrArr[0]
    # Get targetWorld from ikHandle
    targetWorld = getAttr(ikHandle + ".poleVector")
    # Create nulls, position and constrain them to get the baseVector of the local space the ikHandle is in
    null = str(group(em=1))
    delete(pointConstraint(startJoint, null))
    aimConstraint(ikHandle, null, weight=1, upVector=(1, 0, 0), worldUpType="vector", offset=(0, 0, 0),
                  aimVector=(0, -1, 0), worldUpVector=(targetWorld[0], targetWorld[1], targetWorld[2]))
    null2 = str(group(em=1))
    parent(null2, null)
    # Get base-vectors by translating null2(which is in ikHandles localspace) in all three axis
    offset = getAttr(null + ".translate")
    # Later subract the position of null
    setAttr((null2 + ".translate"),
            1, 0, 0)
    baseX = xform(null2, q=1, translation=1, ws=1)
    baseX[0] -= offset[0]
    baseX[1] -= offset[1]
    baseX[2] -= offset[2]
    setAttr((null2 + ".translate"),
            0, 1, 0)
    baseY = xform(null2, q=1, translation=1, ws=1)
    baseY[0] -= offset[0]
    baseY[1] -= offset[1]
    baseY[2] -= offset[2]
    setAttr((null2 + ".translate"),
            0, 0, 1)
    baseZ = xform(null2, q=1, translation=1, ws=1)
    baseZ[0] -= offset[0]
    baseZ[1] -= offset[1]
    baseZ[2] -= offset[2]
    delete(null, null2)
    # Delete these temporary helpers
    # Get the sourceVector in localSpace


    sourceLocal = nilsGetLocalPos(sourceWorld, baseX, baseY, baseZ)
    if len(sourceLocal) == 3:
        twist = float((mel.atan2d(sourceLocal[2], sourceLocal[0]) * -1))
        # Could get local vector from nilsGetLocalPos
        # Calculate twist by getting the angle between the source and targetVector in localSpace. The Y-value is not relevant because it doesnt contribute to the rotation of the ikPlane
        return twist


    # Couldn't calculate twist
    else:
        mel.error("Sorry. Couldn't calculate twist \n")
        # Print Error


def nilsNoFlipIKWinProc():
    sourceWorld = []
    # Get desired poleVector from window
    if window('nilsNoFlipIKWin', exists=1):
        sourceWorld[0] = float(floatField('floatFieldPVX', q=1, v=1))
        sourceWorld[1] = float(floatField('floatFieldPVY', q=1, v=1))
        sourceWorld[2] = float(floatField('floatFieldPVZ', q=1, v=1))


    # If this procedure wasn't called from window use the default settings
    else:
        sourceWorld = [0, 0, -1]

    sel = ls(sl=1)
    # Current selection
    ikHandle = sel[0]
    if nodeType(ikHandle) == "ikHandle":
        initTwist = float(getAttr(ikHandle + ".twist"))
        # If the first selected object is of type ikHandle, proceed
        # Set poleVector and twist on ikHandle
        setAttr((ikHandle + ".twist"),
                0)
        twist = float(nilsNoFlipIKProc(sourceWorld[0], sourceWorld[1], sourceWorld[2], ikHandle) + initTwist)
        setAttr((ikHandle + ".poleVector"),
                sourceWorld[0], sourceWorld[1], sourceWorld[2])
        setAttr((ikHandle + ".twist"),
                twist)
        # Select ikHandle
        select(ikHandle)
        # Print Feedback
        print "Twist calculated to: " + str(twist) + " and set on " + ikHandle + ".twist\n"


    else:
        mel.warning("Wrong selection. Select ikHandle")
