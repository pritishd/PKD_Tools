"""
@package PKD_Tools.libUtilities
@brief Miscellenous package with useful commands that is imported by other packages.
@details As the package gets more complex, we will refactor common methods into specialised packages
"""
import sys
from collections import Mapping
import pymel.core as pm
from maya import cmds, mel
from PKD_Tools import logger


def force_pynode(node):
    """
    Force the node to be pynode
    @param node: This could be a string or pynode
    @return: The converted pynode
    """
    # Check that target is a pynode
    if not isinstance(node, pm.PyNode):
        node = pm.PyNode(node)
    return node


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
    get_selected(scriptEditorWarning=True)
    mel.eval("sets -e -forceElement initialShadingGroup;")
    cmds.undo()
    pm.select(cl=1)


def reverse_attribute(attribute, name=""):
    """
    Create a reverse node and connect it to the attribute
    @param attribute: Can be string name or attribute PyNode
    @param name: The name of the reverese node
    @return: The reverse pyname)
    attributenode
    """

    # PyNode the attribute
    attribute = force_pynode(attribute)
    reverse = pm.createNode("reverse")
    attribute >> reverse.inputX
    if name:
        reverse.rename(name)
    return reverse


def unique_name(name):
    """
    Return a name of a node that is totally unique in the scene. This ignores hierarchy
    @param name: the string which contains the candidate name
    @return: The unique name
    """
    name = pm.createNode("multiplyDivide", name=name).name()
    pm.delete(name)
    return name


def addFloatAttr(target, attrName="", attrMax=1, attrMin=0, softValue=0, shortName="", defaultValue=0):
    """
    Add a float attr to tranform node
    @param target: Transform node
    @param attrName: The name shown in the channelbox
    @param attrMax: The maximum value of the float attribute. Default is 1
    @param attrMin: The minumum value of the float attribute. Default is 0
    @param softValue: Does the attribute has a SoftValue
    @param shortName: The shortname of the atrtribute
    @param defaultValue: The default value of the attribute. Default is 0 however could be set to something else
    """
    if not shortName:
        shortName = attrName
    if softValue:
        pm.addAttr(target, ln=shortName, nn=attrName, at="double", hsn=1, hsx=1, smn=attrMin, smx=attrMax,
                   dv=defaultValue)
    else:
        pm.addAttr(target, ln=shortName, nn=attrName, at="double", min=attrMin, max=attrMax, dv=defaultValue)
    pm.setAttr(target + "." + shortName, e=1, k=1)


def addDivAttr(target, label, ln=None):
    """
    Add a divider on a transform node
    @param target: Tranform node
    @param label: The label to be displayed
    @param ln: The alias name of the attribute
    @return:
    """
    if not ln:
        ln = label
    pm.addAttr(target, ln=ln, en="%s:" % label, at="enum", nn="________")
    pm.setAttr("{0}.{1}".format(target, ln), lock=True, cb=True)


def addBoolAttr(target, label, sn=""):
    """
    Add a boolean attribute on a transform node
    @param target: Tranform node
    @param label: The label to be displayed
    @param sn: The shortname of the atttribute
    """

    if not (sn):
        sn = label
    pm.addAttr(target, ln=sn, nn=label, at="bool")
    pm.setAttr(target + "." + sn, e=1, k=1)


