# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Tilgjengelighet
                                 A QGIS plugin
 My Tilgjengelighet assignment
                              -------------------
        begin                : 2017-08-21
        git sha              : $Format:%H$
        copyright            : (C) 2017 by Kasper Skjeggestad
        email                : kasper.skjeggestad@gmail.com
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
import sys
import os
import io

import urllib
import random
import tempfile
import string
import datetime
import operator
import codecs

from qgis.core import * #QgsDataSourceURI, QgsMapLayerRegistry, QgsVectorLayer, QgsExpression, QgsFeatureRequest, QgsVectorFileWriter, QgsLayerTreeLayer, QgsLayerTreeGroup, QgsMapLayer, QgsProject, QgsFeature, QGis
from PyQt4.QtCore import * #QSettings, QTranslator, qVersion, QCoreApplication, QPyNullVariant, QDateTime, QThread, pyqtSignal, Qt, QRect, QSize, QFileInfo
from PyQt4.QtGui import * #QAction, QIcon, QDockWidget, QGridLayout, QLineEdit, QTableWidget, QTableWidgetItem, QMessageBox, QApplication, QHBoxLayout, QVBoxLayout, QAbstractItemView, QListWidgetItem, QAbstractItemView, QFileDialog, QLabel, QPixmap, QIcon
from PyQt4.QtNetwork import QHttp
from qgis.gui import QgsRubberBand, QgsMessageBar
from osgeo import gdal
from osgeo import ogr


# Initialize Qt resources from file resources.py
import resources_rc

# Import the code for the dialog
from Tilgjengelighet_dialog import TilgjengelighetDialog
from tabledialog import TableDialog
from infoWidgetDialog import infoWidgetDialog

from AttributeForm import AttributeForm #Storing user made attribute information
from SavedSearch import SavedSearch #Save search choises for later use

#from xytools
from xytools.field_chooser import FieldChooserDialog
from xytools.exportlayerdialog import exportLayerDialog
from xytools import utils

#from OpenLayers plugin
from openlayers_plugin.openlayers_layer import OpenlayersLayer
from openlayers_plugin.weblayers.weblayer_registry import WebLayerTypeRegistry
from openlayers_plugin.weblayers.weblayer_registry import WebLayerTypeRegistry
from openlayers_plugin.weblayers.google_maps import OlGooglePhysicalLayer, OlGoogleStreetsLayer, OlGoogleHybridLayer, OlGoogleSatelliteLayer
from openlayers_plugin.weblayers.osm import OlOpenStreetMapLayer, OlOSMHumanitarianDataModelLayer
from openlayers_plugin.weblayers.osm_thunderforest import OlOpenCycleMapLayer, OlOCMLandscapeLayer, OlOCMPublicTransportLayer, OlOCMOutdoorstLayer, OlOCMTransportDarkLayer, OlOCMSpinalMapLayer, OlOCMPioneerLayer, OlOCMMobileAtlasLayer, OlOCMNeighbourhoodLayer
from openlayers_plugin.weblayers.bing_maps import OlBingRoadLayer, OlBingAerialLayer, OlBingAerialLabelledLayer
from openlayers_plugin.weblayers.apple_maps import OlAppleiPhotoMapLayer
from openlayers_plugin.weblayers.osm_stamen import OlOSMStamenTonerLayer, OlOSMStamenTonerLiteLayer, OlOSMStamenWatercolorLayer, OlOSMStamenTerrainLayer
from openlayers_plugin.weblayers.wikimedia_maps import WikimediaLabelledLayer, WikimediaUnLabelledLayer


