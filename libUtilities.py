'''
@package PKD_Tools.libUtilities
@brief Miscellenous package with useful commands that is imported by other packages.
@details As the package gets more complex, we will refactor common methods into specialised packages
'''

from maya import cmds, mel
import pymel.core as pm
import pymel.tools.mel2py as py2mel
from pymel.internal.plogging import pymelLogger as pyLog

import libXml
from libVector import vector

reload(libXml)


def get_selected(stringMode=False, scriptEditorWarning=True):
    '''Return the current selected objects in the viewport. If nothing is selected either error out or return a False bool
    @param stringMode (bool) Return the selection as string list as opposed to pynode list
    @param scriptEditorWarning (bool) Commandmode will force the stop the process. If set to True then a warning will be given instead of erroring out.
    '''
    selection = pm.selected()
    if not selection:
        if scriptEditorWarning:
            cmds.warning("Nothing is selected")
            return False
        else:
            cmds.error("Nothing is Selected")
    if stringMode:
        # Convert all items to list
        selection = [str(item) for item in selection]
    return selection


def fix_shaders():
    """
    Fixing a bug in maya where a referenced maya file loses it's shaders. Mesh needs to be selected
    """
    selection = get_selected(scriptEditorWarning=True)
    mel.eval("sets -e -forceElement initialShadingGroup;")
    cmds.undo()
    pm.select(cl=1)


def reverse_attibute(attribute, name=""):
    """
    Create a reverse node and connect it to the attribute
    @param attribute: Can be string name or attribute PyNode
    @param name: The name of the reverese node
    @return: The reverse pynnode
    """

    # PyNode the attribute
    attribute = pm.PyNode(attribute)
    reverse = pm.createNode("reverse")
    if name:
        reverse.rename(name)
    attribute >> reverse.inputX
    return reverse


#
# def create_wrap(source, target):
#     ## 
#     ## Create  Wrap Deformer and return the deformer name
#     ## 
#     pm.select(source, target)
#     mel.eval('CreateWrap;')
#     for dfr in pm.listHistory(source, pdo=1):
#         if dfr.type() == "wrap":
#             return dfr


def addAttr(target, attrName="", attrMax=1, attrMin=0, SV=0, sn="", df=0):
    """
    Add a float attr to tranform node
    @param target: Tranform node
    @param attrName: The name shown in the channelbox
    @param attrMax: The maximum value of the float attribute. Default is 1
    @param attrMin: The minumum value of the float attribute. Default is 0
    @param SV: Does the attribute has a SoftValue
    @param sn: The shortname of the atrtribute
    @param df: The default value of the attribute. Default is 0 however could be set to something else
    @return:
    """
    if not sn:
        sn = attrName
    if SV:
        pm.addAttr(target, ln=sn, nn=attrName, at="double", hsn=1, hsx=1, smn=attrMin, smx=attrMax, dv=df)
    else:
        pm.addAttr(target, ln=sn, nn=attrName, at="double", min=attrMin, max=attrMax, dv=df)
    pm.setAttr(target + "." + sn, e=1, k=1)


def addDivAttr(target, attrName, sn=""):
    """
    Add a divider on a transform node
    @param target: Tranform node
    @param attrName: The attribute name
    @param sn: The shortname of the atttribute
    @return:
    """

    if not (sn):
        sn = attrName
    pm.addAttr(target, ln=sn, nn=attrName, at="enum", en="__________:")
    pm.setAttr(target + "." + sn, lock=1, cb=1)


def addBoolAttr(target, attrName, sn=""):
    """
    Add a boolean attribute on a transform node
    @param target: Tranform node
    @param attrName: The attribute name
    @param sn: The shortname of the atttribute
    """

    if not (sn):
        sn = attrName
    pm.addAttr(target, ln=sn, nn=attrName, at="bool")
    pm.setAttr(target + "." + sn, e=1, k=1)