def addStrAttr(target, attrName, sn=""):
    """
    Add a string attribute on a transform node
    @param target: Transform node
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


def color_curve(target, color):
    """
    Override Color for shape object
    @param target: The target curve object
    @param color: The color name
    """
    color_dict = {"red": 13, "blue": 6, "yellow": 17, "lightblue": 18}

    if target is not None:
        shape = pm.listRelatives(target, f=1, s=1)[0]
        pm.setAttr(shape + ".overrideEnabled", 1)
        pm.setAttr(shape + ".overrideColor", color_dict[color])


def parZero(target, suffix="Prnt"):
    """
    Zero out a translation on dag by positioning the a new group in the same place as the target
    and then parenting the target to the new group
    @param target: the target transform node
    @param suffix: The new suffix to be added
    @return:The new parent node
    """
    target = force_pynode(target)
    group = pm.group(n="{0}_{1}".format(target.name(), suffix), empty=True)
    parentObject = pm.listRelatives(target, parent=True)
    snap(group, target)
    if parentObject:
        pm.parent(group, parentObject[0])
    pm.parent(target, group)
    return group


def snap(target, source, translate=True, rotate=True):
    """
    Snap the first object to the second object.
    @param target: The target transform
    @param source: The source transform
    @param translate: Should we snap the translation?
    @param rotate: Should we do the rotation?
    @return:
    """
    target = force_pynode(target)
    source = force_pynode(source)
    if translate:
        # Set the world space translation
        target.setTranslation(get_world_space_pos(source), space="world")

    if rotate:
        # Set the world space rotation
        target.setRotation(source.getRotation(space="world"), space="world")


def get_world_space_pos(source):
    """
    Return the world space position of pynode node. Some nodes such as CV do have getTranslation pynode function
    @param source: Pynode which could be transform , CV
    @return: Position
    """
    if hasattr(source, "getTranslation"):
        return pm.xform(source, rp=True, ws=True, query=True)
    elif hasattr(source, "getPosition"):
        return source.getPosition(space="world")
    else:
        raise ValueError("%s world space position cannot be queried" % source.name())


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


def snap_pivot(target, source):
    """
    Snap the pivot of source tranform to target transform
    """

    target = force_pynode(target)
    source = force_pynode(source)

    target.scalePivot.set(source.scalePivot.get())
    target.rotatePivot.set(source.rotatePivot.get())


def set_persp():
    """Set the default perpective"""
    persp = pm.PyNode("persp")
    persp.translate.set([35.118, 17.621, 40.211])
    persp.rotate.set([-6.938, 40.2, 0])
    mel.eval("ActivateViewport20")


def set_driven_key(driverInfo, drivenInfo, tangent="linear"):
    """Automate the set driven key through the use of set driven key
    @param driverInfo (dict) list of values of the driver attribute. The key should be the target attribute
    @param drivenInfo (dict) list of values of the driven attribute. The key should be the target attribute
    @param tangent (str) The type of tangent to be used for the set driven key. Default is linear

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
        raise RuntimeError("Not a dictInfo")

    driver = driverInfo.keys()[0]
    driven = drivenInfo.keys()[0]
    currentDriverValue = cmds.getAttr(driver)
    currentDrivenValue = cmds.getAttr(driven)

    inTangents = outTangent = tangent
    if tangent == "step":
        inTangents = "clamped"

    cmds.setDrivenKeyframe(driven, itt=inTangents, ott=outTangent, cd=driver)
    for driveAttr, drivenAttr in zip(driverInfo[driver], drivenInfo[driven]):
        cmds.setAttr(driver, driveAttr)
        cmds.setAttr(driven, drivenAttr)
        cmds.setDrivenKeyframe(driven, itt=inTangents, ott="linear", cd=driver)

    cmds.setAttr(driver, currentDriverValue)
    cmds.setAttr(driven, currentDrivenValue)


def select_vertices(targetGeo, vertices):
    '''Select vertices in geometery from list of indexes
    @param targetGeo (string/pynode) the geometery from which the vertices are selected
    @param vertices (float list) the vertice indices in a list format
    '''
    pm.select(cl=1)
    for index in vertices:
        pm.select("{}.vtx[{}]".format(targetGeo, index), add=1)


def skin_objects(targets, jointInfluences):
    """
    Skin a list of geo to the specified joints
    @param targets (string/pynode list) the geometeries which are going to be skinned
    @param jointInfluences (string list) the joints which will used for skining
    """
    for geo in targets:
        skinGeo(geo, jointInfluences)


def detach_skin(target):
    """
    @param target (string/pynode) the geometery which the skinning will be removed
    """
    target = force_pynode(target)
    pm.select(target)
    mel.eval('doDetachSkin "2" { "1","1" };')


