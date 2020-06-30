# -*- coding: utf-8 -*-
"""
TableManager.py holds the class TableManager that handles grabbing the SOLR tables on startup
"""

import requests
import configparser
import os
from qgis.core import QgsMessageLog


class TableManager(object):
    """
    Class to abstract handling with Tables.  Uses the SOLR api to get the list of tables and also their
    columns as necessary
    """

    # ******************************************************************************************************************
    def __init__(self, inSOLREndpoint: str, inSOLRTables: list):
        """
        Initialization
        """

        self.SOLREndpoint = inSOLREndpoint
        self.SOLRTables = inSOLRTables
        self.tableDict = dict()
        self.__SolrTables()

    # ******************************************************************************************************************
    def __SolrTables(self):
        """
        Populate the internal dicts for human names of tables
        :return: True on success
        """

        try:
            for tTable in self.SOLRTables:
                tempName = tTable.replace("_", " ")
                tempName = tempName.title()

                # Populate the human readable names
                self.tableDict[tTable] = tempName

        except Exception as e:
            QgsMessageLog.logMessage("TableManager::__SolrTables: Exception: {}".format(e))

    # ******************************************************************************************************************
    def GetSOLRTables(self) -> dict:
        """
        Returns the dictionary of the tables that we got from SOLR
        :return: Dictionary
        """

        return self.tableDict

    # ******************************************************************************************************************
    def GetTableColumns(self, inTableName: str) -> list:
        """
        Query Solr and get the schema.
        :return: list of Solr columns
        """

        try:
            coreName = inTableName.replace("_", "")

            returnList = list()
            tResponse = requests.get(self.SOLREndpoint + "/" + coreName + "/schema")

            if tResponse.json():
                for tColumn in tResponse.json()["schema"]["fields"]:
                    returnList.append(tColumn["name"])

            return returnList

        except Exception as e:
            QgsMessageLog.logMessage("TableManger:GetTableColumns: Exception: {}".format(e))
            return list()