class Tilgjengelighet:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        self.canvas = self.iface.mapCanvas()
        self.settings = QSettings()
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        self.plugin_path = os.path.dirname(os.path.realpath(__file__))
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        self.dir = os.path.dirname(__file__)
        self.locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'Tilgjengelighet_{}.qm'.format(locale))

        if os.path.exists(self.locale_path):
            self.translator = QTranslator()
            self.translator.load(self.locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)


        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&Kartverket Tilgjengelighet')
        self.toolbar = self.iface.addToolBar(u'Tilgjengelighet')
        self.toolbar.setObjectName(u'Tilgjengelighet')

        
        #WFS URLS
        self.namespace = "http://skjema.geonorge.no/SOSI/produktspesifikasjon/TilgjengelighetTettsted/4.5"
        self.namespace_prefix = "app"
        self.online_resource = "https://wfs.geonorge.no/skwms1/wfs.tilgjengelighettettsted"

        #Globale Variabler
        self.uspesifisert = u"" #For emty comboboxses and lineEdtis
        self.mer = u">" #for combobokser linked to more or less iterations
        self.mindre = u"<"
        self.mer_eller_lik = u">="
        self.mindre_eller_lik = u"<="

        #layers and search
        self.layers = [] #gather all baselayers

        self.current_search_layer = None #The last searched layer
        self.current_attributes = None
        self.search_history = {} #history of all search
        self.rubberHighlight = None 

        self.feature_type_tettsted = { u"HC-Parkering" : u'TettstedHCparkering', u"Inngang" : u'TettstedInngangBygg', u'Parkeringsomr\xe5de' : u'TettstedParkeringsomr\xe5de', u"Vei" : u'TettstedVei'}

        #Icons
        self.icon_rullestol_tilgjengelig = QPixmap('icons/Tilgjengelig.png')#QIcon(':/plugins/Tilgjengelighet/icons/Tilgjengelig.png')
        self.icon_rullestol_ikkeTilgjengelig = QPixmap('icons/IkkeTilgjengelig.png')#QIcon(':/plugins/Tilgjengelighet/icons/IkkeTilgjengelig.png')
        self.icon_rullestol_vansekligTilgjengelig = QPixmap('icons/VanskeligTilgjengelig.png')#QIcon(':/plugins/Tilgjengelighet/icons/VanskeligTilgjengelig.png')
        self.icon_rullestol_ikkeVurdert = QPixmap('icons/IkkeVurdert.png')#QIcon(':/plugins/Tilgjengelighet/icons/IkkeVurdert.png')
        self.icons_rullestol = {"tilgjengelig" : self.icon_rullestol_tilgjengelig, "ikkeTilgjengelig" : self.icon_rullestol_ikkeTilgjengelig, "vanskeligTilgjengelig" : self.icon_rullestol_vansekligTilgjengelig, "ikkeVurdert" : self.icon_rullestol_ikkeTilgjengelig}

        self.icon_elrullestol_tilgjengelig = QPixmap('icons/TilgjengeligEl.png')#QIcon(':/plugins/Tilgjengelighet/icons/TilgjengeligEl.png')
        self.icon_elrullestol_ikkeTilgjengelig = QPixmap('icons/IkkeTilgjengeligEl.png')#QIcon(':/plugins/Tilgjengelighet/icons/IkkeTilgjengeligEl.png')
        self.icon_elrullestol_vansekligTilgjengelig = QPixmap('icons/VanskeligTilgjengeligEl.png')#QIcon(':/plugins/Tilgjengelighet/icons/VanskeligTilgjengeligEl.png')
        self.icon_elrullestol_ikkeVurdert = QPixmap('icons/IkkeVurdertEl.png')#QIcon(':/plugins/Tilgjengelighet/icons/IkkeVurdertEl.png')
        self.icons_elrullestol = {"tilgjengelig" : self.icon_elrullestol_tilgjengelig, "ikkeTilgjengelig" : self.icon_elrullestol_ikkeTilgjengelig, "vanskeligTilgjengelig" : self.icon_elrullestol_vansekligTilgjengelig, "ikkeVurdert" : self.icon_elrullestol_ikkeTilgjengelig}

        self.icon_syn_tilgjengelig = QPixmap('icons/TilgjengeligSyn.png')#QIcon(':/plugins/Tilgjengelighet/icons/TilgjengeligSyn.png')
        self.icon_syn_ikkeTilgjengelig = QPixmap('icons/IkkeTilgjengeligSyn.png')#QIcon(':/plugins/Tilgjengelighet/icons/IkkeTilgjengeligSyn.png')
        self.icon_syn_vansekligTilgjengelig = QPixmap('icons/VanskeligTilgjengeligSyn.png')#QIcon(':/plugins/Tilgjengelighet/icons/VanskeligTilgjengeligSyn.png')
        self.icon_syn_ikkeVurdert = QPixmap('icons/IkkeVurdertSyn.png')#QIcon(':/plugins/Tilgjengelighet/icons/IkkeVurdertSyn.png')
        self.icons_syn = {"tilgjengelig" : self.icon_syn_tilgjengelig, "ikkeTilgjengelig" : self.icon_syn_ikkeTilgjengelig, "vanskeligTilgjengelig" : self.icon_syn_vansekligTilgjengelig, "ikkeVurdert" : self.icon_syn_ikkeTilgjengelig}

        self.icons = [self.icons_rullestol, self.icons_elrullestol, self.icons_syn]

        #to hide layers
        self.ltv = self.iface.layerTreeView()
        self.model = self.ltv.model()
        self.root = QgsProject.instance().layerTreeRoot()

        ##############################TEST#######################

        self._olLayerTypeRegistry = WebLayerTypeRegistry(self)
        self._ol_layers = []


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
        return QCoreApplication.translate('Tilgjengelighet', message)


    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None):
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

        # Create the dialog (after translation) and keep reference
        self.dlg = TilgjengelighetDialog() #main dialig

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
            self.iface.addPluginToMenu(
                self.menu,
                action)
            self.iface.addPluginToWebMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/Tilgjengelighet/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Kartverkets Tilgjengelighets database'),
            callback=self.run,
            parent=self.iface.mainWindow())


        #main window
        self.dlg.tabWidget_main.setTabIcon(0, QIcon(":/plugins/Tilgjengelighet/icons/friluft.png"))
        self.dlg.tabWidget_main.setTabIcon(1, QIcon(":/plugins/Tilgjengelighet/icons/tettsted.png"))

        self.dlg.tabWidget_main.currentChanged.connect(self.change_search_name) #change search name based on tab
        self.dlg.tabWidget_friluft.currentChanged.connect(self.change_search_name)
        self.dlg.tabWidget_tettsted.currentChanged.connect(self.change_search_name)

        self.dlg.pushButton_HentData.clicked.connect(self.hentData) #collecting datata for inngangbygg

        self.dlg.pushButton_reset.clicked.connect(self.reset) #resett all choses

        self.dlg.label_Progress.setVisible(False)

        #table window
        self.dock = TableDialog(self.iface.mainWindow())
        self.dock.tableWidget.setSelectionBehavior(QAbstractItemView.SelectRows) #select entire row in table
        self.dock.tableWidget.setEditTriggers(QAbstractItemView.NoEditTriggers) #Making table unediteble

        self.dock.tableWidget.itemClicked.connect(self.table_item_clicked) #what happens when an item is clicked in table
        self.iface.addDockWidget( Qt.BottomDockWidgetArea , self.dock ) #adding seartch result Widget
        self.dock.close()

        #info window
        self.infoWidget = infoWidgetDialog(self.iface.mainWindow())
        self.infoWidget.pushButton_filtrer.clicked.connect(lambda x: self.dlg.show()) #open main window
        self.infoWidget.pushButton_filtrer.clicked.connect(self.get_previus_search_activeLayer) #setting main window to match search for active layer
        self.infoWidget.pushButton_next.clicked.connect(self.infoWidget_next) #itterate the selected objekts
        self.infoWidget.pushButton_prev.clicked.connect(self.infoWidget_prev)
        #self.infoWidget.pushButton_tabell.clicked.connect(self.show_tabell)

        self.selectPolygon = QAction(QIcon(":/plugins/Tilgjengelighet/icons/Tilgjengelig.png"),
                                       QCoreApplication.translate("MyPlugin", "Polygon"),
                                       self.iface.mainWindow())
        self.selectPoint = QAction(QIcon(":/plugins/Tilgjengelighet/icon"),
                                       QCoreApplication.translate("MyPlugin", "Punkt/Frihånd"),
                                       self.iface.mainWindow()) 
        self.selectPolygon.triggered.connect(lambda x: self.iface.actionSelectPolygon().trigger()) #select objects by polygon
        self.selectPoint.triggered.connect(lambda x: self.iface.actionSelectFreehand().trigger()) #select objects by freehand

        self.infoWidget.toolButton_velgikart.addAction(self.selectPolygon)
        self.infoWidget.toolButton_velgikart.addAction(self.selectPoint)

        self.exportExcel = QAction(QIcon(":/plugins/Tilgjengelighet/icons/Tilgjengelig.png"),
                                       QCoreApplication.translate("MyPlugin", "Excel"),
                                       self.iface.mainWindow()) 
        self.exportImage = QAction(QIcon(":/plugins/Tilgjengelighet/icon"),
                                       QCoreApplication.translate("MyPlugin", "Bilde"),
                                       self.iface.mainWindow()) 
        self.exportExcel.triggered.connect(self.excelSave) #export tp excel
        self.exportImage.triggered.connect(self.imageSave) #ecport image

        self.infoWidget.toolButton_eksporter.addAction(self.exportExcel)
        self.infoWidget.toolButton_eksporter.addAction(self.exportImage)

        self.iface.addDockWidget( Qt.BottomDockWidgetArea , self.infoWidget ) #adding seartch result Widget
        self.infoWidget.close()


        #Export window
        self.export_layer = exportLayerDialog()
        self.export_layer.pushButton_bla.clicked.connect(self.OpenBrowser)
        self.export_layer.pushButton_lagre.clicked.connect(self.lagre_lag)
        self.export_layer.pushButton_lagre.clicked.connect(lambda x: self.export_layer.close()) #close winwo when you have saved layer
        self.export_layer.pushButton_avbryt.clicked.connect(lambda x: self.export_layer.close())
        
        self.fill_fylker() #fill fylker combobox

        #set combobox functions
        self.dlg.comboBox_fylker.currentIndexChanged.connect(self.fylke_valgt) #Filling cityes from county
        self.dlg.comboBox_fylker.currentIndexChanged.connect(self.change_search_name) #setting search name based on fylke
        self.dlg.comboBox_komuner.currentIndexChanged.connect(self.change_search_name) #setting search name based on komune

        self.fylker = AttributeForm("fylker")
        self.fylker.setComboBox(self.dlg.comboBox_fylker)
        self.kommuner = AttributeForm("komune")
        self.kommuner.setComboBox(self.dlg.comboBox_komuner)


        #Create attributes object tettsted
        self.assign_combobox_inngang()
        self.assign_combobox_vei()
        self.assign_combobox_hc_parkering()
        self.assign_combobox_parkeringsomraade()

        self.attributes_tettsted = { u"HC-Parkering" : self.attributes_hcparkering, u"Inngang" : self.attributes_inngang, u'Parkeringsområde' : self.attributes_pomrade, u"Vei" : self.attributes_vei}

        #self.dlg.pushButton_filtrer.clicked.connect(self.filtrer) #Filtering out the serach and show results
        self.dlg.pushButton_filtrer.clicked.connect(self.newFilter)

        self.openLayer_background_init()

        ############################################################################################################

    def openLayer_background_init(self):
        """The folowing code has been taken out from OpenLayers Plugin writen by Sourcepole"""
        self._olMenu = QMenu("OpenLayers plugin")

        self._olLayerTypeRegistry.register(OlOpenStreetMapLayer())
        self._olLayerTypeRegistry.register(OlOpenCycleMapLayer())
        self._olLayerTypeRegistry.register(OlOCMLandscapeLayer())
        self._olLayerTypeRegistry.register(OlOCMPublicTransportLayer())

        # ID 8-10 was Yahoo
        self._olLayerTypeRegistry.register(OlOSMHumanitarianDataModelLayer())

        self._olLayerTypeRegistry.register(OlBingRoadLayer())
        self._olLayerTypeRegistry.register(OlBingAerialLayer())
        self._olLayerTypeRegistry.register(OlBingAerialLabelledLayer())

        # Order from here on is free. Layers 0-14 should keep order for
        # compatibility with OL Plugin < 2.3

        self._olLayerTypeRegistry.register(OlOSMStamenTonerLayer())
        self._olLayerTypeRegistry.register(OlOSMStamenTonerLiteLayer())
        self._olLayerTypeRegistry.register(OlOSMStamenWatercolorLayer())
        self._olLayerTypeRegistry.register(OlOSMStamenTerrainLayer())

        self._olLayerTypeRegistry.register(OlAppleiPhotoMapLayer())

        self._olLayerTypeRegistry.register(WikimediaLabelledLayer())
        self._olLayerTypeRegistry.register(WikimediaUnLabelledLayer())

        for group in self._olLayerTypeRegistry.groups():
            #print("group: ", group)
            groupMenu = group.menu()
            for layer in self._olLayerTypeRegistry.groupLayerTypes(group):
                #print("layer: ", layer)
                layer.addMenuEntry(groupMenu, self.iface.mainWindow())
            self._olMenu.addMenu(groupMenu)

        #self.addOLmenu()
        self.infoWidget.toolButton_map.setMenu(self._olMenu)


    #####################################################################
    #TEST
    def addLayer(self, layerType):
        """The folowing code has been taken out from OpenLayers Plugin writen by Sourcepole"""
        if layerType.hasGdalTMS():
            # create GDAL TMS layer
            layer = self.createGdalTmsLayer(layerType, layerType.displayName)
        else:
            # create OpenlayersLayer
            layer = OpenlayersLayer(self.iface, self._olLayerTypeRegistry)
            layer.setLayerName(layerType.displayName)
            layer.setLayerType(layerType)

        if layer.isValid():
            if len(self._ol_layers) > 0:
                QgsMapLayerRegistry.instance().removeMapLayers( [self._ol_layers[0].id()] )
                self._ol_layers.remove(self._ol_layers[0])
            coordRefSys = layerType.coordRefSys(self.canvasCrs())
            self.setMapCrs(coordRefSys)
            QgsMapLayerRegistry.instance().addMapLayer(layer, False)
            self._ol_layers += [layer]

            # last added layer is new reference
            self.setReferenceLayer(layer)

            if not layerType.hasGdalTMS():
                msg = "Printing and rotating of Javascript API " \
                      "based layers is currently not supported!"
                self.iface.messageBar().pushMessage(
                    "OpenLayers Plugin", msg, level=QgsMessageBar.WARNING,
                    duration=5)

            #Set background mat at bacground
            root = QgsProject.instance().layerTreeRoot()
            root.insertLayer(-1, layer)

    def setReferenceLayer(self, layer):
        """The folowing code has been taken out from OpenLayers Plugin writen by Sourcepole"""
        self.layer = layer

    def createGdalTmsLayer(self, layerType, name):
        """The folowing code has been taken out from OpenLayers Plugin writen by Sourcepole"""

        # create GDAL TMS layer with XML string as datasource
        layer = QgsRasterLayer(layerType.gdalTMSConfig(), name)
        layer.setCustomProperty('ol_layer_type', layerType.layerTypeName)
        return layer

    def canvasCrs(self):
        """The folowing code has been taken out from OpenLayers Plugin writen by Sourcepole"""
        mapCanvas = self.iface.mapCanvas()
        if QGis.QGIS_VERSION_INT >= 20300:
            #crs = mapCanvas.mapRenderer().destinationCrs()
            crs = mapCanvas.mapSettings().destinationCrs()
        elif QGis.QGIS_VERSION_INT >= 10900:
            crs = mapCanvas.mapRenderer().destinationCrs()
        else:
            crs = mapCanvas.mapRenderer().destinationSrs()
        return crs

    def setMapCrs(self, coordRefSys):
        """The folowing code has been taken out from OpenLayers Plugin writen by Sourcepole"""
        mapCanvas = self.iface.mapCanvas()
        # On the fly
        if QGis.QGIS_VERSION_INT >= 20300:
            #mapCanvas.setCrsTransformEnabled(True)
            pass
        else:
            #mapCanvas.mapRenderer().setProjectionsEnabled(True)
            pass
        canvasCrs = self.canvasCrs()
        if canvasCrs != coordRefSys:
            coordTrans = QgsCoordinateTransform(canvasCrs, coordRefSys)
            extMap = mapCanvas.extent()
            extMap = coordTrans.transform(extMap, QgsCoordinateTransform.ForwardTransform)
            if QGis.QGIS_VERSION_INT >= 20300:
                #mapCanvas.setDestinationCrs(coordRefSys)
                pass
            elif QGis.QGIS_VERSION_INT >= 10900:
                #mapCanvas.mapRenderer().setDestinationCrs(coordRefSys)
                pass
            else:
                #mapCanvas.mapRenderer().setDestinationSrs(coordRefSys)
                pass
            #mapCanvas.freeze(False)
            #mapCanvas.setMapUnits(coordRefSys.mapUnits())
            #mapCanvas.setExtent(extMap)




    ###########################################################################



    #def addOLmenu(self):
    #    openLayers = OpenlayersPlugin(self.iface, self.infoWidget)
    #    openLayers.initGui()
        
        #self.infoWidget.toolButton_map.connect(self.showOLmenu)
    #    self.infoWidget.toolButton_map.triggered(self.infoWidget.toolButton_map.showMenu())

    #def showOLmenu(self):
    #    self.infoWidget.toolButton_map.showMenu()
        

    def resolve(name, basepath=None):
        if not basepath:
          basepath = os.path.dirname(os.path.realpath(__file__))
        return os.path.join(basepath, name)


    def assign_combobox_inngang(self):
        """Assigning a AttributeForm object to each option in inngang"""
        
        self.avstandHC = AttributeForm("avstandHC", self.dlg.comboBox_avstand_hc, self.dlg.lineEdit_avstand_hc)
        self.ank_stigning = AttributeForm("stigningAdkomstvei", self.dlg.comboBox_ank_stigning, self.dlg.lineEdit_ank_stigning)
        self.byggningstype = AttributeForm("funksjon", self.dlg.comboBox_byggningstype)
        self.rampe = AttributeForm("rampe", self.dlg.comboBox_rampe, comboBoxText={"" : "", "Ja" : "1", "Nei" : "0"})
        self.dortype = AttributeForm(u'dørtype', self.dlg.comboBox_dortype)
        self.dorapner = AttributeForm(u'døråpner', self.dlg.comboBox_dorapner)
        self.man_hoyde = AttributeForm(u'manøverknappHøyde', self.dlg.comboBox_man_hoyde, self.dlg.lineEdit_man_hoyde)
        self.dorbredde = AttributeForm("InngangBredde", self.dlg.comboBox_dorbredde, self.dlg.lineEdit_dorbredde)
        self.terskel = AttributeForm(u'terskelH\xf8yde', self.dlg.comboBox_terskel, self.dlg.lineEdit_terskel)
        self.kontrast = AttributeForm("kontrast", self.dlg.comboBox_kontrast)
        self.rampe_stigning = AttributeForm("rampeStigning", self.dlg.comboBox_rmp_stigning, self.dlg.lineEdit_rmp_stigning)
        self.rampe_bredde = AttributeForm("rampeBredde", self.dlg.comboBox_rmp_bredde, self.dlg.lineEdit_rmp_bredde)
        self.handlist = AttributeForm(u'h\xe5ndlist', self.dlg.comboBox_handliste)
        self.handlist1 = AttributeForm(u'h\xe5ndlistH\xf8yde1', self.dlg.comboBox_hand1, self.dlg.lineEdit_hand1)
        self.handlist2 = AttributeForm(u'h\xe5ndlistH\xf8yde2', self.dlg.comboBox_hand2, self.dlg.lineEdit_hand2)
        self.rmp_tilgjengelig = AttributeForm("rampeTilgjengelig", self.dlg.comboBox_rmp_tilgjengelig)
        self.manuellRullestol = AttributeForm("tilgjengvurderingRullestol", self.dlg.comboBox_manuell_rullestol)
        self.elektriskRullestol = AttributeForm("tilgjengvurderingElRull", self.dlg.comboBox_el_rullestol)
        self.synshemmet = AttributeForm("tilgjengvurderingSyn", self.dlg.comboBox_syn)

        self.attributes_inngang = [self.avstandHC, self.ank_stigning, self.byggningstype, self.rampe, self.dortype, self.dorapner, self.man_hoyde, self.dorbredde, self.terskel, self.kontrast, self.rampe_stigning, self.rampe_bredde, self.handlist, self.handlist1, self.handlist2, self.rmp_tilgjengelig, self.manuellRullestol, self.elektriskRullestol, self.synshemmet]
        self.attributes_inngang_gui = [self.byggningstype, self.dortype, self.dorapner, self.kontrast, self.handlist, self.rmp_tilgjengelig, self.manuellRullestol, self.elektriskRullestol, self.synshemmet]
        self.attributes_inngang_mer_mindre = [self.avstandHC, self.ank_stigning, self.man_hoyde, self.dorbredde, self.terskel, self.rampe_stigning, self.rampe_bredde, self.handlist1, self.handlist2]

        #fyll combobox
        path = ":/plugins/Tilgjengelighet/"
        for attributt in self.attributes_inngang_mer_mindre:
            attributt.getComboBox().clear()
            self.fill_combobox(attributt.getComboBox(), self.plugin_dir + '\mer_mindre.txt')

        self.fill_combobox(self.rampe.getComboBox(), self.plugin_dir + r'\boolean.txt')
        self.fill_combobox(self.byggningstype.getComboBox(), self.plugin_dir + r"\tettstedInngangByggningstype.txt")
        self.fill_combobox(self.dortype.getComboBox(), self.plugin_dir + r"\tettstedInngangdortype.txt")
        self.fill_combobox(self.dorapner.getComboBox(), self.plugin_dir + r"\tettstedInngangDorapner.txt")
        self.fill_combobox(self.kontrast.getComboBox(), self.plugin_dir + r"\tettstedInngangKontrast.txt")
        self.fill_combobox(self.handlist.getComboBox(), self.plugin_dir + r"\tettstedInngangHandlist.txt")
        self.fill_combobox(self.rmp_tilgjengelig.getComboBox(), self.plugin_dir + r"\tettstedInngangTilgjengvurdering.txt")
        self.fill_combobox(self.manuellRullestol.getComboBox(), self.plugin_dir + r"\tettstedInngangTilgjengvurdering.txt")
        self.fill_combobox(self.elektriskRullestol.getComboBox(), self.plugin_dir + r"\tettstedInngangTilgjengvurdering.txt")
        self.fill_combobox(self.synshemmet.getComboBox(), self.plugin_dir + r"\tettstedInngangTilgjengvurdering.txt")

        # def fill_fylker(self):
        #     """Fill up the combobox fylker with fylker from komm.txt"""
        #     self.dlg.comboBox_fylker.clear()
        #     self.dlg.comboBox_fylker.addItem("Norge")

        #     filename = self.plugin_dir + "\komm.txt"
        #     self.komm_dict_nr = {}
        #     self.komm_dict_nm = {}
        #     self.fylke_dict = {}

        #     with io.open(filename, 'r', encoding='utf-8') as f:
        #         for line in f:
        #             komm_nr, komune, fylke = line.rstrip('\n').split(("\t"))
        #             komm_nr = self.to_unicode(komm_nr)
        #             komune = self.to_unicode(komune)
        #             fylke = self.to_unicode(fylke)

        #             self.komm_dict_nr[komm_nr] = komune
        #             self.komm_dict_nm[komune] = komm_nr
        #             if not fylke in self.fylke_dict:
        #                 self.fylke_dict[fylke] = []
        #                 self.dlg.comboBox_fylker.addItem(fylke)

        #             self.fylke_dict[fylke].append(komm_nr)



        #hide gui options
        self.dlg.label_rampe_boxs.setVisible(False)

        self.dlg.lineEdit_rmp_stigning.setVisible(False)
        self.dlg.comboBox_rmp_stigning.setVisible(False)
        self.dlg.label_rmp_stigning.setVisible(False)

        self.dlg.lineEdit_rmp_bredde.setVisible(False)
        self.dlg.comboBox_rmp_bredde.setVisible(False)
        self.dlg.label_rmp_bredde.setVisible(False)

        self.dlg.comboBox_handliste.setVisible(False)
        self.dlg.label_handliste.setVisible(False)

        self.dlg.lineEdit_hand1.setVisible(False)
        self.dlg.comboBox_hand1.setVisible(False)
        self.dlg.label_hand1.setVisible(False)

        self.dlg.lineEdit_hand2.setVisible(False)
        self.dlg.comboBox_hand2.setVisible(False)
        self.dlg.label_hand2.setVisible(False)

        self.dlg.comboBox_rmp_tilgjengelig.setVisible(False)
        self.dlg.label_rmp_tilgjengelig.setVisible(False)

        self.dlg.line_4.setVisible(False)
        self.dlg.line.setVisible(False)

        self.dlg.comboBox_rampe.currentIndexChanged.connect(self.hide_show_rampe)

    def assign_combobox_vei(self):
        """Assigning a AttributeForm object to each option in vei"""

        self.gatetype = AttributeForm("gatetype", self.dlg.comboBox_gatetype)
        self.nedsenkning1 = AttributeForm("nedsenk1", self.dlg.comboBox_nedsenkning1, self.dlg.lineEdit_nedsenkning1)
        self.nedsenkning2 = AttributeForm("nedsenk2", self.dlg.comboBox_nedsenkning2, self.dlg.lineEdit_nedsenkning2)
        self.dekke_vei_tettsted = AttributeForm("dekke", self.dlg.comboBox_dekke_vei_tettsted)
        self.dekkeTilstand_vei_tettsted = AttributeForm("dekkeTilstand", self.dlg.comboBox_dekkeTilstand_vei_tettsted)
        self.bredde = AttributeForm("bredde", self.dlg.comboBox_bredde, self.dlg.lineEdit_bredde)
        self.stigning = AttributeForm("stigning", self.dlg.comboBox_stigning, self.dlg.lineEdit_stigning)
        self.tverfall = AttributeForm("tverrfall", self.dlg.comboBox_tverfall, self.dlg.lineEdit_tverfall)
        self.ledelinje = AttributeForm("ledelinje", self.dlg.comboBox_ledelinje)
        self.ledelinjeKontrast = AttributeForm("ledelinjeKontrast", self.dlg.comboBox_ledelinjeKontrast)

        self.manuell_rullestol_vei = AttributeForm("tilgjengvurderingRullestol", self.dlg.comboBox_manuell_rullestol_vei)
        self.electrisk_rullestol_vei = AttributeForm("tilgjengvurderingElRull", self.dlg.comboBox_electrisk_rullestol_vei)
        self.syn_vei = AttributeForm("tilgjengvurderingSyn", self.dlg.comboBox_syn_vei)

        self.attributes_vei = [self.gatetype, self.nedsenkning1, self.nedsenkning2, self.dekke_vei_tettsted, self.dekkeTilstand_vei_tettsted, self.bredde, self.stigning, self.tverfall, self.ledelinje, self.ledelinjeKontrast, self.manuell_rullestol_vei, self.electrisk_rullestol_vei, self.syn_vei]
        self.attributes_vei_gui = [self.gatetype, self.dekke_vei_tettsted, self.dekkeTilstand_vei_tettsted, self.ledelinje, self.ledelinjeKontrast, self.manuell_rullestol_vei, self.electrisk_rullestol_vei, self.syn_vei]
        self.attributes_vei_mer_mindre = [self.nedsenkning1,self.nedsenkning2,self.bredde,self.stigning,self.tverfall]

        #Hide GUI
        self.dlg.comboBox_nedsenkning1.setVisible(False)
        self.dlg.lineEdit_nedsenkning1.setVisible(False)
        self.dlg.label_nedsenkning1.setVisible(False)
        self.dlg.comboBox_nedsenkning2.setVisible(False)
        self.dlg.lineEdit_nedsenkning2.setVisible(False)
        self.dlg.label_nedsenkning2.setVisible(False)

        self.dlg.comboBox_gatetype.currentIndexChanged.connect(self.hide_show_nedsenkning)

    def assign_combobox_hc_parkering(self):
        """Assigning a AttributeForm object to each option in hc parkering"""

        self.avstandServicebygg = AttributeForm("avstandServicebygg", self.dlg.comboBox_avstandServicebygg, self.dlg.lineEdit_avstandServicebygg)

        self.overbygg = AttributeForm("overbygg", self.dlg.comboBox_overbygg, comboBoxText={"" : "", "Ja" : "1", "Nei" : "0"})
        self.skiltet = AttributeForm("skiltet", self.dlg.comboBox_skiltet, comboBoxText={"" : "", "Ja" : "1", "Nei" : "0"})
        self.merket = AttributeForm("merket", self.dlg.comboBox_merket, comboBoxText={"" : "", "Ja" : "1", "Nei" : "0"})

        self.bredde_vei = AttributeForm("bredde", self.dlg.comboBox_bredde_vei, self.dlg.lineEdit_bredde_vei)
        self.lengde_vei = AttributeForm("lengde", self.dlg.comboBox_lengde_vei, self.dlg.lineEdit_lengde_vei)

        self.manuell_rullestol_hcparkering = AttributeForm("tilgjengvurderingRullestol", self.dlg.comboBox_manuell_rullestol_hcparkering)
        self.elektrisk_rullestol_hcparkering = AttributeForm("tilgjengvurderingElRull", self.dlg.comboBox_elektrisk_rullestol_hcparkering)

        self.attributes_hcparkering = [self.avstandServicebygg, self.overbygg, self.skiltet, self.merket, self.bredde_vei, self.lengde_vei, self.manuell_rullestol_hcparkering, self.elektrisk_rullestol_hcparkering]
        self.attributes_hcparkering_gui = [self.manuell_rullestol_hcparkering, self.elektrisk_rullestol_hcparkering]
        self.attributes_hcparkering_mer_mindre = [self.avstandServicebygg, self.bredde_vei, self.lengde_vei]

        #Hide GUI
        self.dlg.label_bredde_vei.setVisible(False)
        self.dlg.comboBox_bredde_vei.setVisible(False)
        self.dlg.lineEdit_bredde_vei.setVisible(False)
        self.dlg.label_lengde_vei.setVisible(False)
        self.dlg.comboBox_lengde_vei.setVisible(False)
        self.dlg.lineEdit_lengde_vei.setVisible(False)

        self.dlg.comboBox_merket.currentIndexChanged.connect(self.hide_show_merket)

    def assign_combobox_parkeringsomraade(self):
        """Assigning a AttributeForm object to each option in parkeringsområde"""

        self.overbygg_pomrade = AttributeForm("overbygg", self.dlg.comboBox_overbygg_pomrade, comboBoxText={"" : "", "Ja" : "1", "Nei" : "0"})
        self.kapasitetPersonbiler = AttributeForm("kapasitetPersonbiler", self.dlg.comboBox_kapasitetPersonbiler, self.dlg.lineEdit_kapasitetPersonbiler)
        self.kapasitetUU = AttributeForm("kapasitetUU", self.dlg.comboBox_kapasitetUU, self.dlg.lineEdit_kapasitetUU)
        self.dekke_pomrade = AttributeForm("dekke", self.dlg.comboBox_dekke_pomrade)
        self.dekkeTilstand_pomrade = AttributeForm("dekkeTilstand", self.dlg.comboBox_dekkeTilstand_pomrade)

        self.manuell_rullestol_pomrade = AttributeForm("tilgjengvurderingRullestol", self.dlg.comboBox_manuell_rullestol_pomrade)

        self.attributes_pomrade = [self.overbygg_pomrade, self.kapasitetPersonbiler, self.kapasitetUU, self.dekke_pomrade, self.dekkeTilstand_pomrade, self.manuell_rullestol_pomrade]
        self.attributes_pomrade_gui = [self.dekke_pomrade, self.dekkeTilstand_pomrade, self.manuell_rullestol_pomrade]
        self.attributes_pomrade_mer_mindre = [self.kapasitetPersonbiler, self.kapasitetUU]


    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginWebMenu(
                self.tr(u'&Kartverket Tilgjengelighet'),
                action)
            self.iface.removeToolBarIcon(action)
        # remove the toolbar
        del self.toolbar


    def get_temppath(self, filename):
        """Creating a temperarly path for a temperary file
        :param filename: String name for file
        :type filename: str, QString

        :returns: string of full path
        :rtype: str
        """

        tmpdir = os.path.join(tempfile.gettempdir(),'Tilgjengelighet')
        if not os.path.exists(tmpdir):
            os.makedirs(tmpdir)
        tmpfile= os.path.join(tmpdir, filename)
        return tmpfile


    def to_unicode(self, in_string):
        """Transforme string to unicode

        :param in_string: String to transforme

        :returns: unicode verson of string
        :rtype: unicode
        """
        if isinstance(in_string,str):
            out_string = in_string.decode('utf-8')
        elif isinstance(in_string,unicode):
            out_string = in_string
        else:
            raise TypeError('not stringy')
        return out_string


    def updateDataReadProgress(self, bytesRead, totalBytes):
        """Updates the dataprogess of downwloading data"""

        self.dlg.label_Progress.setVisible(True)
        self.dlg.label_Progress.setText("Laster inn data: ") # + self.featuretype.getFeatureType())

    def httpRequestStartet(self):
        """Calls when reqest has started"""

        print("The Request has started!")


    def httpRequestFinished(self, requestId, error):
        """Calls when reqest is finnished"""

        if requestId != self.httpGetId:
            print("requesrtd Id != httpGetId")
            return
        
        self.outFile.close()
        
        if error:
            print("error in requestFinished")
            print(self.http.errorString())
            print(type(error))
            self.outFile.remove()
        else:
            print('No error')
            gdaltimeout = "5"
            gdal.SetConfigOption("GDAL_HTTP_TIMEOUT", gdaltimeout)
            gdal.SetConfigOption('GML_SKIP_RESOLVE_ELEMS', 'ALL')
            gdal.SetConfigOption('GML_ATTRIBUTES_TO_OGR_FIELDS', 'NO')
            nasdetectionstring = 'asdf/asdf/asdf'
            gdal.SetConfigOption('NAS_INDICATOR', nasdetectionstring)
            
            ogrdriver = ogr.GetDriverByName("GML")
            ogrdatasource = ogrdriver.Open(self.outFile.fileName())
            
            if ogrdatasource is None:
                print("ogrdatasource is None")
            else: # Determine the LayerCount
                print("ogrdatasource is some")
                ogrlayercount = ogrdatasource.GetLayerCount()
                print("ogrlayercount: ", ogrlayercount)
                #for i in range(0, ogrlayercount):
                if ogrlayercount > 0:
                    print("no for i in range(0, ogrlayercount): loop")
                    #j = ogrlayercount -1 - i
                    j = ogrlayercount -1 - 0
                    ogrlayer = ogrdatasource.GetLayerByIndex(j)
                    ogrlayername = ogrlayer.GetName()
                    ogrgeometrytype = ogrlayer.GetGeomType()
                    geomtypeids = []
                    
                    if ogrgeometrytype==0:
                        geomtypeids = ["1", "2", "3", "100"]
                    else:
                        geomtypeids = [str(ogrgeometrytype)]
                    
                    for geomtypeid in geomtypeids:
                        print("geomtypeid: ", geomtypeid)
                        #qgislayername = ogrlayername
                        qgislayername = self.layer_name
                        uri = self.outFile.fileName() + "|layerid=" + str(j)
                        if len(geomtypeids) > 1:
                            uri += "|subset=" + self.getsubset(geomtypeid)
                        
                        vlayer = QgsVectorLayer(uri, qgislayername, "ogr")
                        vlayer.setProviderEncoding("UTF-8")
                        #self.layers.append(QgsVectorLayer(uri, qgislayername, "ogr"))
                        #self.layers[-1].setProviderEncoding("UTF-8")
                        
                        if not vlayer.isValid():
                            print("vlayer not valid")
                        else:
                            print("vlayer is valid")
                            featurecount = vlayer.featureCount()
                            if featurecount > 0:
                                print("featurecount > 0")
                                self.dlg.label_Progress.setVisible(False)
                                #for baselayer in self.layers:
                                #    QgsMapLayerRegistry.instance().addMapLayer(baselayer)
                                    #self.hideLayer(baselayer)
                                    #self.iface.legendInterface().setLayerVisible(baselayer, False)

                                #self.dlg.pushButton_filtrer.setEnabled(True)
                                self.current_search_layer = vlayer
                                self.showResults(self.current_search_layer)
                                self.fill_infoWidget(self.current_attributes)
                                self.iface.addDockWidget( Qt.LeftDockWidgetArea , self.infoWidget )

                                self.search_history[self.layer_name] = SavedSearch(self.layer_name, self.current_search_layer, self.dlg.tabWidget_main.currentIndex(), self.dlg.tabWidget_friluft.currentIndex(), self.dlg.tabWidget_tettsted.currentIndex()) #lagerer søkets tab indes, lagnavn og lag referanse
                                for attribute in self.current_attributes: #lagrer valg av attributter
                                    self.search_history[self.layer_name].add_attribute(attribute, int(attribute.getComboBox().currentIndex()), attribute.getLineEditText())

                                self.search_history[self.layer_name].add_attribute(self.fylker, int(self.fylker.getComboBox().currentIndex()), None) #lagerer valg og fylter og komuner
                                self.search_history[self.layer_name].add_attribute(self.kommuner, int(self.kommuner.getComboBox().currentIndex()), None)

                                self.dlg.close() #closing main window for easyer visualisation of results
                                try:
                                    if self.current_search_layer is not None:
                                        QgsMapLayerRegistry.instance().addMapLayer(self.current_search_layer)
                                        self.current_search_layer.selectionChanged.connect(self.selectedObjects) #Filling infoWidget when objects are selected
                                        mapCanvas = self.iface.mapCanvas()
                                        mapCanvas.setExtent(self.current_search_layer.extent())
                                        mapCanvas.zoomOut()
                                        #self.canvas.setExtent(self.current_search_layer.extent())
                                        #self.canvas.refresh()
                                except Exception as e:
                                    print(str(e))
                                    #raise e
                                
                                if self.rubberHighlight is not None: #removing previus single highlight
                                    self.canvas.scene().removeItem(self.rubberHighlight)

                                self.infoWidget.label_typeSok.setText(self.dlg.tabWidget_tettsted.tabText(self.dlg.tabWidget_tettsted.currentIndex()))
                                #msg.done(1)
                                print("Filtering End")
                            else:
                                print("featurecount not > 0")
                                self.show_message("Søket fullførte uten at noen objecter ble funnet", "ingen Objecter funnet", msg_info=None, msg_details=None, msg_type=QMessageBox.Information)
                                return
                else:
                    print("featurecount not > 0")
                    self.show_message("Søket fullførte uten at noen objecter ble funnet", "ingen Objecter funnet", msg_info=None, msg_details=None, msg_type=QMessageBox.Information)
                    return

                            
                            #fill comboboxes
                            # if self.layers[-1].name() == "TettstedInngangBygg":
                            #     #self.fill_fylker()
                            #     for att in self.attributes_inngang_gui:
                            #         pass
                            #         #self.fill_combobox(self.layers[-1], att.getAttribute(), att.getComboBox())
                            #     for att in self.attributes_inngang_mer_mindre:
                            #         pass
                            #         #self.fill_combobox_mer_mindre(att.getComboBox())
                            #     #self.toggle_enable(self.attributes_inngang, True) #enable gui
                            # elif self.layers[-1].name() == "TettstedVei":
                            #     for att in self.attributes_vei_gui:
                            #         pass
                            #         #self.fill_combobox(self.layers[-1], att.getAttribute(), att.getComboBox())
                            #     for att in self.attributes_vei_mer_mindre:
                            #         pass
                            #         #self.fill_combobox_mer_mindre(att.getComboBox())
                            #     #self.toggle_enable(self.attributes_vei, True) #enable gui
                            # elif self.layers[-1].name() == "TettstedHCparkering":
                            #     for att in self.attributes_hcparkering_gui:
                            #         pass
                            #         #self.fill_combobox(self.layers[-1], att.getAttribute(), att.getComboBox())
                            #     for att in self.attributes_hcparkering_mer_mindre:
                            #         pass
                            #         #self.fill_combobox_mer_mindre(att.getComboBox())
                            #     #self.toggle_enable(self.attributes_hcparkering, True) #enable gui
                            # elif self.to_unicode(self.layers[-1].name()) == self.to_unicode("TettstedParkeringsomrÃ¥de"):
                            #     for att in self.attributes_pomrade_gui:
                            #         pass
                            #         #self.fill_combobox(self.layers[-1], att.getAttribute(), att.getComboBox())
                            #     for att in self.attributes_pomrade_mer_mindre:
                            #         pass
                                    #self.fill_combobox_mer_mindre(att.getComboBox())
                                #self.toggle_enable(self.attributes_pomrade, True) #enable gui

                            


    def getFeatures(self, featuretype):
        """This code is taken and adjusted from WFS 2.0 Client writen by Juergen Weichand
        Getting features for TilgjengelighetTettsted, modifye to include friluft"""

        namespace = "http://skjema.geonorge.no/SOSI/produktspesifikasjon/TilgjengelighetTettsted/4.5"
        namespace_prefix = "app"
        online_resource = "https://wfs.geonorge.no/skwms1/wfs.tilgjengelighettettsted"
        typeNames= urllib.quote(featuretype.encode('utf8'))
       
        query_string = "?service=WFS&request=GetFeature&version=2.0.0&srsName={0}&typeNames={1}".format( "urn:ogc:def:crs:EPSG::{0}".format(str(self.iface.mapCanvas().mapRenderer().destinationCrs().postgisSrid())).strip(), typeNames)
        query_string += "&namespaces=xmlns({0},{1})".format(namespace_prefix, urllib.quote(namespace,""))
        query_string+= "&"

        self.httpGetId = 0
        self.http = QHttp()

        self.http.requestStarted.connect(self.httpRequestStartet)
        self.http.requestFinished.connect(self.httpRequestFinished)
        self.http.dataReadProgress.connect(self.updateDataReadProgress)

        layername="wfs{0}".format(''.join(random.choice(string.ascii_uppercase + string.digits) for x in range(6)))
        fileName = self.get_temppath("{0}.gml".format(layername))

        #downloadFile
        url = QUrl(online_resource)

        print("url: ", url)
        print("online resource: ", online_resource)
        print("query string: ", query_string)
        if QFile.exists(fileName):
                    print("File  Exists")
                    QFile.remove(fileName)

        self.outFile = QFile(fileName)

        port = url.port()
        if port == -1:
            port = 0
        
        self.http.setHost(url.host(), QHttp.ConnectionModeHttps, port) #starting request
        #print("url.path: ", url.path())
        self.httpGetId = self.http.get(url.path() + query_string, self.outFile)
        print("url: ", url.path() + query_string)
        #print("httpGetId", self.httpGetId)
        

    def hentData(self):
        """Getting data based on current tab index"""
        print("FeautureType: ", self.feature_type_tettsted[self.dlg.tabWidget_tettsted.tabText(self.dlg.tabWidget_tettsted.currentIndex())])
        self.getFeatures(self.feature_type_tettsted[self.dlg.tabWidget_tettsted.tabText(self.dlg.tabWidget_tettsted.currentIndex())]) #sending featuretype based on current tab index


    def hideNode( self, node, bHide=True ):
        if type( node ) in ( QgsLayerTreeLayer, QgsLayerTreeGroup ):
            index = self.model.node2index( node )
            self.ltv.setRowHidden( index.row(), index.parent(), bHide )
            node.setCustomProperty( 'nodeHidden', 'true' if bHide else 'false' )
            self.ltv.setCurrentIndex( self.model.node2index( self.root ) )

    def hideLayer( self, mapLayer ):
        """Hides a layer that is in layerpanel"""
        if isinstance( mapLayer, QgsMapLayer ):
            self.hideNode( self.root.findLayer( mapLayer.id() ) )

    #NOTE: make generic hide/show modules
    def hide_show_rampe(self):
        """Hides or shows rampe"""
        if self.dlg.comboBox_rampe.currentText() == u"Ja":
            self.dlg.label_rampe_boxs.setVisible(True)

            self.dlg.lineEdit_rmp_stigning.setVisible(True)
            self.dlg.comboBox_rmp_stigning.setVisible(True)
            self.dlg.label_rmp_stigning.setVisible(True)

            self.dlg.lineEdit_rmp_bredde.setVisible(True)
            self.dlg.comboBox_rmp_bredde.setVisible(True)
            self.dlg.label_rmp_bredde.setVisible(True)

            self.dlg.comboBox_handliste.setVisible(True)
            self.dlg.label_handliste.setVisible(True)

            self.dlg.lineEdit_hand1.setVisible(True)
            self.dlg.comboBox_hand1.setVisible(True)
            self.dlg.label_hand1.setVisible(True)

            self.dlg.lineEdit_hand2.setVisible(True)
            self.dlg.comboBox_hand2.setVisible(True)
            self.dlg.label_hand2.setVisible(True)

            self.dlg.comboBox_rmp_tilgjengelig.setVisible(True)
            self.dlg.label_rmp_tilgjengelig.setVisible(True)

            self.dlg.line_4.setVisible(True)
            self.dlg.line.setVisible(True)
        else:
            self.dlg.label_rampe_boxs.setVisible(False)

            self.dlg.lineEdit_rmp_stigning.setVisible(False)
            self.dlg.comboBox_rmp_stigning.setVisible(False)
            self.dlg.label_rmp_stigning.setVisible(False)

            self.dlg.lineEdit_rmp_bredde.setVisible(False)
            self.dlg.comboBox_rmp_bredde.setVisible(False)
            self.dlg.label_rmp_bredde.setVisible(False)

            self.dlg.comboBox_handliste.setVisible(False)
            self.dlg.label_handliste.setVisible(False)

            self.dlg.lineEdit_hand1.setVisible(False)
            self.dlg.comboBox_hand1.setVisible(False)
            self.dlg.label_hand1.setVisible(False)

            self.dlg.lineEdit_hand2.setVisible(False)
            self.dlg.comboBox_hand2.setVisible(False)
            self.dlg.label_hand2.setVisible(False)

            self.dlg.comboBox_rmp_tilgjengelig.setVisible(False)
            self.dlg.label_rmp_tilgjengelig.setVisible(False)


            self.dlg.line_4.setVisible(False)
            self.dlg.line.setVisible(False)

    def hide_show_nedsenkning(self):
        if self.dlg.comboBox_gatetype.currentText() != self.uspesifisert:
            self.dlg.comboBox_nedsenkning1.setVisible(True)
            self.dlg.lineEdit_nedsenkning1.setVisible(True)
            self.dlg.label_nedsenkning1.setVisible(True)
            self.dlg.comboBox_nedsenkning2.setVisible(True)
            self.dlg.lineEdit_nedsenkning2.setVisible(True)
            self.dlg.label_nedsenkning2.setVisible(True)
        else:
            self.dlg.comboBox_nedsenkning1.setVisible(False)
            self.dlg.lineEdit_nedsenkning1.setVisible(False)
            self.dlg.label_nedsenkning1.setVisible(False)
            self.dlg.comboBox_nedsenkning2.setVisible(False)
            self.dlg.lineEdit_nedsenkning2.setVisible(False)
            self.dlg.label_nedsenkning2.setVisible(False)

    def hide_show_merket(self):
        if self.dlg.comboBox_merket.currentText() == "Ja":
            self.dlg.label_bredde_vei.setVisible(True)
            self.dlg.comboBox_bredde_vei.setVisible(True)
            self.dlg.lineEdit_bredde_vei.setVisible(True)
            self.dlg.label_lengde_vei.setVisible(True)
            self.dlg.comboBox_lengde_vei.setVisible(True)
            self.dlg.lineEdit_lengde_vei.setVisible(True)
        else:
            self.dlg.label_bredde_vei.setVisible(False)
            self.dlg.comboBox_bredde_vei.setVisible(False)
            self.dlg.lineEdit_bredde_vei.setVisible(False)
            self.dlg.label_lengde_vei.setVisible(False)
            self.dlg.comboBox_lengde_vei.setVisible(False)
            self.dlg.lineEdit_lengde_vei.setVisible(False)


    def toggle_enable(self, attributes, tr_or_fl):
        """Enabels or disabels gui_attributes

        :param attributes: list of attributes that are to be enabeld or disabeld
        :type attributes: list<AttributeForms>
        """
        for att in attributes:
            if att.getComboBox():
                att.getComboBox().setEnabled(tr_or_fl)
            if att.getLineEdit():
                att.getLineEdit().setEnabled(tr_or_fl)


    def get_previus_search_activeLayer(self):
        """Open filtering window set to preweus choises"""

        activeLayer = self.iface.activeLayer()
        #if self.search_history[activeLayer.name()]:
        if activeLayer is not None and activeLayer.name() in self.search_history:
            try:
                pre_search = self.search_history[activeLayer.name()]
                for key, value in pre_search.attributes.iteritems():
                    key.getComboBox().setCurrentIndex(int(value[0]))
                    if value[1]:
                        key.getLineEdit().setText(value[1])
                self.dlg.tabWidget_main.setCurrentIndex(pre_search.tabIndex_main)
                self.dlg.tabWidget_friluft.setCurrentIndex(pre_search.tabIndex_friluft)
                self.dlg.tabWidget_tettsted.setCurrentIndex(pre_search.tabIndex_tettsted)
                self.dlg.lineEdit_navn_paa_sok.setText(self.layer_name)
                self.dlg.show()

            except KeyError:
                raise



    def table_item_clicked(self):
        """Action for item click in table. Selects corrisponding object in map, and fills info widget with its data"""
        self.current_search_layer.setSelectedFeatures([]) #Disabels all selections in current search layer
        indexes = self.dock.tableWidget.selectionModel().selectedRows()
        if self.current_search_layer is not None: 
            for index in sorted(indexes):
                self.current_search_layer.setSelectedFeatures([self.feature_id[self.dock.tableWidget.item(index.row(), 0).text()]])
  


    #def set_availebility_icon(self, feature, tilgjenglighetsvurdering, icon, images, button):
    def set_availebility_icon(self, tilgjenglighetsvurdering, icons, button):
        """Method to set wheter object is availeble or not, not currently in use"""
        button.setIcon(icons[tilgjenglighetsvurdering])
        image_tilgjengelig = images[0]
        image_vanskeligTilgjengelig = images[1]
        image_ikkeTilgjengelig = images[2]
        image_ikkeVurdert = images[3]

        if tilgjenglighetsvurdering == "tilgjengelig":
            button.setIcon(image_tilgjengelig)
        elif tilgjenglighetsvurdering == "ikkeTilgjengelig":
            button.setIcon(image_ikkeTilgjengelig)
        elif tilgjenglighetsvurdering == "vanskeligTilgjengelig":
            button.setIcon(image_vanskeligTilgjengelig)
        else:
            button.setIcon(image_ikkeVurdert)



    def fill_combobox_old(self, layer, feat_name, combobox):
        """Filling out comboboxes based in features in layer

        :param layer: the layer that holds the attributes
        :param feat_name: the name of the feat that the attributes should be gatherd from
        :param combobox: The combobox to fill

        :type layer: qgis._core.QgsVectorLayer
        :type feat_name: str
        :type combobox: QComboBox
        """
        

        combobox.clear()
        combobox.addItem(self.uspesifisert)
        
        feat_name = self.to_unicode(feat_name)

        if feat_name == u'funksjon':
            textFile  = r'C:\Users\kaspa_000\.qgis2\python\plugins\Tilgjengelighet\tettstedInngangByggningstype.txt'#, 'w', 'utf-8'
        elif feat_name == u'dørtype':
            textFile  = r'C:\Users\kaspa_000\.qgis2\python\plugins\Tilgjengelighet\tettstedInngangDortype.txt'#, 'w', 'utf-8'
        elif feat_name == u'døråpner':
            textFile  = r'C:\Users\kaspa_000\.qgis2\python\plugins\Tilgjengelighet\tettstedInngangDorapner.txt'#, 'w', 'utf-8'
        elif feat_name == 'kontrast':
            textFile  = r'C:\Users\kaspa_000\.qgis2\python\plugins\Tilgjengelighet\tettstedInngangKontrast.txt'#, 'w', 'utf-8'
        elif feat_name == u'håndlist':
            textFile  = r'C:\Users\kaspa_000\.qgis2\python\plugins\Tilgjengelighet\tettstedInngangHandlist.txt'#, 'w', 'utf-8'
        elif feat_name == u'tilgjengvurderingElRull':
            textFile  = r'C:\Users\kaspa_000\.qgis2\python\plugins\Tilgjengelighet\tettstedInngangTilgjengvurdering.txt'#, 'w', 'utf-8')
        else:
            textFile = None
        print("feat_name: ", feat_name)
        for feature in layer.getFeatures(): #Sett inn error catchment her
            try:
                value = feature[feat_name]
            except KeyError:
                print("Layer does not contain given key")
                return
            if isinstance(value, int):
                value = str(value)
            if not isinstance(value, QPyNullVariant) and combobox.findText(value) < 0:
                combobox.addItem(value)

            AllItems = [combobox.itemText(i) for i in range(combobox.count())]
            if textFile is not None:
                with open(textFile, 'w') as f_out:
                    for item in AllItems:
                        f_out.write(item.encode('utf8') + '\n')
                #textFile.write(str(value) + '\n')
        #textFile.close()


    def fill_combobox(self, combobox, filename):
        with open(filename, 'r') as file:
            for line in file:
                combobox.addItem(self.uspesifisert)
                combobox.addItem(self.to_unicode(line).rstrip('\n'))



    def fill_combobox_mer_mindre(self, combobox):
        """Fill combobox with defult text

        :param combobx: QComboBox
        """
        combobox.clear()
        combobox.addItem(self.uspesifisert)
        combobox.addItem(self.mer)
        combobox.addItem(self.mindre)
        combobox.addItem(self.mer_eller_lik)
        combobox.addItem(self.mindre_eller_lik)
        
        

    def showResults(self, layer):
        """Presenting the result of a seach in a table

        :param layer: search result
        :type layer: qgis._core.QgsVectorLayer
        """
        #reset table
        self.dock.tableWidget.setRowCount(0)
        self.dock.tableWidget.setColumnCount(0)

        #Create data providers
        prov = layer.dataProvider()
        feat = layer.getFeatures()
        
        #Create colums
        self.nrColumn = len(prov.fields())
        self.dock.tableWidget.setColumnCount(len(prov.fields())) #creating colums

        for i in range(0, len(prov.fields())): #creating header in table         
            self.dock.tableWidget.setHorizontalHeaderItem(i,QTableWidgetItem(prov.fields().field(i).name()))

        # creating rows
        nr_objects  = 0
        for f in feat:
            nr_objects = nr_objects + 1
        self.dock.tableWidget.setRowCount(nr_objects)
        
        # filling table values
        current_object = 0
        self.feature_id = {}
        feat = layer.getFeatures() #resetting iterator
        for f in feat:
            self.feature_id[f['gml_id']] = f.id()
            for i in range(0,len(prov.fields())):
                if isinstance(f[i], QDateTime):
                    if f[i].isNull:
                        self.dock.tableWidget.setItem(current_object,i,QTableWidgetItem("NULL"))
                    else:
                        self.dock.tableWidget.setItem(current_object,i,QTableWidgetItem(f[i].toString('dd.MM.yy')))
                elif hasattr(f[i], 'toString'):
                    self.dock.tableWidget.setItem(current_object,i,QTableWidgetItem(f[i].toString()))
                elif isinstance(f[i], (int, float, long)):
                    self.dock.tableWidget.setItem(current_object,i,QTableWidgetItem(str(f[i])))
                elif isinstance(f[i], QPyNullVariant):
                    self.dock.tableWidget.setItem(current_object,i,QTableWidgetItem("NULL"))
                else:
                    self.dock.tableWidget.setItem(current_object,i,QTableWidgetItem(f[i]))

            current_object = current_object + 1
        self.dock.tableWidget.setSortingEnabled(True) #enabeling sorting
        #self.iface.addDockWidget( Qt.BottomDockWidgetArea , self.dock ) #adding seartch result Widget
        #self.dock.close()


    def fill_infoWidget(self, attributes):
        """Filling infowidget with attributes name and no value. Also ajustes size of infowidget

        :param attributes: List of gui attriibutes
        :type attributes: list<AttributeForms>
        """
        # for i in range(0, self.infoWidget.gridLayout.rowCount()): #Clears infowidget
        #     self.infoWidget.gridLayout.itemAtPosition(i, 0).widget().setText("")
        #     self.infoWidget.gridLayout.itemAtPosition(i, 1).widget().setText("")
        #     #self.infoWidget.gridLayout.itemAtPosition(i, 2).widget().setText("")

        # for i in range(0,len(attributes)): #Fills infowidgets and add new rows if needed

        #     if i < self.infoWidget.gridLayout.rowCount():
        #         self.infoWidget.gridLayout.itemAtPosition(i, 0).widget().setText(attributes[i].getAttribute())
        #         self.infoWidget.gridLayout.itemAtPosition(i, 1).widget().setText("-")

        #         self.infoWidget.gridLayout.itemAtPosition(i, 0).widget().setVisible(True)
        #         self.infoWidget.gridLayout.itemAtPosition(i, 1).widget().setVisible(True)
        #     else:
        #         self.infoWidget.gridLayout.addWidget(QLabel(attributes[i].getAttribute()), i, 0)
        #         self.infoWidget.gridLayout.addWidget(QLabel("-"), i, 1)

        # for i in range(len(attributes), self.infoWidget.gridLayout.rowCount()): #Hides rows that are not used
        #     self.infoWidget.gridLayout.itemAtPosition(i, 0).widget().setVisible(False)
        #     self.infoWidget.gridLayout.itemAtPosition(i, 1).widget().setVisible(False)

        for i in range(0, len(attributes)):
            self.infoWidget.gridLayout.itemAtPosition(i, 0).widget().setText(attributes[i].getAttribute())
            self.infoWidget.gridLayout.itemAtPosition(i, 1).widget().setText("-")

            self.infoWidget.gridLayout.itemAtPosition(i, 0).widget().setVisible(True)
            self.infoWidget.gridLayout.itemAtPosition(i, 1).widget().setVisible(True)

        for i in range(len(attributes), self.infoWidget.gridLayout.rowCount()): #Hides rows that are not used
            self.infoWidget.gridLayout.itemAtPosition(i, 0).widget().setVisible(False)
            self.infoWidget.gridLayout.itemAtPosition(i, 1).widget().setVisible(False)

        #TEST
        # for i in range(0, len(attributes)):
        #     #print(i)
        #     #print("widget: ", self.infoWidget.gridLayout.itemAtPosition(i, 0).widget(), "type; ", type(self.infoWidget.gridLayout.itemAtPosition(i, 0).widget()))
        #     self.infoWidget.gridLayout.itemAtPosition(i, 0).widget().setText(attributes[i].getAttribute())
        #     self.infoWidget.gridLayout.itemAtPosition(i, 1).widget().setText("-")

        #     for j in range(0, self.infoWidget.gridLayout.columnCount()):
        #         self.infoWidget.gridLayout.itemAtPosition(i, j).widget().setVisible(True)

        # if len(attributes) < self.infoWidget.gridLayout.rowCount():
        #     for i in range(len(attributes), self.infoWidget.gridLayout.rowCount()):
        #         for j in range(0,2):
        #             print("i: {0}, j: {1}".format(i,j))
        #             self.infoWidget.gridLayout.itemAtPosition(i, j).widget().setVisible(False)
        # if not self.infoWidget.isVisible():
        #     self.infoWidget.show()



    def fill_fylker(self):
        """Fill up the combobox fylker with fylker from komm.txt"""
        self.dlg.comboBox_fylker.clear()
        self.dlg.comboBox_fylker.addItem("Norge")

        filename = self.plugin_dir + "\komm.txt"
        self.komm_dict_nr = {}
        self.komm_dict_nm = {}
        self.fylke_dict = {}

        with io.open(filename, 'r', encoding='utf-8') as f:
            for line in f:
                komm_nr, komune, fylke = line.rstrip('\n').split(("\t"))
                komm_nr = self.to_unicode(komm_nr)
                komune = self.to_unicode(komune)
                fylke = self.to_unicode(fylke)

                self.komm_dict_nr[komm_nr] = komune
                self.komm_dict_nm[komune] = komm_nr
                if not fylke in self.fylke_dict:
                    self.fylke_dict[fylke] = []
                    self.dlg.comboBox_fylker.addItem(fylke)

                self.fylke_dict[fylke].append(komm_nr)


    def fylke_valgt(self):
        """Fill uo komune combobox with kommune in chosen fylke"""
        fylke = self.dlg.comboBox_fylker.currentText()
        self.dlg.comboBox_komuner.clear()
        self.dlg.comboBox_komuner.addItem(self.uspesifisert)
        if fylke != "Norge":
            try:
                for komune_nr in self.fylke_dict[fylke]:
                    self.dlg.comboBox_komuner.addItem(self.komm_dict_nr[komune_nr])
            except Exception as e:
                print(str(e))

    def komune_valgt(self):
        """Alter the name on seach after kommune is chosen"""
        if self.dlg.comboBox_komuner.currentText() != "":
            self.dlg.lineEdit_navn_paa_sok.setText(self.dlg.lineEdit_navn_paa_sok.text() + ": " + self.dlg.comboBox_komuner.currentText())
        else:
            self.dlg.lineEdit_navn_paa_sok.setText(self.dlg.lineEdit_navn_paa_sok.text() + ": " + self.dlg.comboBox_fylker.currentText())


    def change_search_name(self):
        """Changes the name of search baes on current tab and fyle and kommune"""
        self.dlg.lineEdit_navn_paa_sok.setText(self.dlg.tabWidget_main.tabText(self.dlg.tabWidget_main.currentIndex()))
        if self.dlg.tabWidget_main.currentIndex() == 0:
            self.dlg.lineEdit_navn_paa_sok.setText(self.dlg.lineEdit_navn_paa_sok.text() + " " + self.dlg.tabWidget_friluft.tabText(self.dlg.tabWidget_friluft.currentIndex()))
        else:
            self.dlg.lineEdit_navn_paa_sok.setText(self.dlg.lineEdit_navn_paa_sok.text() + " " + self.dlg.tabWidget_tettsted.tabText(self.dlg.tabWidget_tettsted.currentIndex()))
        if self.dlg.comboBox_fylker.currentText() != "Norge":
            if self.dlg.comboBox_komuner.currentText() != "":
                self.dlg.lineEdit_navn_paa_sok.setText(self.dlg.lineEdit_navn_paa_sok.text() + ": " + self.dlg.comboBox_komuner.currentText())
            else:
                self.dlg.lineEdit_navn_paa_sok.setText(self.dlg.lineEdit_navn_paa_sok.text() + ": " + self.dlg.comboBox_fylker.currentText())


    def save_search(self):
        self.search_history[self.layer_name] = SavedSearch(self.layer_name, self.current_search_layer, self.dlg.tabWidget_main.currentIndex(), self.dlg.tabWidget_friluft.currentIndex(), self.dlg.tabWidget_tettsted.currentIndex()) #lagerer søkets tab indes, lagnavn og lag referanse
        for attribute in self.current_attributes: #lagrer valg av attributter
            self.search_history[self.layer_name].add_attribute(attribute, int(attribute.getComboBox().currentIndex()), attribute.getLineEditText())

        self.search_history[self.layer_name].add_attribute(self.fylker, int(self.fylker.getComboBox().currentIndex()), None) #lagerer valg og fylter og komuner
        self.search_history[self.layer_name].add_attribute(self.kommuner, int(self.kommuner.getComboBox().currentIndex()), None)



    def create_where_statement(self,attributes):
        """Create a where statement for search
        :param attributes:
        :type attributes: list<AttributeForms>

        :returns: a where statement string sorted after given attributes
        :rtype: str
        """

        fylke = self.dlg.comboBox_fylker.currentText()
        komune = self.dlg.comboBox_komuner.currentText()
        where =  "WHERE lokalId > 0"

        if fylke != "Norge":
            if komune == self.uspesifisert:
                where = where + " AND " + "(kommune = '{0}'".format(self.fylke_dict[fylke][0])
                for komune_nr in range(1, len(self.fylke_dict[fylke])-1):
                    where = where + " OR kommune = '{0}'".format(self.fylke_dict[fylke][komune_nr])
                where = where + ")"
            else:
                where = where + " AND " + "kommune = '{0}'".format(self.komm_dict_nm[komune])

        #onde_atributter = ["dørtype", "terskelHøyde", "håndlist", "håndlistHøyde1", "håndlistHøyde2"]
        #one_att_dict = {"dørtype" : "d_rtype", "terskelHøyde" : "terskelH_yde", "håndlist" : "h_ndlist", "håndlistHøyde1" : "h_ndlistH_yde1", "håndlistHøyde2" : "h_ndlistH_yde2"}
        for attribute in attributes:
            if attribute.getLineEdit() is None:
                if attribute.getComboBoxCurrentText() != self.uspesifisert:
                    if len(where) == 0:
                        where = "WHERE %s = '%s'" % (attribute.getAttribute(), attribute.getComboBoxCurrentText())
                    else:
                        where =  where + " AND " + "%s = '%s'" % (attribute.getAttribute(), attribute.getComboBoxCurrentText())
            else:
                if attribute.getLineEditText() != self.uspesifisert:
                    if len(where) == 0:
                        where = "WHERE %s %s '%s'" % (attribute.getAttribute(), attribute.getComboBoxCurrentText(), attribute.getLineEditText())
                    else:
                        where = where + " AND " +  "%s %s '%s'" % (attribute.getAttribute(), attribute.getComboBoxCurrentText(), attribute.getLineEditText())

        return where

    def create_where_statement2(self,attributes):
        """Create an optinal where statement for search
        :param attributes:
        :type attributes: list<AttributeForms>

        :returns: a where statement string sorted after given attributes
        :rtype: str
        """
        fylke = self.dlg.comboBox_fylker.currentText()
        komune = self.dlg.comboBox_komuner.currentText()
        where = ""
        if fylke != "Norge":
            if komune == self.uspesifisert:
                where = where + " (\"kommune\"={0}".format(self.fylke_dict[fylke][0])
                for komune_nr in range(1, len(self.fylke_dict[fylke])-1):
                    where = where + " OR \"kommune\"={0}".format(self.fylke_dict[fylke][komune_nr])
                where = where + ")"
            else:
                where = where + " \"kommune\"={0}".format(self.komm_dict_nm[komune])
        else:
            where = " \"kommune\" > 0"

        #onde_atributter = ["dørtype", "terskelHøyde", "håndlist", "håndlistHøyde1", "håndlistHøyde2"]
        #one_att_dict = {"dørtype" : "d_rtype", "terskelHøyde" : "terskelH_yde", "håndlist" : "h_ndlist", "håndlistHøyde1" : "h_ndlistH_yde1", "håndlistHøyde2" : "h_ndlistH_yde2"}
        for attribute in attributes:
            if attribute.getLineEdit() is None:
                if attribute.getComboBoxCurrentText() != self.uspesifisert:
                    if len(where) == 0:
                        where = "\"%s\" = '%s'" % (attribute.getAttribute(), attribute.getComboBoxCurrentText())
                    else:
                        where =  where + " AND " + "\"%s\" = '%s'" % (attribute.getAttribute(), attribute.getComboBoxCurrentText())
            else:
                if attribute.getLineEditText() != self.uspesifisert:
                    if len(where) == 0:
                        where = "\"%s\" %s '%s'" % (attribute.getAttribute(), attribute.getComboBoxCurrentText(), attribute.getLineEditText())
                    else:
                        where = where + " AND " +  "\"%s\" %s '%s'" % (attribute.getAttribute(), attribute.getComboBoxCurrentText(), attribute.getLineEditText())

        return where


    def create_filter(self, opperator, valueReference, value):
        constraint = u"<fes:{0}><fes:ValueReference>app:{1}</fes:ValueReference><fes:Literal>{2}</fes:Literal></fes:{0}>".format(opperator,valueReference,value)
        return constraint


    def create_where_statement3(self, attributeList):
        fylke = self.dlg.comboBox_fylker.currentText()
        komune = self.dlg.comboBox_komuner.currentText()
        #query = "<fes:PropertyIsNotEqualTo><fes:ValueReference>app:lokalId</fes:ValueReference><fes:Literal>0</fes:Literal></fes:PropertyIsNotEqualTo>"
        constraint = []
        query = ""
        if fylke != "Norge":
            if komune == self.uspesifisert:
                for komune_nr in range(0, len(self.fylke_dict[fylke])):
                    valueReference = "kommune"
                    if len(self.fylke_dict[fylke][komune_nr]) < 4:
                        value = "0" + self.fylke_dict[fylke][komune_nr]
                    else:
                        value = self.fylke_dict[fylke][komune_nr]
                    query += "<fes:PropertyIsEqualTo><fes:ValueReference>app:{0}</fes:ValueReference><fes:Literal>{1}</fes:Literal></fes:PropertyIsEqualTo>".format(valueReference,value)
                    
                    #query += "<fes:{0}><fes:ValueReference>app:{1}</fes:ValueReference><fes:Literal>{2}</fes:Literal></fes:{0}>".format("PropertyIsEqualTo", "kommune", self.fylke_dict[fylke][komune_nr])
                if len(self.fylke_dict[fylke]) > 1: #Oslo har kun en kommune
                    query = "<Or>{0}</Or>".format(query)
            else:
                valueReference = "kommune"
                if len(self.komm_dict_nm[komune]) < 4:
                        value = "0" + self.komm_dict_nm[komune]
                else:
                    value = self.komm_dict_nm[komune]
                #value = self.komm_dict_nm[komune]
                query += "<fes:PropertyIsEqualTo><fes:ValueReference>app:{0}</fes:ValueReference><fes:Literal>{1}</fes:Literal></fes:PropertyIsEqualTo>".format(valueReference,value)
                #query += "<fes:{0}><fes:ValueReference>app:{1}</fes:ValueReference><fes:Literal>{2}</fes:Literal></fes:{0}>".format("PropertyIsEqualTo", "kommune", self.komm_dict_nm[komune])
                print("query: ", query)

        if len(query) > 0:
            constraint.append(query)
        
        print("query: ", query)


        for attribute in attributeList:
            if attribute.getComboBoxCurrentText() != self.uspesifisert:
                print("cmb_curent text: ", attribute.getComboBox().currentText())
                for key, value in attribute.opperatorDict.iteritems() :
                    print key, value
                valueReference = attribute.valueReference()
                value = attribute.value()
                opperator = attribute.opperator()
                constraint.append(self.create_filter(opperator, valueReference, value))
                #constraint = "<fes:{0}><fes:ValueReference>app:{1}</fes:ValueReference><fes:Literal>{2}</fes:Literal></fes:{0}>".format(opperator,valueReference,value)
                #query += constraint
                #query +=  "<fes:{0}><fes:ValueReference>app:{1}</fes:ValueReference><fes:Literal>{2}</fes:Literal></fes:{0}>".format(attribute.opperator(), attribute.valueReference(), attribute.value())
        # if len(query) > 0:
        #     filterURL = "<fes:Filter><And>{0}</And></fes:Filter>".format(query)
        #     print("query: ", query)
        #     print("filterURL: ", filterURL)
        #     return("FILTER=" + urllib.quote(filterURL.encode('utf8')))
        query = ""
        filterString = ""
        if len(constraint) > 1:
            for q in constraint:
                query += q
            filterString = u"<fes:Filter><And>{0}</And></fes:Filter>".format(query)
            print("filterString: ", filterString)
            return ("FILTER=" + self.to_unicode(filterString))
            #return ("FILTER=" + filterString.encode('utf8'))
            #return ("FILTER=" + urllib.quote(filterString.encode('utf8')))
        elif len(constraint) == 1:
            filterString = "<fes:Filter>{0}</fes:Filter>".format(constraint[0])
            print("filterString: ", filterString)
            return ("FILTER=" + self.to_unicode(filterString))
            #return ("FILTER=" + filterString.encode('utf8'))
            #return ("FILTER=" + urllib.quote(filterString.encode('utf8')))
        print("filterString: ", filterString)

        return filterString
        
        
    def newFilter(self):
        print (u"NewFilterStart")

        self.layer_name = self.dlg.lineEdit_navn_paa_sok.text() #setter navn på laget
        search_type = self.dlg.tabWidget_tettsted.tabText(self.dlg.tabWidget_tettsted.currentIndex()) #henter hvilke søk som blir gjort (må spesifisere esenere for tettsted eller friluft)
        search_type_pomrade = self.dlg.tabWidget_tettsted.tabText(3) #setter egen for pområde pga problemer med norske bokstaver
        if self.dlg.tabWidget_main.currentIndex() < 1:
            tilgjDB = "friluft"
        else:
            tilgjDB = "tettsted"
            featuretype = self.feature_type_tettsted[self.dlg.tabWidget_tettsted.tabText(self.dlg.tabWidget_tettsted.currentIndex())]
            self.current_attributes = self.attributes_tettsted[self.dlg.tabWidget_tettsted.tabText(self.dlg.tabWidget_tettsted.currentIndex())]

        url = u"http://wfs.geonorge.no/skwms1/wfs.tilgjengelighet{0}?service=WFS&request=GetFeature&version=2.0.0&srsName=urn:ogc:def:crs:EPSG::4258&typeNames=app:{1}&".format(tilgjDB, featuretype)

        filter_encoding = self.create_where_statement3(self.current_attributes)#= "FILTER=<fes:Filter><fes:PropertyIsEqualTo><fes:ValueReference>app:kommune</fes:ValueReference><fes:Literal>0301</fes:Literal></fes:PropertyIsEqualTo></fes:Filter>"
        #print("url: {}".format(url + filter_encoding))
        layer = QgsVectorLayer(url + filter_encoding, self.layer_name, "ogr")


        if layer.isValid():
            existing_layers = self.iface.legendInterface().layers()
            try:
                for layer in existing_layers: #Removing layers with same name
                    if layer.name() == tempLayer.name():
                        QgsMapLayerRegistry.instance().removeMapLayers( [layer.id()] )
            except Exception as e:
                print(str(e))
            
            QgsMapLayerRegistry.instance().addMapLayer(layer)
            self.current_search_layer = layer
            self.current_search_layer.selectionChanged.connect(self.selectedObjects) #Filling infoWidget when objects are selected
            
            self.canvas.setExtent(self.current_search_layer.extent())
            self.canvas.zoomOut()

            self.fill_infoWidget(self.current_attributes)
            self.showResults(self.current_search_layer)
            self.infoWidget.show()
            
            self.infoWidget.label_typeSok.setText(self.dlg.tabWidget_tettsted.tabText(self.dlg.tabWidget_tettsted.currentIndex()))
            
            if self.rubberHighlight is not None: #removing previus single highlight
                self.canvas.scene().removeItem(self.rubberHighlight)
            self.save_search()
            self.dlg.close() #closing main window for easyer visualisation of results
        else:
            self.show_message("Ingen objekter funnet", msg_title="layer not valid", msg_type=QMessageBox.Warning)
        print(u"NewFilterEnd")

    def filtrer(self, attributes):
        """Goes throu all atributes in current tab, creates a where statement and create layer based on that"""
        print("Filtering Start")

        # msg = QMessageBox()
        # msg.setText("Filtrerer, venligst vent")
        # msg.open()
    
        #sok_metode = self.dlg.comboBox_sok_metode.currentText() #henter hvilke metode som benyttes(virtuelt eller memory)
        self.layer_name = self.dlg.lineEdit_navn_paa_sok.text() #setter navn på laget
        search_type = self.dlg.tabWidget_tettsted.tabText(self.dlg.tabWidget_tettsted.currentIndex()) #henter hvilke søk som blir gjort (må spesifisere esenere for tettsted eller friluft)
        search_type_pomrade = self.dlg.tabWidget_tettsted.tabText(3) #setter egen for pområde pga problemer med norske bokstaver

        #setter baselayre basert på søketypen
        try:
            if search_type == "Vei":
                #baselayer = QgsMapLayerRegistry.instance().mapLayersByName('TettstedVei')[0]
                attributes = self.attributes_vei
            elif search_type == "Inngang":
                #baselayer = QgsMapLayerRegistry.instance().mapLayersByName('TettstedInngangBygg')[0]
                attributes = self.attributes_inngang
            elif search_type == "HC-Parkering":
                #baselayer = QgsMapLayerRegistry.instance().mapLayersByName('TettstedHCparkering')[0]
                attributes = self.attributes_hcparkering
            elif search_type == search_type_pomrade:
                #baselayer = QgsMapLayerRegistry.instance().mapLayersByName('TettstedParkeringsomr\xc3\xa5de')[0]
                attributes = self.attributes_pomrade
        except IndexError as e:
            self.show_message("Kan ikke filtrere uten data, venligst hent data og prøv igjen", msg_title="Manger Data", msg_type=QMessageBox.Warning)
            #QMessageBox.warning(self.iface.mainWindow(), "Mangler data, hent data før filtrering")
            return
        
        #attributes = self.attributes_inngang
        self.current_attributes = attributes

        # if self.dlg.tabWidget_main.currentIndex() < 1:
        #     namespace = "http://skjema.geonorge.no/SOSI/produktspesifikasjon/TilgjengelighetFriluft/1.0"
        #     online_resource = "https://wfs.geonorge.no/skwms1/wfs.tilgjengelighettettsted"
        #     featuretype = self.feature_type_tettsted[self.dlg.tabWidget_friluft.tabText(self.dlg.tabWidget_friluft.currentIndex())]
        # else:
        #     namespace = "http://skjema.geonorge.no/SOSI/produktspesifikasjon/TilgjengelighetTettsted/4.5"
        #     online_resource = "https://wfs.geonorge.no/skwms1/wfs.tilgjengelighettettsted"
        #     featuretype = self.feature_type_tettsted[self.dlg.tabWidget_tettsted.tabText(self.dlg.tabWidget_tettsted.currentIndex())]

        namespace = "http://skjema.geonorge.no/SOSI/produktspesifikasjon/TilgjengelighetTettsted/4.5"
        #namespace = "http://skjema.geonorge.no/SOSI/produktspesifikasjon/{0}".format(database)
        namespace_prefix = "app"
        online_resource = "https://wfs.geonorge.no/skwms1/wfs.tilgjengelighettettsted"

        featuretype = self.feature_type_tettsted[self.dlg.tabWidget_tettsted.tabText(self.dlg.tabWidget_tettsted.currentIndex())]
        typeNames= urllib.quote(featuretype.encode('utf8'))

        query_string = "?service=WFS&request=GetFeature&version=2.0.0&srsName={0}&typeNames={1}".format( "urn:ogc:def:crs:EPSG::{0}".format(str(self.iface.mapCanvas().mapRenderer().destinationCrs().postgisSrid())).strip(), typeNames)
        query_string += "&namespaces=xmlns({0},{1})".format(namespace_prefix, urllib.quote(namespace,""))
        query_string+= "&"
        query_string += self.create_where_statement3(self.current_attributes)
        print("query_string: ", query_string)

        self.httpGetId = 0
        self.http = QHttp()

        self.http.requestStarted.connect(self.httpRequestStartet)
        self.http.requestFinished.connect(self.httpRequestFinished)
        self.http.dataReadProgress.connect(self.updateDataReadProgress)


        layername="wfs{0}".format(''.join(random.choice(string.ascii_uppercase + string.digits) for x in range(6)))
        fileName = self.get_temppath("{0}.gml".format(layername))

        #downloadFile
        url = QUrl(online_resource)

        print("url: ", url)
        print("online resource: ", online_resource)
        print("query string: ", query_string)
        if QFile.exists(fileName):
                    print("File  Exists")
                    QFile.remove(fileName)

        self.outFile = QFile(fileName)

        port = url.port()
        if port == -1:
            port = 0
        
        self.http.setHost(url.host(), QHttp.ConnectionModeHttps, port) #starting request
        #print("url.path: ", url.path())
        self.httpGetId = self.http.get(url.path() + query_string, self.outFile)
        print("url: ", url.path() + query_string)
        #print("httpGetId", self.httpGetId)


        #self.sourceMapTool = IdentifyGeometry(self.canvas, self.infoWidget, self.current_attributes, pickMode='selection') #For selecting abject in map and showing data
        
        #fylke = self.dlg.comboBox_fylker.currentText()
        #komune = self.dlg.comboBox_komuner.currentText()

        #genererer express string og where spørringer med komuner
        # expr_string  = self.create_where_statement2(attributes)
        
        # where = self.create_where_statement(attributes)

        # print ("expr_string: ", expr_string, " where: ", where)
        

        # #genererer express string og where spørringer basert på tilstndte attributter
        # #for attribute in attributes:
        # #    where = self.create_where_statement(attribute, where)
        # #    expr_string = self.create_where_statement2(attribute, expr_string)

        # #Genererer lag basert på virtuell metode eller memory metode
        # if sok_metode == "virtual":
            
        #     layer_name_text = layer_name.text() + "Virtual"
        #     base_layer_name = baselayer.name()
        #     query = "SELECT * FROM " + base_layer_name + " " + where
        #     self.current_search_layer = QgsVectorLayer("?query=%s" % (query), layer_name_text, "virtual" )

        #     if self.current_search_layer.featureCount() > 0: #Lager lag hvis noen objecter er funnet
        #         if len(QgsMapLayerRegistry.instance().mapLayersByName(layer_name_text)) > 0:
        #             try:
        #                 QgsMapLayerRegistry.instance().removeMapLayer( QgsMapLayerRegistry.instance().mapLayersByName(layer_name_text)[0].id() ) #Fjerner lag med samme navn, for å ungå duplicates
        #             except (RuntimeError, AttributeError) as e:
        #                 print(str(e))

        #         QgsMapLayerRegistry.instance().addMapLayer(self.current_search_layer) #Legger inn nytt lag
        #         self.fill_infoWidget(attributes)
        #         self.canvas.setExtent(self.current_search_layer.extent()) #zoomer inn på nytt lag
        #         self.iface.addDockWidget( Qt.LeftDockWidgetArea , self.infoWidget ) #legger inn infowidget
        #         self.showResults(self.current_search_layer) #Legger inn tabell
        #         #self.sourceMapTool.setLayer(self.current_search_layer) #new layer target for tools

        #         self.search_history[layer_name_text] = SavedSearch(layer_name_text, self.current_search_layer, layer_name, self.dlg.tabWidget_main.currentIndex(), self.dlg.tabWidget_friluft.currentIndex(), self.dlg.tabWidget_tettsted.currentIndex()) #lagerer søkets tab indes, lagnavn og lag referanse
        #         for attribute in attributes: #lagrer valg av attributter
        #             self.search_history[layer_name_text].add_attribute(attribute, int(attribute.getComboBox().currentIndex()), attribute.getLineEditText())

        #         self.search_history[layer_name_text].add_attribute(self.fylker, int(self.fylker.getComboBox().currentIndex()), None) #lagerer valg og fylter og komuner
        #         self.search_history[layer_name_text].add_attribute(self.kommuner, int(self.kommuner.getComboBox().currentIndex()), None)
        #         if self.infoWidget.comboBox_search_history.findText(layer_name_text) == -1: #Legger til ikke existerende søk i søk historien
        #             self.infoWidget.comboBox_search_history.addItem(layer_name_text)
        #         self.dlg.close() #lukker hovedvindu for enklere se resultater
                
        #     else:
        #         self.show_message("Søket fullførte uten at noen objecter ble funnet", "ingen Objecter funnet", msg_info=None, msg_details=None, msg_type=None) #Melding som vises om søket feilet
        
        # if sok_metode == "memory": #self.dlg.comboBox_sok_metode.currentText() == "memory":
        #     try:
        #         QgsMapLayerRegistry.instance().removeMapLayer( tempLayer )
        #     except (RuntimeError, AttributeError, UnboundLocalError):
        #         pass

        #     layer_name_text = layer_name.text()# + "Memory"

        #     if search_type == "Vei":
        #         tempLayer = QgsVectorLayer("LineString?crs=epsg:4326", layer_name_text, "memory")
        #     elif search_type == search_type_pomrade:
        #         tempLayer = QgsVectorLayer("Polygon?crs=epsg:4326", layer_name_text, "memory")
        #     else:
        #         tempLayer = QgsVectorLayer("Point?crs=epsg:4326", layer_name_text, "memory")

        #     if len(expr_string) == 0: #tester en liten ting med gitKrakken
        #         #expr_string = " \"kommune\" > 0"
        #         temp_data = mem_layer.dataProvider()
        #         attr = layer.dataProvider().fields().toList()
        #         temp_data.addAttributes(attr)
        #         tempLayer.updateFields()
        #         temp_data.addFeatures(feats)
        #     else:
        #         expr = QgsExpression(expr_string)
        #         it = baselayer.getFeatures( QgsFeatureRequest( expr ) )
        #         ids = [i.id() for i in it]
        #         baselayer.setSelectedFeatures( ids )
        #         selectedFeatures = baselayer.selectedFeatures()
        #         temp_data = tempLayer.dataProvider()
        #         attr = baselayer.dataProvider().fields().toList()
        #         temp_data.addAttributes(attr)
        #         tempLayer.updateFields()
        #         temp_data.addFeatures(selectedFeatures)

        #     if tempLayer.featureCount() > 0:
        #         existing_layers = self.iface.legendInterface().layers()
        #         try:
        #             for layer in existing_layers: #Removing layers with same name
        #                 if layer.name() == tempLayer.name():
        #                     QgsMapLayerRegistry.instance().removeMapLayers( [layer.id()] )
        #         except Exception as e:
        #             print(str(e))

        #         self.current_search_layer = tempLayer
        #         QgsMapLayerRegistry.instance().addMapLayer(self.current_search_layer)

        #         #self.canvas.setExtent(self.current_search_layer.extent())
        #         #self.canvas.refresh()
        #         #tempLayer.triggerRepaint()
        #         self.iface.addDockWidget( Qt.LeftDockWidgetArea , self.infoWidget )
        #         #self.sourceMapTool.setLayer(self.current_search_layer)
        #         self.showResults(self.current_search_layer)
        #         self.fill_infoWidget(attributes)

        #         self.search_history[layer_name_text] = SavedSearch(layer_name_text, self.current_search_layer, layer_name, self.dlg.tabWidget_main.currentIndex(), self.dlg.tabWidget_friluft.currentIndex(), self.dlg.tabWidget_tettsted.currentIndex()) #lagerer søkets tab indes, lagnavn og lag referanse
        #         for attribute in attributes: #lagrer valg av attributter
        #             self.search_history[layer_name_text].add_attribute(attribute, int(attribute.getComboBox().currentIndex()), attribute.getLineEditText())

        #         self.search_history[layer_name_text].add_attribute(self.fylker, int(self.fylker.getComboBox().currentIndex()), None) #lagerer valg og fylter og komuner
        #         self.search_history[layer_name_text].add_attribute(self.kommuner, int(self.kommuner.getComboBox().currentIndex()), None)

        #         self.dlg.close() #closing main window for easyer visualisation of results

        #     else: #no objects found
        #         #msg.done(1)
        #         self.show_message("Søket fullførte uten at noen objecter ble funnet", "ingen Objecter funnet", msg_info=None, msg_details=None, msg_type=QMessageBox.Information)
        #         QgsMapLayerRegistry.instance().removeMapLayer( tempLayer.id() )
        # try:
        #     if self.current_search_layer is not None:
        #         self.current_search_layer.selectionChanged.connect(self.selectedObjects) #Filling infoWidget when objects are selected
        #         mapCanvas = self.iface.mapCanvas()
        #         mapCanvas.setExtent(self.current_search_layer.extent())
        #         mapCanvas.zoomOut()
        #         #self.canvas.setExtent(self.current_search_layer.extent())
        #         #self.canvas.refresh()
        # except Exception as e:
        #     print(str(e))
        #     #raise e
        
        # if self.rubberHighlight is not None: #removing previus single highlight
        #     self.canvas.scene().removeItem(self.rubberHighlight)

        # self.infoWidget.label_typeSok.setText(self.dlg.tabWidget_tettsted.tabText(self.dlg.tabWidget_tettsted.currentIndex()))
        # #msg.done(1)
        # print("Filtering End")


    def selectedObjects(self, selFeatures):
        """changing number of selected objects in infowidget and settning current selected object
        :param selFeatures: Selected features of layer
         """
        self.selFeatures = selFeatures
        print(selFeatures)
        print(len(selFeatures))
        self.number_of_objects = len(selFeatures)
        self.cur_sel_obj = 0

        self.infoWidget.label_object_number.setText("{0}/{1}".format(self.cur_sel_obj+1, self.number_of_objects))
        self.obj_info()

        self.highlightSelected()


    def highlightSelected(self):
        """Highlights the object viewed in infowidget"""

        if self.rubberHighlight is not None:
            self.canvas.scene().removeItem(self.rubberHighlight)

        selection = self.iface.activeLayer().selectedFeatures()
        if len(selection) > 0:
            self.rubberHighlight = QgsRubberBand(self.canvas,QGis.Polygon)
            self.rubberHighlight.setBorderColor(QColor(255,0,0))
            self.rubberHighlight.setFillColor(QColor(255,0,0,255))
            #self.rubberHighlight.setLineStyle(Qt.PenStyle(Qt.DotLine))
            self.rubberHighlight.setWidth(4)
            self.rubberHighlight.setToGeometry(selection[self.cur_sel_obj].geometry(), self.current_search_layer)
            self.rubberHighlight.show()

    def infoWidget_next(self):
        """shows next object in infoWidget"""
        try:
            self.cur_sel_obj+=1
            if self.cur_sel_obj >= self.number_of_objects:
                self.cur_sel_obj = 0
            self.obj_info()
            self.highlightSelected()
        except AttributeError as e:
            pass
        except Exception as e:
            raise e
        

    def infoWidget_prev(self):
        """shows previus object in infoWidget"""
        try:
            self.cur_sel_obj-=1
            if self.cur_sel_obj < 0:
                self.cur_sel_obj = self.number_of_objects-1
            self.obj_info()
            self.highlightSelected()
        except AttributeError as e:
            pass
        except Exception as e:
            raise e

    def show_tabell(self):
        if self.infoWidget.pushButton_tabell.isChecked():
            self.dock.show()
        else:
            self.dock.close()
        


    def obj_info(self):
        """Fills infowidget with info of current object"""

        self.infoWidget.label_object_number.setText("{0}/{1}".format(self.cur_sel_obj+1, self.number_of_objects))
        selection = self.current_search_layer.selectedFeatures()
        #for feature in selection: #For availebility icon, not currently working
            #self.set_availebility_icon(feature)
            #self.set_availebility_icon(feature, "tilgjengvurderingRullestol", self.icon_rullestol, [self.image_tilgjengelig, self.image_vanskeligTilgjengelig, self.image_ikkeTilgjengelig, self.image_ikkeVurdert], self.infoWidget.pushButton_rullestol)
            #self.set_availebility_icon(feature, "tilgjengvurderingElRull", self.icon_rullestol_el, [self.image_tilgjengelig_el, self.image_vanskeligTilgjengelig_el, self.image_ikkeTilgjengelig_el, self.image_ikkeVurdert_el], self.infoWidget.pushButton_elrullestol)
            #self.set_availebility_icon(feature, "tilgjengvurderingSyn", self.icon_syn, [self.image_tilgjengelig_syn, self.image_vanskeligTilgjengelig_syn, self.image_ikkeTilgjengelig_syn, self.image_ikkeVurdert_syn], self.infoWidget.pushButton_syn)
        if len(selection) > 0:
            for i in range(0, len(self.current_attributes)):
                try:
                    value = selection[self.cur_sel_obj][self.to_unicode(self.current_attributes[i].getAttribute())]
                    print("value: ", value, "type: ", type(value))
                    try:
                        if isinstance(value, (int, float, long)):
                            self.infoWidget.gridLayout.itemAtPosition(i, 1).widget().setText(str(value))
                        elif isinstance(value, (QPyNullVariant)):
                            self.infoWidget.gridLayout.itemAtPosition(i, 1).widget().setText("-")
                        else:
                            self.infoWidget.gridLayout.itemAtPosition(i, 1).widget().setText(value)
                    except Exception as e:
                        print(str(e))
                        self.infoWidget.gridLayout.itemAtPosition(i, 1).widget().setText("-")
                        print(self.current_attributes[i].getAttribute())
                    print(value)
                except KeyError as e: #Rampe Stigning forsvinner...
                    print("missing attribute due to no value")
                    pass

                ####Iconer i Infowidget, ikke fått til å fungere#####
                # for j in range(0, 9, 4):#len(self.icons)):
                #     print("j: ", j)
                #     gridLayout = self.infoWidget.gridLayout
                #     #img_layout = self.infoWidget.gridLayout.itemAtPosition(i, j+2).widget()
                #     tilgjenglighetsvurdering = self.tilgjengelighetsvurdering(value, self.current_attributes[i].notAcceceble, self.current_attributes[i].acceceble, self.current_attributes[i].relate_notAccec, self.current_attributes[i].relate_accec)
                #     #icon_size = self.infoWidget.gridLayout.itemAtPosition(i, j+2).widget().iconSize()
                #     print("tilgjenglighetsvurdering: ", tilgjenglighetsvurdering)

                #     #print("icon: ", self.icons[j][tilgjenglighetsvurdering], " type: ", type(self.icons[j][tilgjenglighetsvurdering]))
                #     if tilgjenglighetsvurdering == "tilgjengelig":
                #         gridLayout.itemAtPosition(i,j+2).widget().setVisible(False)
                #         gridLayout.itemAtPosition(i,j+4).widget().setVisible(False)
                #         gridLayout.itemAtPosition(i,j+5).widget().setVisible(False)
                #         gridLayout.itemAtPosition(i,j+3).widget().setVisible(True)
                #     elif tilgjenglighetsvurdering == "vanskeligTilgjengelig":
                #         gridLayout.itemAtPosition(i,j+2).widget().setVisible(False)
                #         gridLayout.itemAtPosition(i,j+4).widget().setVisible(True)
                #         gridLayout.itemAtPosition(i,j+5).widget().setVisible(False)
                #         gridLayout.itemAtPosition(i,j+3).widget().setVisible(False)
                #     elif tilgjenglighetsvurdering == "ikkeTilgjengelig":
                #         gridLayout.itemAtPosition(i,j+2).widget().setVisible(False)
                #         gridLayout.itemAtPosition(i,j+4).widget().setVisible(False)
                #         gridLayout.itemAtPosition(i,j+5).widget().setVisible(True)
                #         gridLayout.itemAtPosition(i,j+3).widget().setVisible(False)
                #     elif tilgjenglighetsvurdering == "ikkeVurdert":
                #         gridLayout.itemAtPosition(i,j+2).widget().setVisible(True)
                #         gridLayout.itemAtPosition(i,j+4).widget().setVisible(False)
                #         gridLayout.itemAtPosition(i,j+5).widget().setVisible(False)
                #         gridLayout.itemAtPosition(i,j+3).widget().setVisible(False)

                        #img_layout.setVisible(False)
                    #img_layout.setPixmap(self.icons[j][tilgjenglighetsvurdering])
                    #img_layout.setIconSize(icon_size)
                    #img_layout.setFixedSize(icon_size)
        else:
            for i in range(0, len(self.current_attributes)):
                self.infoWidget.gridLayout.itemAtPosition(i, 1).widget().setText("-")
                    
    
    def tilgjengelighetsvurdering(self, value, notAcceceble=None, acceceble=None, relate_notAccec=None, relate_acces=None):
        #["tilgjengelig", "ikkeTilgjengelig", "vanskeligTilgjengelig", "ikkeVurdert"]
        if self.is_float(value):
            value = float(value)
        elif self.is_int(value):
            value = int(value)
            
        #print("Vurederer Tilgjenglighet")
        if value is None or value == "-" or isinstance(value, QPyNullVariant):
            print("ikkeVurdert")
            return "ikkeVurdert"
        elif notAcceceble:
            if relate_notAccec(value, notAcceceble):
                #print("ikkeTilgjengelig")
                return "ikkeTilgjengelig"
        elif acceceble:
            if relate_acces(value, acceceble):
                #print("Tilgjengelig")
                return "tilgjengelig"
        else:
            #print("vanskeligTilgjengelig")
            return "vanskeligTilgjengelig"
        #print("I should not see this")
        return "ikkeVurdert"

    def is_float(slef, value):
        try:
            float(value)
            return True
        except (ValueError, TypeError) as e:
            return False

    def is_int(self, value):
        try:
            int(value)
            return True
        except (ValueError, TypeError) as e:
            return False


    def show_message(self, msg_text, msg_title=None, msg_info=None, msg_details=None, msg_type=None):
        """Show the user a message
        :param msg_test: the tekst to show the user
        :type msg_tekt: str

        :param msg_title: the title of the message box
        :type msg_title: str

        :param msg_info: additional info for the user
        :type msg_info: str

        :param msg_details: details for the user
        :type msg_details: str

        :param msg_type: the type of message
        :type msg_type: QMessageBox.Icon
        """
        msg = QMessageBox()
        
        msg.setText(self.to_unicode(msg_text))

        if msg_title is not None:
            msg.setWindowTitle(msg_title)

        if msg_info is not None:
            msg.setInformativeText(msg_info)
        
        if msg_details is not None:
            msg.setDetailedText(msg_details)
        
        if msg_type is not None:
            msg.setIcon(msg_type)

        msg.setStandardButtons(QMessageBox.Ok)

        #msg.buttonClicked.connect()

        retval = msg.exec_()
        print(("value of pressed message box button:", retval))


    def excelSave(self):
        """obtaind from xytools, Saves features to excel format
        @author: Richard Duivenvoorde
        """
        if self.current_search_layer == None: 
            QMessageBox.warning(self.iface.mainWindow(), "Finner ingen lag å eksportere")
            if self.iface.activeLayer():
                self.currentLayerChanged(self.iface.activeLayer())
            else:   
                QMessageBox.warning(self.iface.mainWindow(), "No active layer", "Please make an vector layer active before saving it to excel file.")
                return

        fieldNames = utils.fieldNames(self.current_search_layer)
        dlg = FieldChooserDialog(fieldNames)

        names = []
        while len(names) == 0:
            dlg.show()
            if dlg.exec_() == 0:
                return
            names = dlg.getSelectedFields()
            if len(names) == 0:
                QMessageBox.warning(self.iface.mainWindow(), "No fields selected", "Please select at least one field.")

        dirPath = self.settings.value("/xytools/excelSavePath", ".", type=str)    
        (filename, filter) = QFileDialog.getSaveFileNameAndFilter(self.iface.mainWindow(),
                    "Please save excel file as...",
                    dirPath,
                    "Excel files (*.xls)",
                    "Filter list for selecting files from a dialog box")
        fn, fileExtension = os.path.splitext(unicode(filename))
        if len(fn) == 0: # user choose cancel
            return
        self.settings.setValue("/xytools/excelSavePath", QFileInfo(filename).absolutePath())
        if fileExtension != '.xls':
            filename = filename + '.xls'
        try:
            from providers import excel
        except:
            QMessageBox.warning(self.iface.mainWindow(), "Unable to load Python module", "There is a problem with loading a python module which is needed to read/write Excel files. Please see documentation/help how to install python xlw and xlrd libraries.")
            return
        xlw = excel.Writer(filename)
        #self.layer = self.iface.activeLayer()
        selection = None
        if self.current_search_layer.selectedFeatureCount() > 0:
            if QMessageBox.question(self.iface.mainWindow(), 
                "Eksporter Til Excel", 
                ("You have a selection in this layer. Only export this selection?\n" "Click Yes to export selection only, click No to export all rows."), 
                QMessageBox.No, QMessageBox.Yes) == QMessageBox.Yes:
                    selection = self.current_search_layer.selectedFeaturesIds()
        feature = QgsFeature();

        xlw.writeAttributeRow(0, names)

        rowNr = 1
        if QGis.QGIS_VERSION_INT < 10900:
            prov = self.current_search_layer.dataProvider()
            prov.select(prov.attributeIndexes())
            while prov.nextFeature(feature):
                # attribute values, either for all or only for selection
                if selection == None or feature.id() in selection:
                    values = feature.attributeMap().values()
                    rowValues = []
                    for field in names:
                        rowValues.append(values[field])
                    xlw.writeAttributeRow(rowNr, values)
                    rowNr += 1
        else:
            prov = self.current_search_layer.getFeatures()
            while prov.nextFeature(feature):
                # attribute values, either for all or only for selection
                if selection == None or feature.id() in selection:
                    values = []
                    for field in names:
                        values.append(feature.attribute(field))
                    xlw.writeAttributeRow(rowNr, values)
                    rowNr += 1
        xlw.saveFile()
        QMessageBox.information(self.iface.mainWindow(), "Success", "Successfully saved as xls file")


    def savePath(self, saveType, saveExtension): #sett inn denne for exel også
        dirPath = self.settings.value("/Tilgjengelighet/savePath", ".", type=str)    
        (filename, filter) = QFileDialog.getSaveFileNameAndFilter(self.iface.mainWindow(),
                    "Please save {0} file as...".format(saveType),
                    dirPath,
                    "Image files (*{0})".format(saveExtension),
                    "Filter list for selecting files from a dialog box")
        fn, fileExtension = os.path.splitext(unicode(filename))
        if len(fn) == 0: # user choose cancel
            return
        self.settings.setValue("/Tilgjengelighet/savePath", QFileInfo(filename).absolutePath())
        if fileExtension != saveExtension:
            filename = filename + saveExtension

        return dirPath, filename


    def imageSave(self):
        #filename1 = QFileDialog.getSaveFileName()
        #print(filename1)

        # dirPath = self.settings.value("/Tilgjengelighet/savePath", ".", type=str)    
        # (filename, filter) = QFileDialog.getSaveFileNameAndFilter(self.iface.mainWindow(),
        #             "Please save image file as...",
        #             dirPath,
        #             "Image files (*.png)",
        #             "Filter list for selecting files from a dialog box")
        # fn, fileExtension = os.path.splitext(unicode(filename))
        # if len(fn) == 0: # user choose cancel
        #     return
        # self.settings.setValue("/Tilgjengelighet/savePath", QFileInfo(filename).absolutePath())
        # if fileExtension != '.png':
        #     filename = filename + '.png'

        dirPath, filename = self.savePath("Image", ".png")

        print("path: " + dirPath + " name: " + filename)
        size = self.canvas.size()
        image = QImage(size, QImage.Format_RGB32)

        painter = QPainter(image)
        settings = self.canvas.mapSettings()

        # You can fine tune the settings here for different
        # dpi, extent, antialiasing...
        # Just make sure the size of the target image matches

        # You can also add additional layers. In the case here,
        # this helps to add layers that haven't been added to the
        # canvas yet
        #layers = settings.layers()
        #settings.setLayers([layerP.id(), layerL.id()] + layers)

        job = QgsMapRendererCustomPainterJob(settings, painter)
        job.renderSynchronously()
        painter.end()
        image.save(filename) #filename1 + ".png")#'C:\\Users\\kaspa_000\\OneDrive\\Documents\\Skole-KaspArno\\Master\\tests\\newimageTest3.png')


    def open_export_layer_dialog(self): #Not currently in use
        """opens the excport gui"""
        self.export_layer.show()

    def OpenBrowser(self): #Not currently in use
        """Opens broeser to save file"""
        filename1 = QFileDialog.getSaveFileName()
        self.export_layer.lineEdit.setText(filename1)

    def lagre_lag(self): #Not currently in use
        """Saves layer as exported"""
        QgsVectorFileWriter.writeAsVectorFormat(self.iface.activeLayer(), self.export_layer.lineEdit.text(), "utf-8", None, self.export_layer.comboBox.currentText())


    def reset(self): 
        """Resets the gui back to default"""
        comboBoxes = [self.dlg.comboBox_fylker, self.dlg.comboBox_komuner, self.dlg.comboBox_avstand_hc, self.dlg.comboBox_ank_stigning, self.dlg.comboBox_byggningstype, self.dlg.comboBox_rampe, self.dlg.comboBox_dortype, self.dlg.comboBox_dorbredde, self.dlg.comboBox_terskel, self.dlg.comboBox_kontrast, self.dlg.comboBox_rmp_stigning, self.dlg.comboBox_rmp_bredde, self.dlg.comboBox_handliste, self.dlg.comboBox_hand1, self.dlg.comboBox_hand2, self.dlg.comboBox_manuell_rullestol, self.dlg.comboBox_el_rullestol, self.dlg.comboBox_syn]
        for cmb in comboBoxes:
            cmb.setCurrentIndex(0)

        lineEdits = [self.dlg.lineEdit_avstand_hc, self.dlg.lineEdit_ank_stigning, self.dlg.lineEdit_dorbredde, self.dlg.lineEdit_terskel, self.dlg.lineEdit_rmp_stigning, self.dlg.lineEdit_rmp_bredde, self.dlg.lineEdit_hand1, self.dlg.lineEdit_hand2, self.dlg.lineEdit_navn_paa_sok]
        for le in lineEdits:
            le.setText("")

  



    def run(self):
        #reloadPlugin('Tilgjengelighet')
        """Run method that performs all the real work"""


        # show the dialog
        self.dlg.show()
        #self.featuretype = FeatureType()
        #if self.featuretype:
        #    self.getFeatures()
        

        # Run the dialog event loop
        result = self.dlg.exec_()
        # See if OK was pressed
        if result:
            # Do something useful here - delete the line containing pass and
            # substitute with your code.
            pass