def addStrAttr(target, attrName, sn=""):
    """
    Add a string attribute on a transform node
    @param target: Tranform node
    @param attrName: The attribute name
    @param sn: The shortname of the atttribute
    """
    if not sn:
        sn = attrName
    pm.addAttr(target, ln=sn, nn=attrName, dt="string")
    pm.setAttr(target + "." + sn, e=1, k=1)


def lockAttr(target, attributes, lock=True):
    """
    Toggle Lock and hide / unlock and show attributes
    @param target: The target transform ndoe
    @param attributes: The attibutes which will be toggled
    @param lock: Toggle state
    """
    for attr in attributes:
        if pm.attributeQuery(attr, node=target, ex=1):
            if lock:
                pm.setAttr(target + "." + attr, l=1, k=0, cb=0)
            else:
                pm.setAttr(target + "." + attr, l=0, k=1)
    if ["rx", "ry", "rz"] == attributes[0:3] and lock:
        for i in range(3):
            pm.setAttr(target + "." + attributes[i], l=0)


def name_me(Description="", attributeType="", side=""):
    """
    Return a naming convention for a node
    @param Description: Short discription of the node
    @param attributeType: What type of node is it
    @param side: Which side does it belong to
    """
    if side:
        return "%s_%s_%s" % (side, Description, attributeType)
    else:
        return "%s_%s" % (Description, attributeType)


def colorCurve(target, col):
    """
    Override Color for shape object
    @param target: The target curve object
    @param col: The color index
    """
    if target is not None:
        shape = pm.listRelatives(target, f=1, s=1)[0]
        pm.setAttr(shape + ".overrideEnabled", 1)
        pm.setAttr(shape + ".overrideColor", col)


def parZero(target, sfx="Prnt"):
    """
    Zero out a translation on dag by positioning the a new group in the same place as the target and then parenting the target to the new group
    @param target:
    @param sfx:
    @return:
    """
    ## 
    ##
    ## 
    group = pm.group(n=target + "_" + sfx, em=1)
    parentObject = pm.listRelatives(target, p=1)
    snapper(group, target)
    if parentObject:
        pm.parent(group, parentObject[0])
    pm.parent(target, group)
    return group


def snapper(source, target="", t=True, r=True):
    """
    Snap the first object to the second object. However a preset value can also be given.
    @param source: The source transform object
    @param target: The target transform attriute
    @param t: Should we snap the translation?
    @param r: Should we do the rotation?
    @return:
    """
    ## 
    ## Snap the first object to second object
    ##  t = Translate
    ##  r = rotate
    ##  preSetVal = first item list relates to a translate, second one relates to rotate
    source = str(source)
    target = str(target)
    if t:
        ## Get the translation values of second object if nothing is given
        trans = xform(target)
        ## Assign the translation values on to the first Object

        if len(trans):
            pm.move(trans[0], trans[1], trans[2], source, rpr=1)

    if r:
        ## Get the rotation values of second object if nothing is given
        rot = xform(target, 0)
        ## Always Assign the translation values on to the first Object]
        if len(rot):
            pm.xform(source, ws=1, ro=[rot[0], rot[1], rot[2]])


def xform(target, t=True):
    """
    Query the world space translate or rotate
    @param target: The target transform
    @param t: are we quering translation or rotation
    @return:
    """
    if t:
        return vector(pm.xform(target, q=1, ws=1, rp=1))
    else:
        return pm.xform(target, q=1, ws=1, ro=1)


def indexize_vertice_group(vertice_group):
    '''Iterate through vertic group and decompress into individual index
    @param vertice_group (pynode) vertice group, which usually comes from a selection or when querying a deformer set
    @return list of vertices
    '''
    vertices = []
    for item in vertice_group:
        for ind in item.indices():
            vertices.append(ind)
    return vertices


