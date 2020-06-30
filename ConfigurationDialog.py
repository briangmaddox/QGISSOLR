# -*- coding: utf-8 -*-
"""
ConfigurationDialog.py holds the class definition for the dialog to allow users to enter in the server and table strings.
"""

from PyQt5.QtWidgets import QDialog, QFormLayout, QLabel, QLineEdit, QDialogButtonBox


class ConfigurationDialog(QDialog):
    """
    Class to present the user with a configuration dialog and return the values entered.
    """

    # ******************************************************************************************************************
    def __init__(self, parent=None):
        QDialog.__init__(self)

        layout = QFormLayout()

        self.SOLRLabel = QLabel("SOLR Endpoint")
        self.SOLRLineEdit = QLineEdit()
        layout.addRow(self.SOLRLabel, self.SOLRLineEdit)

        self.TableLabel = QLabel("SOLR Tables")
        self.TableLineEdit = QLineEdit()
        layout.addRow(self.TableLabel, self.TableLineEdit)

        self.buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        layout.addRow(None, self.buttonBox)

        self.setLayout(layout)
        self.setWindowTitle("Configure QGIS SOLR Plugin")
        self.setMinimumWidth(550)