def skinGeo(target, jointInfluences, **kwargs):
    """
    Skin a list of geo to the specified joints
    @param target (string/pynode) the geometery which is going to be skinned
    @param jointInfluences (string list) the joints which will used for skinning
    @param kwargs (dict) Any other keyword arguement that needs to be pass on to the maya command
    @return pynode of the skincluster that is made
    """
    target = force_pynode(target)
    jointInfluences = [force_pynode(inf) for inf in jointInfluences]

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
        detach_skin(target)

    # Skin to Joints
    pm.select(jnts, target)
    # Skin to the front of chain so that maya does not create a
    # "ShapeDeformed" mesh node for a referenced geo
    res = pm.skinCluster(tsb=1, mi=1, foc=True, **kwargs)

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
    for i in range(len(name) - 1, - 1, -1):
        if not name[i].isdigit():
            i += 1
            break
    return name[0:i]


def transfer_shape(source, target, snap_to_target=True, fix_name=False):
    """
    Reparent a shape node from one parent to another
    @param source: The source dag which contains the shape
    @param target: The source dag which will have the new shape the shape
    @param snap_to_target: Should be we reparent with world space or object space
    @param fix_name: Should we match the name of the shape to the new target
    @return:
    """
    source = force_pynode(source)
    target = force_pynode(target)
    if snap_to_target:
        snap(source, target)
        pm.makeIdentity(source, apply=1)
        if source.getShape().type() != "locator":
            try:
                pm.cluster(source)
                pm.delete(source, ch=1)
            except RuntimeError:
                logger.warning("Cannot cluster {}".format(source))

    oldShape = source.getShape()
    pm.parent(oldShape, target, shape=1, relative=1)
    if fix_name:
        fix_shape_name(target)
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
        pyVert.append(force_pynode(item))

    for item in pyVert:
        mel.eval("sets -rm %s %s" % (deformerSet, item))


def get_centre_piv_pos(geo):
    """
    Get the center point of a geo with help of cluster
    @param geo: The target geo
    """
    cluster = pm.cluster(geo)[1]
    pos = pm.xform(cluster)
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
        logger.warning("Unable to set the target scale")


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
            logger.warning("## ## ##  FAILED MEL STATEMENT: %s## ## ## " % ("%s;" % statement))


def print_list(listItems):
    """Print each item in a list in a new line
    @param listItems (list) the items that needs to be printed
    """
    if type(listItems) != list:
        raise RuntimeError("Not a list datatype")
    else:
        for item in listItems:
            print item


def print_attention(iteration=1):
    """get attention in the command line
    @param iteration (integer) the number of attention character needs
    """
    base = "## ## "
    for i in range(iteration):
        base += base
    return base


def pyList(listItems):
    """Convert a string list into pynodes
    @param listItems (list) list of string item
    @return list of pynodes

    """
    return [force_pynode(node) for node in listItems]


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
    """Capitlise first letter without losing camelcasing"""
    return (item[0].upper() + item[1:])


def title(item):
    """Capitalise each word in a string while not changing the case of the other letters in the world
    @code
    import libUtilities
    libUtilities.title("GI joe is awesome")
    # Result: 'GI Joe Is Awesome' #
    @endcode
    """
    wordList = [word[0].upper() + word[1:] for word in item.split()]
    return " ".join(wordList)


def mel2pyStr(text, namespace):
    """
    Convert a mel command to pymel command and print the result
    @param text: The mel command
    @param namespace: The module name
    """
    if not text.endswith(";"):
        logger.warning('Please end the mel code with ";"')
    else:
        import pymel.tools.mel2py as py2mel
        print py2mel.mel2pyStr(text, pymelNamespace=namespace)


def mel2pm(text):
    """Convert a mel command to pymel command and print the result
      @param text: The mel command"""
    mel2pyStr(text, "pm")


def mel2cmds(text):
    """Convert a mel command to pymel command and print the result
      @param text: The mel command"""
    print "from maya import cmds"
    mel2pyStr(text, "cmds")