def snap_pivot(source, target):
    """
    Snap the pivot of source tranform to target transform
    """

    source = pm.PyNode(source)
    target = pm.PyNode(target)
    pivPos = xform(target)
    pm.setAttr(source.scalePivot, pivPos)
    pm.setAttr(source.rotatePivot, pivPos)


def set_persp():
    """Set the default perpective"""
    persp = pm.PyNode("persp")
    persp.translate.set([35.118, 17.621, 40.211])
    persp.rotate.set([-6.938, 40.2, 0])
    mel.eval("ActivateViewport20")


def setDrivenKey(driverInfo, drivenInfo):
    """Automate the set driven key through the use of set driven key
    @param driverInfo list of values of the driver attribute. The key should be the target attribute
    @param drivenInfo list of values of the driven attribute. The key should be the target attribute

    @code
    import libUtilities
    #Set up the driver info
    driverInfo = {"ctrl.tx":[0,1]}
    drivenInfo = {"cube.rz":[0,360]}
    libUtilities.setDrivenKey(driverInfo, drivenInfo )
    @endcode

    @warning The number of values in both driver and driven attribute should be same
    """

    if type(driverInfo) != dict or type(drivenInfo) != dict:
        raise Exception("Not a dictInfo")

    driver = driverInfo.keys()[0]
    driven = drivenInfo.keys()[0]
    currentDriverValue = cmds.getAttr(driver)
    currentDrivenValue = cmds.getAttr(driven)

    cmds.setDrivenKeyframe(driven, itt="linear", ott="linear", cd=driver)
    for driveAttr, drivenAttr in zip(driverInfo[driver], drivenInfo[driven]):
        cmds.setAttr(driver, driveAttr)
        cmds.setAttr(driven, drivenAttr)
        cmds.setDrivenKeyframe(driven, itt="linear", ott="linear", cd=driver)

    cmds.setAttr(driver, currentDriverValue)
    cmds.setAttr(driven, currentDrivenValue)


def select_vertices(targetGeo, vertices):
    '''Select vertices in geometery from list of indexes
    @param targetGeo (string/pynode) the geometery from which the vertices are selected
    @param vertices (float list) the vertice indices in a list format
    '''
    pm.select(cl=1)
    for index in vertices:
        pm.select("%s.vtx[%i]" % (targetGeo, index), add=1)


def skinObjects(targets, jointInfluences):
    """
    Skin a list of geo to the specified joints
    @param targets (string/pynode list) the geometeries which are going to be skinned
    @param jointInfluences (string list) the joints which will used for skining
    """
    for geo in targets:
        skinGeo(geo, jointInfluences)


def skinGeo(target, jointInfluences):
    """
    Skin a list of geo to the specified joints
    @param target (string/pynode) the geometery which is going to be skinned
    @param jointInfluences (string list) the joints which will used for skining
    @return pynode of the skincluster that is made
    """
    target = pm.PyNode(target)
    jointInfluences = [pm.PyNode(inf) for inf in jointInfluences]

    # Apply Defomers
    jnts = []
    nonJnts = []

    for item in jointInfluences:
        if item.getShape():
            nonJnts.append(item)
        else:
            jnts.append(item)

    # Detach the skin if there is one.
    currentSkin = get_target_defomer(target, "skinCluster")
    if currentSkin:
        pm.select(target)
        mel.eval('doDetachSkin "2" { "1","1" };')

    # Skin to Joints
    pm.select(jnts, target)
    # Skin to the front of chain so that maya does not create a
    # "ShapeDeformed" mesh node for a referenced geo
    res = pm.skinCluster(tsb=1, mi=1, foc=True)

    # Skin to non Joints
    if nonJnts:
        pm.select(nonJnts, target)
        pm.skinCluster(res, e=1, ai=nonJnts)

    return res


