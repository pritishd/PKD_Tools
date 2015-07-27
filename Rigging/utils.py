__author__ = 'admin'
import pymel.core as pm
from pymel.internal.plogging import pymelLogger as pyLog

from PKD_Tools import libFile

reload(libFile)


def nameMe(partSfx, partName, endSuffix):
    """Set the name convention of all nodes"""
    if partSfx and partName and endSuffix:
        return "%s_%s_%s"%(partSfx,partName,endSuffix)

ctrlJsonFile = libFile.join(libFile.current_working_directory(),"Rigging/Data/Ctrl.json")

def export_ctrl_shapes():
    """Export curve data from the existing curve to a json file"""
    curvesData= {}
    for top in pm.ls(assemblies=True, ud=True):
        if top.getShape().type()=="nurbsCurve":
            detailedInfo = {}
            detailedInfo["cvs"] = [list(cv) for cv in top.getCVs()]
            detailedInfo["form"] = top.f.get()
            detailedInfo["degree"] = top.degree()
            detailedInfo["knots"] = top.numKnots()
            curvesData[top.name()] = detailedInfo

    libFile.write_json(ctrlJsonFile,curvesData)
    pyLog.info("Curve information written to: %s"%ctrlJsonFile)

def build_ctrl_shape(type=""):
    """Create a curve from the json"""
    curvesData = libFile.load_json(ctrlJsonFile)

    if curvesData.has_key(type):
        detailedInfo = curvesData[type]
        return pm.curve(name = type,
                 point=detailedInfo["cvs"],
                 per=detailedInfo["form"],
                 k=range(detailedInfo["knots"]),
                 degree=detailedInfo["degree"])

    else:
        pyLog.warning("%s not found in exported curve information file"%type)

def build_all_ctrls_shapes():
    """Build all curves from the json file"""
    curvesData = libFile.load_json(ctrlJsonFile)
    for crv in curvesData.keys():
        build_ctrl_shape(crv)