def change_tangents(tangent):
    """Function to change the default tangent based
    @param tangent (string) the type of default in and out tangent
    """
    pm.keyTangent(g=True, ott=tangent)
    if tangent == "step":
        pm.keyTangent(itt="clamped", g=True)
    else:
        pm.keyTangent(g=True, itt=tangent)
    logger.info("Current Tangents: %s" % tangent.capitalize())


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
    node = force_pynode(node)
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
    node = force_pynode(node)
    for attr in lockStatusDict:
        if lockStatusDict[attr]:
            node.attr(attr).lock()
        else:
            node.attr(attr).unlock()


def unlock_default_attribute(node):
    """
    Unlock the the default status of a node
    """
    node = force_pynode(node)
    for attr in _default_attibute_list_():
        node.attr(attr).unlock()


def freeze_transform(transform):
    """Freeze the default attributes of transform node even if the some of the attributes are locked. After freezing the
    status reset the transform status
    @param transform: The transform node that is being evaluated
    """
    # Get the current lock status of the default attributes
    defaultLockStatus = get_default_lock_status(transform)
    transform = force_pynode(transform)
    childrenLockStatus = {}
    # Check to see if there are any children
    if transform.getChildren(ad=1, type="transform"):
        # Iterate through all the children
        for childTransform in transform.getChildren(ad=1, type="transform"):
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
        set_lock_status(childTransform, childrenLockStatus[childTransform])
    set_lock_status(transform, defaultLockStatus)


def freeze_rotation(target):
    """Freeze the rotation attribute of a transform node
    @param target: The transform node or list of target that is being evaluated
    """
    pm.makeIdentity(target, n=0, s=0, r=1, t=0, apply=True)


def freeze_scale(target):
    """Freeze the scale attribute of a transform node
    @param target: The transform node or list of target that is being evaluated
    """
    pm.makeIdentity(target, n=0, s=1, r=0, t=0, apply=True)


def lock_attr(attr):
    """
    Convience function to lock and hide a attr
    @param attr: The pynode attr
    """
    attr.set(lock=True, keyable=False, channelBox=False)


def lock_default_attribute(transform):
    """Lock all the translation attr
    @param transform: The transform node that is being evaluated
    """
    node = force_pynode(transform)
    for attr in _default_attibute_list_():
        lock_attr(node.attr(attr))


def lock_translate(transform):
    """Lock all the position attr
    @param transform: The transform node that is being evaluated
    """
    node = force_pynode(transform)
    for attr in _translate_attribute_list_():
        lock_attr(node.attr(attr))


def lock_rotate(transform):
    """Lock all the rotation attr
    @param transform: The transform node that is being evaluated
    """
    node = force_pynode(transform)
    for attr in _rotate_attribute_list_():
        lock_attr(node.attr(attr))


def lock_scale(transform):
    """Lock all the scale attr
    @param transform: The transform node that is being evaluated
    """
    node = force_pynode(transform)
    for attr in _scale_attribute_list_():
        lock_attr(node.attr(attr))


def _default_attibute_list_():
    """"Return the list of default maya attributes"""
    return _translate_attribute_list_() + _rotate_attribute_list_() + _scale_attribute_list_() + \
           _visibility_attribute_list_()


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


def inverseMultiplyDivide(name=""):
    """
    Create a multiplyDivide(MD) node which changes the values from positive to negative and vice versa
    @param name The name of the multiplyDivide node
    @return: MD node
    """
    md = pm.createNode("multiplyDivide")
    md.input2X.set(-1)
    if name:
        md.rename(name)
    return md


def fix_shape_name(transform):
    """
    Rename the shape name so that it matches the parent
    @param transform:  The pynode transform name with the wrong shape name
    """
    transform.getShape().rename("%sShape" % transform.shortName())


