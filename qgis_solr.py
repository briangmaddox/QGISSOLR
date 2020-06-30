# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QGISSolr
                                 A QGIS plugin
 This plugin allows the user to run and load SOLR queries into QGIS
                              -------------------
        begin                : 2018-04-02
        git sha              : $Format:%H$
        copyright            : (C) 2018 by Brian Maddox
        email                : brian.maddox@gmail.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

import configparser
import os.path
from osgeo import ogr
from osgeo import osr
# Initialize Qt resources from file resources.py
from . import resources
# Import the code for the dialog
from qgis.core import QgsMessageLog, QgsVectorLayer, QgsProject, QgsField, QgsFeature, QgsGeometry, QgsPointXY
from qgis.PyQt.QtCore import QVariant
from qgis.gui import QgsMessageBar
from . import iso3166
from PyQt5.QtCore import QSettings, QTranslator, qVersion, QCoreApplication, Qt
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QAction, QMessageBox, QProgressBar, QPushButton
from .ConfigurationDialog import ConfigurationDialog
from .managers import *
from .qgis_solr_dialog import QGISSOLRDialog


class QGISSolr(object):
    """QGIS Plugin Implementation."""

    # ******************************************************************************************************************
    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgisInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
                self.plugin_dir,
                'i18n',
                'QGISSolr_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&QGIS SOLR Plugin')
        # TODO: We are going to let the user set this up in a future iteration
        self.toolbar = self.iface.addToolBar(u'Solr')
        self.toolbar.setObjectName(u'Solr')

        # Check if plugin was started the first time in current QGIS session
        # Must be set in initGui() to survive plugin reloads
        self.first_start = None

        # Instantiate so we pull the data in at creation
        self.myTableManager = None
        self.myQueryManager = None

        self.tableDict = dict()

        # Create the dialog (after translation) and keep reference
        self.dlg = QGISSOLRDialog()

        # Set and keep our spatial reference
        self.spatialRef = osr.SpatialReference()
        self.spatialRef.SetFromUserInput("WGS84")

        # Progress bar
        self.progressDialog = None
        self.progressBar = None

        # ConfigurationDialog
        self.configurationDialog = ConfigurationDialog()
        self.configurationDialog.hide()

        # Connect the signal/slot
        self.dlg.configureButton.clicked.connect(self.__HandleConfigurationDialog)

    # ******************************************************************************************************************
    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('QGISSolr', message)

    # ******************************************************************************************************************
    def add_action(self, icon_path, text, callback, enabled_flag=True, add_to_menu=True, add_to_toolbar=True,
                   status_tip=None, whats_this=None, parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            self.toolbar.addAction(action)

        if add_to_menu:
            self.iface.addPluginToWebMenu(
                    self.menu,
                    action)

        self.actions.append(action)

        return action

    # ******************************************************************************************************************
    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/QGISSolr/icon.png'
        self.add_action(
                icon_path,
                text=self.tr(u'QGIS SOLR Query'),
                callback=self.run,
                parent=self.iface.mainWindow())

        # will be set False in run()
        self.first_start = True

    # ******************************************************************************************************************
    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginWebMenu(
                    self.tr(u'&QGIS SOLR Plugin'),
                    action)
            self.iface.removeToolBarIcon(action)
        # remove the toolbar
        del self.toolbar

    # ******************************************************************************************************************
    def run(self):
        """Run method that performs all the real work"""

        # Populate the dialog
        self.__InitSOLR()

        # show the dialog
        self.dlg.show()

        # Run the dialog event loop
        result = self.dlg.exec_()

        # Did we find anything?
        foundResults = False

        # To hold what layers had nothing
        noresultList = list()

        # See if OK was pressed
        if result:
            try:
                tableList = list()

                searchQuery = str(self.dlg.queryLineEdit.text()).strip()
                if len(searchQuery) < 3:
                    self.__ShowError("You must specify at least three characters as a search term!")
                    return

                cc3QueryIndex = self.dlg.whereComboBox.currentIndex()
                cc3Query = self.dlg.whereComboBox.itemData(cc3QueryIndex)

                tableQueryIndex = self.dlg.tableComboBox.currentIndex()
                tableQuery = self.dlg.tableComboBox.itemData(tableQueryIndex)

                if tableQuery != "":
                    tableList.append(tableQuery)
                else:
                    tableList = list(self.tableDict.keys())

                # Start the progressbar
                tablesDone = 0
                self.__ShowProgressBar(len(tableList))

                # Now iterate through the results
                for tempTable in tableList:
                    pageNumber = 0

                    # Update progress
                    self.__UpdateProgressBar(tablesDone)
                    tablesDone += 1

                    # Prime the search pump
                    results = self.myQueryManager.Search(inQuery=searchQuery, inCC3=cc3Query, inTable=tempTable)

                    # Get the human readable layer name
                    tableHumanName = ""
                    for key in self.tableDict:
                        if key == tempTable:
                            tableHumanName = self.tableDict[key]

                    if len(results) == 0:
                        noresultList.append("{}\n".format(tableHumanName))
                        continue

                    foundResults = True

                    # Get the fields list
                    layerFields = self.myTableManager.GetTableColumns(tempTable)

                    # Create our layer
                    tableLayer = self.__CreateLayer("{}_{}".format(tableHumanName, searchQuery), layerFields)
                    dataProvider = tableLayer.dataProvider()

                    while len(results) > 0:
                        for result in results:
                            tempFeature = QgsFeature(tableLayer.fields())

                            # Go through the fields
                            for tField in result:
                                try:
                                    tempFeature[tField] = str(result[tField])
                                except:
                                    # Solr will return some internal fields that we just ignore here.
                                    pass

                            # Set the geometry
                            # Some tables may not have location data.  Catch
                            # exceptions here and just continue without adding the feature.
                            try:
                                tempFeature.setGeometry(self.GetLocation(result))
                            except Exception as nogeom:
                                QgsMessageLog.logMessage("System ID {} has a NULL shape field".format(result["system_id"]))
                                continue

                            # Now add the features
                            dataProvider.addFeature(tempFeature)

                        tableLayer.updateExtents()

                        pageNumber += 1

                        results = self.myQueryManager.GetPage(tempTable, pageNumber)

                    QgsProject().instance().addMapLayer(tableLayer)

            except Exception as e:
                self.__ShowError("A problem occurred while running the plugin. Please consult the QGIS log!")
                QgsMessageLog.logMessage("QGISSolr::run: Exception: {}".format(e))
                self.__ResetFields()
                self.__RemoveProgressBar()
                return

            QgsMessageLog.logMessage("finished!")
            self.__RemoveProgressBar()
            self.__CreateFinishedMessage(noresultList)

            if not foundResults:
                self.__ShowError("Your query returned no results!")
                self.__ResetFields()
                return

            # And clean up
            self.__ResetFields()

    # ******************************************************************************************************************
    def GetLocation(self, inResult):
        """
        Attempt to parse the location out of a SOLR query result.
        :param inResult: dict of results
        :return: tuple with the x and y values.  0.0 for each means no coordinates found.
        """

        return QgsGeometry.fromWkt(inResult["the_geom"])

    # ******************************************************************************************************************
    def __PopulateWhereBox(self):
        """
        Populates the where combo box using the iso3166 module
        :return: None
        """

        # Clear out any existing entries
        self.dlg.whereComboBox.clear()

        # Add an empty entry
        self.dlg.whereComboBox.addItem("--Select an Optional Country--", "")

        # And add the current bounds entry
        self.dlg.whereComboBox.addItem("Use the current view boundaries", "QGIS")

        # Loop through and add countries from iso3166
        for tCountry in iso3166.countries:
            self.dlg.whereComboBox.addItem(tCountry.name, tCountry.alpha3)

    # ******************************************************************************************************************
    def __PopulateTableBox(self):
        """
        Populates the table box using standard SOLR tables
        :return: None
        """

        # Clear out any existing entries
        self.dlg.tableComboBox.clear()

        # Add an empty entry
        self.dlg.tableComboBox.addItem("--Select an Optional Table--", "")

        # And push them on
        self.tableDict = self.myTableManager.GetSOLRTables()

        if not self.tableDict:
            self.__ShowError("Could not retrieve tables. Please check your settings!")
            return

        for tTable in self.tableDict:
            self.dlg.tableComboBox.addItem(self.tableDict[tTable], tTable)

    # ******************************************************************************************************************
    def __ShowError(self, inText: str):
        """
        Display a warning to the user
        :param inText: text to display
        :return:
        """

        QgsMessageLog.logMessage("Critical Error: {}".format(inText))
        QMessageBox.critical(None, "Error:", inText)

    # ******************************************************************************************************************
    def __ShowWarning(self, inText: str):
        """
        Display a warning to the user
        :param inText: text to display
        :return:
        """

        QgsMessageLog.logMessage("Warning: {}".format(inText))
        QMessageBox.warning(None, "Warning", inText)

    # ******************************************************************************************************************
    def __CreateLayer(self, inLayerName: str, inLayerFields):
        """
        Creates a layer in the Geopackage with the specified fields.  Note all fields will be strings to mostly match
        what SOLR returns
        :param inLayerName: string of the layer name
        :param inLayerFields: dictionary of fields
        :return: True if successful
        """

        try:
            # Make the layer
            layer = QgsVectorLayer("Point?crs=epsg:4326", inLayerName, "memory")
            dataProvider = layer.dataProvider()

            # Create the fields in the layer
            for tField in inLayerFields:
                dataProvider.addAttributes([QgsField(tField, QVariant.String)])

            layer.updateFields()

            return layer

        except Exception as e:
            QgsMessageLog.logMessage("QGISSOLR::__CreateLayer: Exception: {}".format(e))
            raise e

    # ******************************************************************************************************************
    def __ShowProgressBar(self, inMaximum: int):
        """
        Initialize and display the progress bar
        :param inMaximum: Maximum value
        :return:
        """

        self.progressDialog = self.iface.messageBar().createMessage("Querying SOLR...")
        self.progressBar = QProgressBar()
        self.progressBar.setMaximum(inMaximum)
        self.progressBar.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.progressDialog.layout().addWidget(self.progressBar)
        self.iface.messageBar().pushWidget(self.progressDialog)
        self.progressDialog.show()

    # ******************************************************************************************************************
    def __RemoveProgressBar(self):
        """
        Removes the progress bar
        :return:
        """

        self.iface.messageBar().clearWidgets()
        self.progressDialog = None
        self.progressBar = None

    # ******************************************************************************************************************
    def __UpdateProgressBar(self, inValue: int):
        """
        Updates the value for the progress bar
        :param inValue: value to set
        :return:
        """

        self.progressBar.setValue(inValue)
        QCoreApplication.processEvents()

    # ******************************************************************************************************************
    def __ResetFields(self):
        """
        Resets the fields of the dialog box
        :return:
        """

        self.dlg.queryLineEdit.clear()
        self.dlg.whereComboBox.setCurrentIndex(0)
        self.dlg.tableComboBox.setCurrentIndex(0)

    # ******************************************************************************************************************
    def __InitSOLR(self):
        """
        Initialize SOLR and fill the combo boxes when someone actually runs the plugin instead of at object
        instantiation.
        :return:
        """

        try:
            # Get our configuration values
            SOLREndPoint, SOLRTables = self.__GetConfiguration()

            # Instantiate
            self.myTableManager = TableManager(SOLREndPoint, SOLRTables)
            self.myQueryManager = QueryManager(SOLREndPoint, self.iface, SOLRTables)

            self.__PopulateWhereBox()
            self.__PopulateTableBox()

        except Exception as e:
            self.__ShowError("An error has occurred while pulling table names from SOLR!")
            QgsMessageLog.logMessage("QGISSOLR::__InitSOLR: Exception {}".format(e))
            raise e

    # ******************************************************************************************************************
    def __CreateFinishedMessage(self, inStringList: list):
        """
        Creates the finished dialog box
        :param inStringList: list of strings to display
        :return:
        """
        if inStringList:
            listToString = "".join(inStringList)
            QMessageBox.information(None,
                                    "Finished!",
                                    "The query found no results in the following tables:\n{}".format(listToString))

    # ******************************************************************************************************************
    def __GetConfiguration(self):
        """
        Get the configuration values
        :return: tuple with configuration values
        """

        # Get the base directory for the plugin
        plugin_path = os.path.dirname(os.path.realpath(__file__))

        # Read in the configuration
        config = configparser.ConfigParser()
        config.read(plugin_path + "/config.ini")

        endPoint = config.get("QGISSOLR", "SOLR_ENDPOINT")
        tableList = config.get("QGISSOLR", "SOLR_TABLES").split(",")

        return endPoint, tableList

    # ******************************************************************************************************************
    def __HandleConfigurationDialog(self):
        """
        Display the configuration dialog and save any changes to the configuration
        :return: None
        """

        # Get our configuration values
        SOLREndPoint, tableList = self.__GetConfiguration()

        # Set the values for the dialog
        self.configurationDialog.SOLRLineEdit.setText(SOLREndPoint)
        self.configurationDialog.TableLineEdit.setText(",".join(str(x) for x in tableList))

        result = self.configurationDialog.exec_()

        if result:
            # Get the base directory for the plugin
            plugin_path = os.path.dirname(os.path.realpath(__file__))

            # Read in the configuration
            config = configparser.ConfigParser()
            config.read(plugin_path + "/config.ini")

            config.set("QGISSOLR", "SOLR_ENDPOINT", self.configurationDialog.SOLRLineEdit.text())
            config.set("QGISSOLR", "SOLR_TABLES", self.configurationDialog.TableLineEdit.text())

            with open(plugin_path + "/config.ini", "w") as configfile:
                config.write(configfile)

            # And now reinit
            self.__InitSOLR()
