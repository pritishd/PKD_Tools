import json
from PKD_Tools import libGUI


class JointOrientWidget(libGUI.JointOrientWidget):
    """
    Widget which is compatible with metarig
    """

    def __init__(self, *args, **kwargs):
        self.pyattr = kwargs.get("pyattr", 20)
        del kwargs["pyattr"]
        super(JointOrientWidget, self).__init__(*args, **kwargs)

    def update_gimbal_axis(self):
        super(JointOrientWidget, self).update_gimbal_axis()
        for attr in self.pyattr:
            attr.set(json.dumps(self.gimbal_data))

    def change_gimbal(self):
        super(JointOrientWidget, self).change_gimbal()
        for attr in self.pyattr:
            attr.set(json.dumps(self.gimbal_data))


class JointOrientWindow(libGUI.JointOrientWindow):
    def __init__(self, pyattr):
        self.pyattr = pyattr
        super(JointOrientWindow, self).__init__()

    def _add_joint_widget_(self):
        self.joint_widget = JointOrientWidget(padding=40, pyattr=self.pyattr)
