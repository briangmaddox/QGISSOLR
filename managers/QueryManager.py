# -*- coding: utf-8 -*-
"""
This file contains the QueryManager class that helps to abstract and move the query handling into a single class.
"""
from . import pysolr
from qgis.core import *
from qgis.gui import *


class QueryManager(object):
    """
    This class holds all of the logic to communicate with Solr, such as creating queries and getting
    search results.
    """

    # ******************************************************************************************************************
    def __init__(self, inSOLREndpoint: str, inQIface, inSolrTables: list):
        """
        Initialize ourself
        """

        # Variables for SOLR
        self.solrEndpoint = inSOLREndpoint
        self.rows = 500  # Number of rows to process at a time
        self.queryOK = False  # Have we run a query that worked ok?
        self.queryTerms = ""  # search terms from the user
        self.mySOLR = dict()
        self.iface = inQIface
        self._MakeSOLRObjects(inSolrTables)

    # ******************************************************************************************************************
    def _MakeSOLRObjects(self, inSOLRTables: list):
        """
        Create our internal dictionary of SOLR objects since pysolr doesn't really let you specify a core to search
        :param inSOLRTables: list of tables that need to be converted to a dictionary
        :return: True on success
        """

        try:
            for table in inSOLRTables:
                self.mySOLR[table] = pysolr.Solr(self.solrEndpoint + "/" + table.replace("_", ""))

        except Exception as e:
            self.queryOK = False
            QgsMessageLog.logMessage("QueryManager::_MakeSOLRObjects: Could not make objects.")
            QgsMessageLog.logMessage("QueryManager::_MakeSOLRObjects: Exception: {}".format(e))

    # ******************************************************************************************************************
    def Search(self, inQuery, inTable, inCC3="", ) -> pysolr.Results:
        """
        Perform the Solr search. Set useCurrentViewport to true to pull the bounds of the current
        QGIS view.
        :param inQuery: string with the search term(s)
        :param inCC3: string with the country to search
        :param inTable: string with the table to search
        :return: pysolr.results
        """

        try:
            self.queryTerms = str()

            # Build the query
            tempList = inQuery.split()
            for item in tempList:
                if item != tempList[-1]:
                    self.queryTerms += "_text_:" + item + " AND "
                    # self.queryTerms += item + " AND "
                else:
                    self.queryTerms += "_text_:" + item

            if inCC3:
                self.queryTerms += " AND {}".format(self.__CreateCC3(inCC3))

            self.queryOK = True  # so the other functions know to go ahead

            return self.__RunQuery(inTable, 0)

        except Exception as e:
            QgsMessageLog.logMessage("QueryManager::Search: Exception Type: {}".format(type(e).__name__))
            QgsMessageLog.logMessage("QueryManager::Search: Exception: {}".format(e))
            QgsMessageLog.logMessage("QueryManager::Search: Traceback: {}".format(e.__traceback__))
            self.queryOK = False
            return pysolr.Results()

    # ******************************************************************************************************************
    def GetPage(self, inTable, inPageNumber=0):
        """
        Returns the requested page of results
        :param inPageNumber: integer of the requested page
        :return: pysolr.Results class
        """

        try:
            if self.queryOK:
                return self.__RunQuery(inTable, inPageNumber)
        except Exception as e:
            QgsMessageLog.logMessage("QueryManager::getpage: Exception: {}".format(e))
            self.queryOK = False
            return pysolr.Results

    # ******************************************************************************************************************
    def __CreateCC3(self, inCC3=""):
        """
        Creates the FQ parameter to pass in to SOLR
        """

        if inCC3:
            if inCC3 == "QGIS":
                viewBounds = self.iface.mapCanvas().extent()
                xMin, yMin, xMax, yMax = self.__ConvertExtentToGeographic(viewBounds)

                # Swap the order to pass in since qgis is lat, long and solr is long, lat
                return "the_geom:[{},{} TO {},{}]".format(yMin, xMin, yMax, xMax)
            else:
                return "_cc3:{}".format(inCC3)

    # ******************************************************************************************************************
    def __RunQuery(self, inTable, inPageNumber=0):
        """
        Actually perform the internal query
        :param inPageNumber: int pagenumber
        :return: pysolr.Results class
        """

        if self.queryOK:
            return self.mySOLR[inTable].search(q=self.queryTerms, start=inPageNumber * self.rows, rows=self.rows)

    # ******************************************************************************************************************
    def __ConvertExtentToGeographic(self, inExtent):
        """
        Convert the canvas extent to geographic coordinates for SOLR
        :param inExtent: map extent
        :return: dictionary of converted coordinates
        """

        fromCRSString = QgsProject.instance().crs()
        toCRSString = "EPSG:4326"

        fromCRS = QgsCoordinateReferenceSystem(fromCRSString)
        toCRS = QgsCoordinateReferenceSystem(toCRSString)

        transform = QgsCoordinateTransform(fromCRS, toCRS, QgsProject.instance())

        newExtent = transform.transform(inExtent)

        return newExtent.xMinimum(), newExtent.yMinimum(), newExtent.xMaximum(), newExtent.yMaximum()