def get_target_defomer(target, deformer, multiple=False):
    """
    Query the name of deformer on a target geometery
    @param target (string/pynode) the geometery which contains the deformer
    @param deformer (string) the deformer which is queried
    @param multiple (bool) whether to query the first deformer found and return a list of deformer
    @return name / list of names of the target deformers

    @code
    import libUtilities
    #Query a single defomer
    libUtilities.get_target_defomer("myGeo","skinCluster")
    # Result: 'skinCluster1' #
    #Query multiple defomers
    libUtilities.get_target_defomer("myGeo","cluster",multiple=True)
    # Result: ['cluster1','cluster2','cluster3','cluster4']#
    @endcode
    """
    allDeformers = pm.listHistory(target, pdo=1)
    if allDeformers:
        allTargetDeformers = []
        for dfrm in allDeformers:
            if dfrm.type() == deformer:
                if multiple:
                    allTargetDeformers.append(dfrm.name())
                else:
                    return dfrm.name()
        if allTargetDeformers:
            allTargetDeformers.reverse()
        return allTargetDeformers


def strip_integer(item):
    """Remove and strip a integer from a pymel object"""
    name = strip_integer_in_string(item.name())
    item.rename(name)


def strip_integer_in_string(name):
    """Strip interger from string"""
    i = 0
    for i in range(len(name) - 1, 0 - 1, -1):
        if not name[i].isdigit():
            i += 1
            break
    return name[0:i]


def transfer_shape(source, target, snap=True):
    """
    Reparent a shape node from one parent to another
    @param source: The source dag which contains the shape
    @param target: The source dag which will have the new shape the shape
    @param snap: Should be we reparent with world space or object space
    @return:
    """
    source = pm.PyNode(source)
    target = pm.PyNode(target)
    if snap:
        snapper(source, target)
        pm.makeIdentity(source, apply=1)
    oldShape = source.getShape()

    pm.parent(oldShape, target, shape=1, r=1)
    return oldShape


def create_locator(name="locator"):
    """
    Create a nurbs curve which looks like a locator
    @param name: The name of the transform
    @return:
    """
    shape = [
        [-2.22044604925e-16, 1.7763568394e-15, -0.3],
        [-2.22044604925e-16, 1.7763568394e-15, 0.3],
        [-2.22044604925e-16, 1.7763568394e-15, 2.48689957516e-12],
        [-2.22044604925e-16, -0.3, 2.48689957516e-12],
        [-2.22044604925e-16, 0.3, 2.48689957516e-12],
        [-2.22044604925e-16, 1.7763568394e-15, 2.48689957516e-12],
        [0.3, 1.7763568394e-15, 2.48689957516e-12],
        [-0.3, 1.7763568394e-15, 2.48689957516e-12]
    ]

    locator = pm.curve(d=1, p=shape, n=name)
    return locator


def remove_cv_from_deformer(deformerSet, vertices):
    """
    Remove a list of CVs from a deformer set
    @param deformerSet: The target deformer set
    @param vertices: The vertices which will be removed.
    @return:
    """
    pyVert = []
    for item in vertices:
        pyVert.append(pm.PyNode(item))

    for item in pyVert:
        mel.eval("sets -rm %s %s" % (deformerSet, item))


def get_centre_piv_pos(geo):
    """
    Get the center point of geo with help of cluster
    @param geo: The target geo
    """
    cluster = pm.cluster(geo)[1]
    pos = xform(cluster)
    pm.delete(cluster)
    return pos


def bakeAnimation(target):
    """
    Bake the animation of the target dag with the appropriate settings and using the current time range as start and
    end times
    @param target: The target transform node
    @return:
    """
    timeRange = get_animation_time_range()
    target.select()
    mel.eval('''
    bakeResults -simulation true
    -t "%i:%i"
    -smart 1
    -disableImplicitControl true
    -preserveOutsideKeys true
    -sparseAnimCurveBake false
    -removeBakedAttributeFromLayer false
    -bakeOnOverrideLayer false
    -minimizeRotation true
    -controlPoints false
    -shape true {"%s"};''' % (timeRange[0], timeRange[1], target))


