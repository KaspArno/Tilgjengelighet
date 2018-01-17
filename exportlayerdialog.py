import os

from PyQt4 import QtCore, QtGui, uic


FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'ui/export_layer.ui'))

class exportLayerDialog(QtGui.QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        super(exportLayerDialog, self).__init__(parent)
        self.setupUi(self)
