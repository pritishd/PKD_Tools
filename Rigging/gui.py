import json
from PKD_Tools import libJoint, libGUI, libPySide
import pymel.core as pm


class JointOrientWidget(libGUI.JointOrientWidget):
    """
    Widget which is compatible with metarig
    """

    def __init__(self, *args, **kwargs):
        self.pyattr = kwargs.get("pyattr", [])
        del kwargs["pyattr"]
        super(JointOrientWidget, self).__init__(*args, **kwargs)

    def delete_child_lock(self):
        """
        Delete the constraint
        """
        pm.delete(pm.listRelatives(self.joint, allDescendents=True, type="parentConstraint"))
        if pm.objExists("PKD_child_locker"):
            pm.delete("PKD_child_locker")
            libJoint.freeze_rotation(self.joint)

    def _setup_(self):
        super(JointOrientWidget, self)._setup_()
        self.stack_layout.insertWidget(3, libPySide.horizontal_divider())
        child_button = libPySide.QtGui.QPushButton("Lock Children")
        self.stack_layout.insertWidget(4, child_button)
        child_button.clicked.connect(self.lock_child)

    def lock_child(self):
        selection = pm.selected()
        child_locker = pm.createNode("transform", name="PKD_child_locker")
        child_joint = pm.listRelatives(self.joint)[0]
        pm.parentConstraint(child_locker, child_joint, maintainOffset=True)
        if selection:
            pm.select(selection)

    def orient(self):
        self.delete_child_lock()
        super(JointOrientWidget, self).orient()

    def zero_out_bend(self):
        self.delete_child_lock()
        super(JointOrientWidget, self).zero_out_bend()

    def update_gimbal_axis(self):
        self.delete_child_lock()
        super(JointOrientWidget, self).update_gimbal_axis()
        for attr in self.pyattr:
            attr.set(json.dumps(self.gimbal_data))

    def change_gimbal(self):
        self.delete_child_lock()
        super(JointOrientWidget, self).change_gimbal()
        for attr in self.pyattr:
            attr.set(json.dumps(self.gimbal_data))


class JointOrientWindow(libGUI.JointOrientWindow):
    def __init__(self, pyattr, closeFunc=None):
        self.pyattr = pyattr
        self.closeFunc = closeFunc
        super(JointOrientWindow, self).__init__()

    def _add_joint_widget_(self):
        self.joint_widget = JointOrientWidget(padding=40, pyattr=self.pyattr)
        self.joint_widget.done_button.clicked.connect(self.closeWin)

    def closeWin(self):
        if self.closeFunc:
            self.closeFunc()
        super(JointOrientWindow, self).close()