def snapBake(source, target):
    """
    Snap and bake the position of the source to the target. Delete all keys first
    @param source: Source transform
    @param target: Target transform
    """
    # Contraint
    mel.eval('cutKey -t ":" -f ":" -at "tx" -at "ty" -at "tz" -at "rx" -at "ry" -at "rz" %s;' % target)
    # Contraint
    con = pm.parentConstraint(source, target)
    # Bake Animation
    bakeAnimation(target)
    # Delete the contraint
    pm.delete(con)
    # Get the scale value
    scale = target.getScale()
    # Transfer
    mel.eval('cutKey -t ":" -f ":" -at "sx" -at "sy" -at "sz" %s;' % target)
    # Scale
    try:
        target.setScale(scale)
    except:
        pyLog.warning("Unable to set the target scale")



def melEval(evalStatment, echo=False):
    '''evaluate mel statement line for line. Print out error message for failed eval states
    @param evalStatment (string) the mel command which need to be evaluated. Multiple lines of mel commands can also be evaluated.
    @param echo (bool) print out the mel statement before evaluating. Useful for debugging
    '''
    for statement in evalStatment.split(";"):
        try:
            if echo:
                print statement
            mel.eval("%s;" % statement)
        except:
            pyLog.warning("## ## ##  FAILED MEL STATEMENT: %s## ## ## " % ("%s;" % statement))


def normalise_list(original_vals, new_normal):
    """
    normalize a list to fit a specific range, eg [-5,5],[0,1],[1,1].
    @param original_vals: The orginal list of number
    @param new_normal: The new desired range
    """
    #

    # get max absolute value
    original_max = max([abs(val) for val in original_vals])

    # normalize to desired range size
    return [float(val) / original_max * new_normal for val in original_vals]


def print_list(listItems):
    """Print each item in a list in a new line
    @param listItems (list) the items that needs to be printed
    """
    if type(listItems) != list:
        raise Exception("Not a list datatype")
    else:
        for item in listItems:
            print item


def print_attention(iteration=1):
    """get attention in the command line
    @param iteration (integer) the number of attention character needs
    """
    base = "## ## "
    for i in range(iteration):
        base = + base


def pyList(listItems):
    """Convert a string list into pynodes
    @param listItems (list) list of string item
    @return list of pynodes

    """
    return [pm.PyNode(node) for node in listItems]


def numberList(listItems):
    """Convert a string list into number
    @param listItems (list) list of numbers
    @return list of number list
    """
    return [float(node) for node in listItems]


def stringList(listItems):
    """Convert a list into string list"""
    return [str(node) for node in listItems]


def stringDict(PyDict):
    """Convert a pyDict into string dict"""
    stringDict = {}
    for key in PyDict.keys():
        stringDict[key.name()] = stringList(PyDict[key])
    return stringDict


def remove_namespace_from_reference():
    """Converted a referenced file with name space to one without namespace"""
    # Check if there are namespaces
    if pm.listReferences():
        # Get the First reference file
        ref = pm.listReferences()[0]
        # Get the path
        path = ref.path
        # Remove the path name
        ref.remove()
        # Reload the reference
        pm.createReference(path, namespace=":", mergeNamespacesOnClash=False)
    else:
        pm.warning("No namespaces found")


def capitalize(item):
    """Capitlise first case without losing camelcasing"""
    return (item[0].upper() + item[1:])


def title(item):
    """Capitalise each word in a string while not formating the other cases
    @code
    import libUtilities
    libUtilities.title("GI joe is awesome")
    # Result: 'GI Joe Is Awesome' #
    @endcode
    """
    lst = [word[0].upper() + word[1:] for word in item.split()]
    return " ".join(lst)


