# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QGISSolr
                                 A QGIS plugin
 This plugin allows the user to run and load SOLR queries into QGIS
                             -------------------
        begin                : 2018-04-02
        copyright            : (C) 2018 by Brian Maddox
        email                : brian.maddox@gmail.com
        git sha              : $Format:%H$
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
 This script initializes the plugin, making it known to QGIS.
"""


# noinspection PyPep8Naming
def classFactory(iface):  # pylint: disable=invalid-name
    """Load QGISSolr class from file QGISSolr.

    :param iface: A QGIS interface instance.
    :type iface: QgisInterface
    """
    #
    from .qgis_solr import QGISSolr
    return QGISSolr(iface)