def add_nodes_to_namespace(namespace, nodes):
    """
    Put target nodes under a namespace. If the namespace is not found then it will created
    @param namespace: The target namespace
    @param nodes: List of target PyNodes

    """
    # Check if the namespace exists
    if not pm.namespace(exists=namespace):
        pm.namespace(add=namespace)
    # Put items under namespace
    for item in nodes:
        item.rename("%s:%s" % (namespace, item.nodeName()))


def cheap_point_constraint(source, target, maintainOffset=False):
    """
    An much lighter alternative to a point constraint which uses locatorShape.worldPosition[0] attribute.
    @param source: (locator)The a pynode locator
    @param target: (transform) The target pynode transform node
    @param maintainOffset: (bool) Should an offset be maintained
    @return: return the plus minus node if there is maintain offset
    """
    if not source.listRelatives(type="locator"):
        source.select()
        raise ValueError("Source must be a locator")

    if hasattr(target, "translate"):
        target = target.translate

    if maintainOffset:
        # Calculate diff
        diff = get_world_space_pos(source) - get_world_space_pos(target)
        # Create a MD node
        pma = pm.createNode("plusMinusAverage")
        pma.input3D[0].input3D.set(diff)
        source.worldPosition[0] >> pma.input3D[1]
        pma.output3D >> target
        return pma
    else:
        source.worldPosition[0] >> target


def output_window(text):
    """Write to the output windows instead of the script editor
    @param text: (str) The text to be outputted
    """
    sys.__stdout__.writelines("{}\n".format(text))


def update_deep_dict(target, source):
    """Recursively update a target dict with a source dict
    @param target: (dict) The target dictionary
    @param source: (dict) The source dictionary
    """
    for key, value in source.items():
        # this condition handles the problem
        if not isinstance(target, Mapping):
            target = source
        elif isinstance(value, Mapping):
            res = update_deep_dict(target.get(key, {}), value)
            target[key] = res
        else:
            target[key] = source[key]
    return target


class Ctrl(object):
    """
    Create basic ctrl setup
    """

    def __init__(self, loc_name):
        """
        Initialise the object
        :param loc_name: (str) The base name
        """
        self.ctrl = pm.createNode("transform", name=loc_name)
        self.xtra = parZero(self.ctrl, "Xtra")
        self.prnt = parZero(self.xtra)
        self.prnt.rename("{}_Prnt".format(loc_name))
        self.ctrl.rename("{}_Ctrl".format(loc_name))
        for node in self.ctrl, self.xtra, self.prnt:
            lock_attr(node.v)


def transpose(collection):
    """
    Turn a list of index upside down
        [[1,2,3]      --- [[1,4]
        [4,5,6]]      --- [2,5]
                      --- [3,6]]
    @param collection: The original collection of indexes
    @return: The transposed values
    """

    return map(list, zip(*collection))


def break_connection(node, attr):
    """Break the connection on attribute in a node
    @param node: The node that is being is worked on
    @param node: The attr that needs to be disconnected
    """

    mel.eval('source channelBoxCommand;')
    mel.eval('CBdeleteConnection "{0}.{1}";'.format(node, attr))


# noinspection PyStatementEffect
def connect_override(node, target):
    """Connect the drawing override for target from a control node
    @param node: The node that will control the drawing overrides
    @param target: The node that will have their drawing overridden
    """

    node = force_pynode(node)
    target = force_pynode(target)
    addDivAttr(node, label="Model", ln="model")
    pm.addAttr(node, ln="displayType", nn="Display Type", at="enum",
               en="normal:template:reference:", dv=2)
    node.displayType.set(e=True, keyable=True)
    target.overrideEnabled.set(True)
    node.displayType >> target.overrideDisplayType


def create_npc_node(curve):
    """
    Create a nearest point on curve.

    Used to determine the nearest parameters for a position in world space

    @param curve: The curve which is being evaluated
    @return: (PyNode) The nearest point on curve node
    """
    # Create nearest point curve
    npc = pm.createNode("nearestPointOnCurve")
    # Connect the curve shape to input curve
    curve.worldSpace[0] >> npc.inputCurve

    return npc