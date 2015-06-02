"""
@package PKD_Tools.libUtilities
@brief Miscellenous package with useful commands that is imported by other packages.
@details As the package gets more complex, we will refactor common methods into specialised packages
"""

from maya import cmds, mel
from pymel import core as pm
import pymel.core as pm
import libXml
import libFile
for module in libFile, libXml:
    reload(module)

def get_selected(stringMode=False, scriptEditorWarning=True):
    """Return the current selected objects in the viewport. If nothing is selected either error out or return a False bool.
    @param stringMode (bool) Return the selection as string list as opposed to pynode list
    @param scriptEditorWarning (bool) Commandmode will force the stop the process. If set to false then a warning will be given instead of erroring out.
    """
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


def decompress_vertice_group(vertice_group):
    """Iterate through vertic group and decompress into individual index
    @param vertice_group (pynode) vertice group, which usually comes from a selection or when querying a deformer set
    @return list of vertices
    """
    vertices = []
    for item in vertice_group:
        for ind in item.indices():
            vertices.append(ind)
    return vertices


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

    pm.select(target)
    try:
        mel.eval('doDetachSkin "2" { "1","1" };')
    except:
        pass

    # Skin to Joints
    pm.select(jnts, target)
    res = pm.skinCluster(tsb=1, mi=1)

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


def melEval(evalStatment, echo=False):
    '''evaluate mel statement line for line. Print out error message for failed eval states
    @param evalStatment (string) the mel command which need to be evaluated. Multiple lines of mel commands can also be evaluated.
    @param echo (bool) print out the mel statement before evaluating. Useful for debugging
    '''
    for statement in evalStatment.split(";"):
        try:
            if echo:
                print
                statement
            mel.eval("%s;" % statement)
        except:
            print
            "###### FAILED MEL STATEMENT: %s######" % ("%s;" % statement)


def normalise_list(original_vals, new_normal):
    # normalize a list to fit a specific range, eg [-5,5].

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
    base = "####"
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


def changeTangents(tangent, *args):
    """Function to change the default tangent based
    @oaram tangent (string) the type of default in and out tangent
    """
    pm.keyTangent(g=True, ott=tangent)
    if tangent == "step":
        pm.keyTangent(itt="clamped", g=True)
    else:
        pm.keyTangent(g=True, itt=tangent)
    print "Current Tangents: %s" % tangent.capitalize()