def mel2pyStr(text):
    """
    Convert a mel command to pymel command and print the result
    @param text: The mel command
    """
    ''.endswith()
    if not text.endswith(";"):
        pyLog.warning('Please end the mel code with ";"')
    else:
        print py2mel.mel2pyStr(text, pymelNamespace="pm")


def changeTangents(tangent):
    """Function to change the default tangent based
    @param tangent (string) the type of default in and out tangent
    """
    pm.keyTangent(g=True, ott=tangent)
    if tangent == "step":
        pm.keyTangent(itt="clamped", g=True)
    else:
        pm.keyTangent(g=True, itt=tangent)
    pyLog.info("Current Tangents: %s" % tangent.capitalize())

def get_animation_time_range():
    """Function to return the Start frame and End Frame
    @return tuple of integer
    """
    return pm.playbackOptions(q=1, ast=1), pm.playbackOptions(q=1, aet=1)


def get_default_lock_status(node):
    """
    Return the status of the transform of the node
    @param node: The pynode that is being evaluated
    @return: Dictonary of the various attributes lock status
    """
    node = pm.PyNode(node)
    lockStatus = {}
    for attr in _default_attibute_list_():
        lockStatus[attr] = node.attr(attr).isLocked()
    return lockStatus


def set_lock_status(node, lockStatusDict):
    """
    Set the lock status based on a dictonary of attributes
    @param node: The pynode that is being evaluated
    @param lockStatusDict: Dictonary of the various attributes lock status
    """
    node = pm.PyNode(node)
    for attr in lockStatusDict:
        if lockStatusDict[attr]:
            node.attr(attr).lock()
        else:
            node.attr(attr).unlock()

def set_visibility(node):
    k = pm.PyNode("asd")


def unlock_default_attribute(node):
    """
    Unlock the the default status of a node
    """
    node = pm.PyNode(node)
    for attr in _default_attibute_list_():
        node.attr(attr).unlock()


def freeze_transform(transform):
    """Freeze the default attributes of transform node even if the some of the attributes are locked. After freezing the
    status reset the transform status
    @param transform: The tranform node that is being evaluated
    """
    # Get the current lock status of the default attributes
    defaultLockStatus = get_default_lock_status(transform)
    transform = pm.PyNode(transform)
    childrenLockStatus = {}
    # Check to see if there are any children
    if transform.getChildren(ad=1,type="transform"):
        # Iterate through all the children
        for childTransform in transform.getChildren(ad=1,type="transform"):
            # Get the lock status of the children and store it in the dictonary
            childrenLockStatus[childTransform] = get_default_lock_status(childTransform)
            # Unlock the child transform status
            unlock_default_attribute(childTransform)

    # Unlock default status
    unlock_default_attribute(transform)

    # Freeze the tranform
    pm.makeIdentity(transform, n=0, s=1, r=1, t=1, apply=True)

    # Reset the children lock status
    for childTransform in childrenLockStatus:
        set_lock_status(childTransform,childrenLockStatus[childTransform])
    set_lock_status(transform,defaultLockStatus)

def _default_attibute_list_():
    """"Return the list of default maya attributes"""
    return _translate_attribute_list_() + _rotate_attribute_list_() + _scale_attribute_list_() + _visibility_attribute_list_()


def _translate_attribute_list_():
    """
    @return: Return the list of names of the default translate attribute of a maya transform node
    """
    return ["translateX",
            "translateY",
            "translateZ",
            "translate"
            ]


def _rotate_attribute_list_():
    """
    @return: Return the list of names of the default rotate attribute of a maya transform node
    """
    return ["rotateX",
            "rotateY",
            "rotateZ",
            "rotate"
            ]


def _scale_attribute_list_():
    """
    @return: Return the list of names of the default scale attribute of a maya transform node
    """
    return ["scaleX",
            "scaleY",
            "scaleZ",
            "scale"
            ]


def _visibility_attribute_list_():
    """
    @return: Return the list of names of the default scale attribute of a maya transform node
    """
    return ["visibility"]
