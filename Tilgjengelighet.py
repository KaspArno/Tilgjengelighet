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
#import sys
import os
import io

import utils
import urllib
import random
import tempfile
import string
import datetime

from qgis.core import * #QgsDataSourceURI, QgsMapLayerRegistry, QgsVectorLayer, QgsExpression, QgsFeatureRequest, QgsVectorFileWriter, QgsLayerTreeLayer, QgsLayerTreeGroup, QgsMapLayer, QgsProject, QgsFeature, QGis
from PyQt4.QtCore import * #QSettings, QTranslator, qVersion, QCoreApplication, QPyNullVariant, QDateTime, QThread, pyqtSignal, Qt, QRect, QSize, QFileInfo
from PyQt4.QtGui import * #QAction, QIcon, QDockWidget, QGridLayout, QLineEdit, QTableWidget, QTableWidgetItem, QMessageBox, QApplication, QHBoxLayout, QVBoxLayout, QAbstractItemView, QListWidgetItem, QAbstractItemView, QFileDialog, QLabel, QPixmap, QIcon
from PyQt4.QtNetwork import QHttp
from qgis.gui import QgsRubberBand
from osgeo import gdal
from osgeo import ogr
from field_chooser import FieldChooserDialog



# Initialize Qt resources from file resources.py
import resources_rc

# Import the code for the dialog
from Tilgjengelighet_dialog import TilgjengelighetDialog
from tabledialog import TableDialog
from infoWidgetDialog import infoWidgetDialog
from exportlayerdialog import exportLayerDialog

from GuiAttribute import GuiAttribute #Storing user made attribute information
from identifyGeometry import IdentifyGeometry #For selection
from SavedSearch import SavedSearch #Save search choises for later use
from openlayers_plugin.openlayers_plugin import OpenlayersPlugin

#test
from weblayers.weblayer_registry import WebLayerTypeRegistry
from weblayers.osm_stamen import OlOSMStamenTonerLiteLayer


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

        
        #Globale Variabler
        self.uspesifisert = "" #For emty comboboxses and lineEdtis
        self.mer = ">" #for combobokser linked to more or less iterations
        self.mindre = "<"
        self.mer_eller_lik = ">="
        self.mindre_eller_lik = "<="

        #layers and search
        self.layers = [] #gather all baselayers

        self.current_search_layer = None #The last searched layer
        self.current_attributes = None
        self.search_history = {} #history of all search
        self.rubberHighlight = None 

        self.feature_type_tettsted = { "HC-Parkering" :'app:TettstedHCparkering', "Inngang" :'app:TettstedInngangBygg', u'Parkeringsomr\xe5de' : u'app:TettstedParkeringsomr\xe5de', "Vei" : 'app:TettstedVei'}

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

        #info window
        self.infoWidget = infoWidgetDialog(self.iface.mainWindow())
        self.infoWidget.pushButton_filtrer.clicked.connect(lambda x: self.dlg.show()) #open main window
        self.infoWidget.pushButton_filtrer.clicked.connect(self.get_previus_search_activeLayer) #setting main window to match search for active layer
        self.infoWidget.pushButton_next.clicked.connect(self.infoWidget_next) #itterate the selected objekts
        self.infoWidget.pushButton_prev.clicked.connect(self.infoWidget_prev)

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

        self.fylker = GuiAttribute("fylker")
        self.fylker.setComboBox(self.dlg.comboBox_fylker)
        self.kommuner = GuiAttribute("komune")
        self.kommuner.setComboBox(self.dlg.comboBox_komuner)


        #Create attributes object
        self.assign_combobox_inngang()
        self.assign_combobox_vei()
        self.assign_combobox_hc_parkering()
        self.assign_combobox_parkeringsomraade()

        self.dlg.pushButton_filtrer.clicked.connect(self.filtrer) #Filtering out the serach and show results

        ############################################################################################################
        self._olMenu = QMenu("OpenLayers plugin")
        self._olLayerTypeRegistry.register(OlOSMStamenTonerLiteLayer())

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
        self.layer = layer

    def createGdalTmsLayer(self, layerType, name):
        # create GDAL TMS layer with XML string as datasource
        layer = QgsRasterLayer(layerType.gdalTMSConfig(), name)
        layer.setCustomProperty('ol_layer_type', layerType.layerTypeName)
        return layer

    def canvasCrs(self):
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



    def addOLmenu(self):
        openLayers = OpenlayersPlugin(self.iface, self.infoWidget)
        openLayers.initGui()
        
        #self.infoWidget.toolButton_map.connect(self.showOLmenu)
        self.infoWidget.toolButton_map.triggered(self.infoWidget.toolButton_map.showMenu())

    def showOLmenu(self):
        self.infoWidget.toolButton_map.showMenu()
        

    def assign_combobox_inngang(self):
        """Assigning a GuiAttribute object to each option in inngang"""
        
        self.avstandHC = GuiAttribute("avstandHC", self.dlg.comboBox_avstand_hc, self.dlg.lineEdit_avstand_hc)
        self.ank_stigning = GuiAttribute("stigningAdkomstvei", self.dlg.comboBox_ank_stigning, self.dlg.lineEdit_ank_stigning)
        self.byggningstype = GuiAttribute("funksjon", self.dlg.comboBox_byggningstype)
        self.rampe = GuiAttribute("rampe", self.dlg.comboBox_rampe, comboBoxText={"" : "", "Ja" : "1", "Nei" : "0"})
        self.dortype = GuiAttribute(u'dørtype', self.dlg.comboBox_dortype)
        self.dorapner = GuiAttribute(u'døråpner', self.dlg.comboBox_dorapner)
        self.man_hoyde = GuiAttribute(u'manøverknappHøyde', self.dlg.comboBox_man_hoyde, self.dlg.lineEdit_man_hoyde)
        self.dorbredde = GuiAttribute("InngangBredde", self.dlg.comboBox_dorbredde, self.dlg.lineEdit_dorbredde)
        self.terskel = GuiAttribute(u'terskelH\xf8yde', self.dlg.comboBox_terskel, self.dlg.lineEdit_terskel)
        self.kontrast = GuiAttribute("kontrast", self.dlg.comboBox_kontrast)
        self.rampe_stigning = GuiAttribute("rampeStigning", self.dlg.comboBox_rmp_stigning, self.dlg.lineEdit_rmp_stigning)
        self.rampe_bredde = GuiAttribute("rampeBredde", self.dlg.comboBox_rmp_bredde, self.dlg.lineEdit_rmp_bredde)
        self.handlist = GuiAttribute(u'h\xe5ndlist', self.dlg.comboBox_handliste)
        self.handlist1 = GuiAttribute(u'h\xe5ndlistH\xf8yde1', self.dlg.comboBox_hand1, self.dlg.lineEdit_hand1)
        self.handlist2 = GuiAttribute(u'h\xe5ndlistH\xf8yde2', self.dlg.comboBox_hand2, self.dlg.lineEdit_hand2)
        self.rmp_tilgjengelig = GuiAttribute("rampeTilgjengelig", self.dlg.comboBox_rmp_tilgjengelig)
        self.manuellRullestol = GuiAttribute("tilgjengvurderingRullestol", self.dlg.comboBox_manuell_rullestol)
        self.elektriskRullestol = GuiAttribute("tilgjengvurderingElRull", self.dlg.comboBox_el_rullestol)
        self.synshemmet = GuiAttribute("tilgjengvurderingSyn", self.dlg.comboBox_syn)

        self.attributes_inngang = [self.avstandHC, self.ank_stigning, self.byggningstype, self.rampe, self.dortype, self.dorapner, self.man_hoyde, self.dorbredde, self.terskel, self.kontrast, self.rampe_stigning, self.rampe_bredde, self.handlist, self.handlist1, self.handlist2, self.rmp_tilgjengelig, self.manuellRullestol, self.elektriskRullestol, self.synshemmet]
        self.attributes_inngang_gui = [self.byggningstype, self.dortype, self.dorapner, self.kontrast, self.handlist, self.rmp_tilgjengelig, self.manuellRullestol, self.elektriskRullestol, self.synshemmet]
        self.attributes_inngang_mer_mindre = [self.avstandHC, self.ank_stigning, self.man_hoyde, self.dorbredde, self.terskel, self.rampe_stigning, self.rampe_bredde, self.handlist1, self.handlist2]

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
        """Assigning a GuiAttribute object to each option in vei"""

        self.gatetype = GuiAttribute("gatetype", self.dlg.comboBox_gatetype)
        self.nedsenkning1 = GuiAttribute("nedsenk1", self.dlg.comboBox_nedsenkning1, self.dlg.lineEdit_nedsenkning1)
        self.nedsenkning2 = GuiAttribute("nedsenk2", self.dlg.comboBox_nedsenkning2, self.dlg.lineEdit_nedsenkning2)
        self.dekke_vei_tettsted = GuiAttribute("dekke", self.dlg.comboBox_dekke_vei_tettsted)
        self.dekkeTilstand_vei_tettsted = GuiAttribute("dekkeTilstand", self.dlg.comboBox_dekkeTilstand_vei_tettsted)
        self.bredde = GuiAttribute("bredde", self.dlg.comboBox_bredde, self.dlg.lineEdit_bredde)
        self.stigning = GuiAttribute("stigning", self.dlg.comboBox_stigning, self.dlg.lineEdit_stigning)
        self.tverfall = GuiAttribute("tverrfall", self.dlg.comboBox_tverfall, self.dlg.lineEdit_tverfall)
        self.ledelinje = GuiAttribute("ledelinje", self.dlg.comboBox_ledelinje)
        self.ledelinjeKontrast = GuiAttribute("ledelinjeKontrast", self.dlg.comboBox_ledelinjeKontrast)

        self.manuell_rullestol_vei = GuiAttribute("tilgjengvurderingRullestol", self.dlg.comboBox_manuell_rullestol_vei)
        self.electrisk_rullestol_vei = GuiAttribute("tilgjengvurderingElRull", self.dlg.comboBox_electrisk_rullestol_vei)
        self.syn_vei = GuiAttribute("tilgjengvurderingSyn", self.dlg.comboBox_syn_vei)

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
        """Assigning a GuiAttribute object to each option in hc parkering"""

        self.avstandServicebygg = GuiAttribute("avstandServicebygg", self.dlg.comboBox_avstandServicebygg, self.dlg.lineEdit_avstandServicebygg)

        self.overbygg = GuiAttribute("overbygg", self.dlg.comboBox_overbygg, comboBoxText={"" : "", "Ja" : "1", "Nei" : "0"})
        self.skiltet = GuiAttribute("skiltet", self.dlg.comboBox_skiltet, comboBoxText={"" : "", "Ja" : "1", "Nei" : "0"})
        self.merket = GuiAttribute("merket", self.dlg.comboBox_merket, comboBoxText={"" : "", "Ja" : "1", "Nei" : "0"})

        self.bredde_vei = GuiAttribute("bredde", self.dlg.comboBox_bredde_vei, self.dlg.lineEdit_bredde_vei)
        self.lengde_vei = GuiAttribute("lengde", self.dlg.comboBox_lengde_vei, self.dlg.lineEdit_lengde_vei)

        self.manuell_rullestol_hcparkering = GuiAttribute("tilgjengvurderingRullestol", self.dlg.comboBox_manuell_rullestol_hcparkering)
        self.elektrisk_rullestol_hcparkering = GuiAttribute("tilgjengvurderingElRull", self.dlg.comboBox_elektrisk_rullestol_hcparkering)

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
        """Assigning a GuiAttribute object to each option in parkeringsområde"""

        self.overbygg_pomrade = GuiAttribute("overbygg", self.dlg.comboBox_overbygg_pomrade, comboBoxText={"" : "", "Ja" : "1", "Nei" : "0"})
        self.kapasitetPersonbiler = GuiAttribute("kapasitetPersonbiler", self.dlg.comboBox_kapasitetPersonbiler, self.dlg.lineEdit_kapasitetPersonbiler)
        self.kapasitetUU = GuiAttribute("kapasitetUU", self.dlg.comboBox_kapasitetUU, self.dlg.lineEdit_kapasitetUU)
        self.dekke_pomrade = GuiAttribute("dekke", self.dlg.comboBox_dekke_pomrade)
        self.dekkeTilstand_pomrade = GuiAttribute("dekkeTilstand", self.dlg.comboBox_dekkeTilstand_pomrade)

        self.manuell_rullestol_pomrade = GuiAttribute("tilgjengvurderingRullestol", self.dlg.comboBox_manuell_rullestol_pomrade)

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
                ogrlayercount = ogrdatasource.GetLayerCount()
                for i in range(0, ogrlayercount):
                    j = ogrlayercount -1 - i
                    ogrlayer = ogrdatasource.GetLayerByIndex(j)
                    ogrlayername = ogrlayer.GetName()
                    ogrgeometrytype = ogrlayer.GetGeomType()
                    geomtypeids = []
                    
                    if ogrgeometrytype==0:
                        geomtypeids = ["1", "2", "3", "100"]
                    else:
                        geomtypeids = [str(ogrgeometrytype)]
                    
                    for geomtypeid in geomtypeids:
                        qgislayername = ogrlayername
                        uri = self.outFile.fileName() + "|layerid=" + str(j)
                        if len(geomtypeids) > 1:
                            uri += "|subset=" + self.getsubset(geomtypeid)
                        
                        self.layers.append(QgsVectorLayer(uri, qgislayername, "ogr"))
                        self.layers[-1].setProviderEncoding("UTF-8")
                        
                        if not self.layers[-1].isValid():
                            print("self.vlayer not valid")
                        else:
                            featurecount = self.layers[-1].featureCount()
                            if featurecount > 0:
                                pass
                            
                            #fill comboboxes
                            if self.layers[-1].name() == "TettstedInngangBygg":
                                #self.fill_fylker()
                                for att in self.attributes_inngang_gui:
                                    self.fill_combobox(self.layers[-1], att.getAttribute(), att.getComboBox())
                                for att in self.attributes_inngang_mer_mindre:
                                    self.fill_combobox_mer_mindre(att.getComboBox())
                                self.toggle_enable(self.attributes_inngang, True) #enable gui
                            elif self.layers[-1].name() == "TettstedVei":
                                for att in self.attributes_vei_gui:
                                    self.fill_combobox(self.layers[-1], att.getAttribute(), att.getComboBox())
                                for att in self.attributes_vei_mer_mindre:
                                    self.fill_combobox_mer_mindre(att.getComboBox())
                                self.toggle_enable(self.attributes_vei, True) #enable gui
                            elif self.layers[-1].name() == "TettstedHCparkering":
                                for att in self.attributes_hcparkering_gui:
                                    self.fill_combobox(self.layers[-1], att.getAttribute(), att.getComboBox())
                                for att in self.attributes_hcparkering_mer_mindre:
                                    self.fill_combobox_mer_mindre(att.getComboBox())
                                self.toggle_enable(self.attributes_hcparkering, True) #enable gui
                            elif self.to_unicode(self.layers[-1].name()) == self.to_unicode("TettstedParkeringsomrÃ¥de"):
                                for att in self.attributes_pomrade_gui:
                                    self.fill_combobox(self.layers[-1], att.getAttribute(), att.getComboBox())
                                for att in self.attributes_pomrade_mer_mindre:
                                    self.fill_combobox_mer_mindre(att.getComboBox())
                                self.toggle_enable(self.attributes_pomrade, True) #enable gui

                            self.dlg.label_Progress.setVisible(False)
                            for baselayer in self.layers:
                                QgsMapLayerRegistry.instance().addMapLayer(baselayer)
                                self.hideLayer(baselayer)
                                self.iface.legendInterface().setLayerVisible(baselayer, False)

                            self.dlg.pushButton_filtrer.setEnabled(True)


    def getFeatures(self, featuretype):
        """Getting features for TilgjengelighetTettsted, modifye to include friluft"""

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
        #print("httpGetId", self.httpGetId)
        

    def hentData(self):
        """Getting data based on current tab index"""
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
        if self.dlg.comboBox_rampe.currentText() == "Ja":
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
        :type attributes: list<GuiAttributes>
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
        if activeLayer.name() in self.search_history:
            try:
                pre_search = self.search_history[activeLayer.name()]
                for key, value in pre_search.attributes.iteritems():
                    key.getComboBox().setCurrentIndex(int(value[0]))
                    if value[1]:
                        key.getLineEdit().setText(value[1])
                self.dlg.tabWidget_main.setCurrentIndex(pre_search.tabIndex_main)
                self.dlg.tabWidget_friluft.setCurrentIndex(pre_search.tabIndex_friluft)
                self.dlg.tabWidget_tettsted.setCurrentIndex(pre_search.tabIndex_tettsted)
                pre_search.lineEdit_seach.setText(pre_search.search_name)
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
  


    def set_availebility_icon(self, feature, tilgjenglighetsvurdering, icon, images, button):
        """Method to set wheter object is availeble or not, not currently in use"""

        image_tilgjengelig = images[0]
        image_vanskeligTilgjengelig = images[1]
        image_ikkeTilgjengelig = images[2]
        image_ikkeVurdert = images[3]

        if feature[self.to_unicode(tilgjenglighetsvurdering)] == "tilgjengelig":
            icon.addPixmap(image_tilgjengelig)
            button.setIcon(icon)
            button.setIconSize(image_tilgjengelig.rect().size())
            button.setFixedSize(image_tilgjengelig.rect().size())

        elif feature[self.to_unicode(tilgjenglighetsvurdering)] == "vanskeligTilgjengelig":
            icon.addPixmap(image_vanskeligTilgjengelig)
            button.setIcon(icon)
            button.setIconSize(image_vanskeligTilgjengelig.rect().size())
            button.setFixedSize(image_vanskeligTilgjengelig.rect().size())

        elif feature[self.to_unicode(tilgjenglighetsvurdering)] == "ikkeTilgjengelig":
            icon.addPixmap(image_ikkeTilgjengelig)
            button.setIcon(icon)
            button.setIconSize(image_ikkeTilgjengelig.rect().size())
            button.setFixedSize(image_ikkeTilgjengelig.rect().size())
        else:
            icon.addPixmap(image_ikkeVurdert)
            button.setIcon(icon)
            button.setIconSize(image_ikkeVurdert.rect().size())
            button.setFixedSize(image_ikkeVurdert.rect().size())



    def fill_combobox(self, layer, feat_name, combobox):
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

        for feature in layer.getFeatures(): #Sett inn error catchment her
            try:
                name = feature[feat_name]
            except KeyError:
                print("Layer does not contain given key")
                return
            if isinstance(name, int):
                name = str(name)
            if not isinstance(name, QPyNullVariant) and combobox.findText(name) < 0:
                combobox.addItem(name)

    def fill_combobox_mer_mindre(self, combobox):
        """Fill combobox with defult text

        :param combobx: QComboBox
        """
        combobox.clear()
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
        self.iface.addDockWidget( Qt.BottomDockWidgetArea , self.dock ) #adding seartch result Widget


    def fill_infoWidget(self, attributes):
        """Filling infowidget with attributes name and no value. Also ajustes size of infowidget

        :param attributes: List of gui attriibutes
        :type attributes; list<GuiAttributes>
        """
        for i in range(0, self.infoWidget.gridLayout.rowCount()): #Clears infowidget
            self.infoWidget.gridLayout.itemAtPosition(i, 0).widget().setText("")
            self.infoWidget.gridLayout.itemAtPosition(i, 1).widget().setText("")
            #self.infoWidget.gridLayout.itemAtPosition(i, 2).widget().setText("")

        for i in range(0,len(attributes)): #Fills infowidgets and add new rows if needed

            if i < self.infoWidget.gridLayout.rowCount():
                self.infoWidget.gridLayout.itemAtPosition(i, 0).widget().setText(attributes[i].getAttribute())
                self.infoWidget.gridLayout.itemAtPosition(i, 1).widget().setText("-")

                self.infoWidget.gridLayout.itemAtPosition(i, 0).widget().setVisible(True)
                self.infoWidget.gridLayout.itemAtPosition(i, 1).widget().setVisible(True)
            else:
                self.infoWidget.gridLayout.addWidget(QLabel(attributes[i].getAttribute()), i, 0)
                self.infoWidget.gridLayout.addWidget(QLabel("-"), i, 1)

        for i in range(len(attributes), self.infoWidget.gridLayout.rowCount()): #Hides rows that are not used
            self.infoWidget.gridLayout.itemAtPosition(i, 0).widget().setVisible(False)
            self.infoWidget.gridLayout.itemAtPosition(i, 1).widget().setVisible(False)


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


    # def create_expr_statement(self, attribute, expr_string): #Not currently beeing used
    #     if attribute.getLineEdit() is None:
    #         if attribute.getComboBoxCurrentText() != self.uspesifisert:
    #             if len(expr_string) == 0:
    #                 expr_string = "\"%s\"=\'%s\' " % (attribute.getAttribute(), attribute.getComboBoxCurrentText())
    #             else:
    #                 expr_string =  expr_string + " AND " + "\"%s\"=\'%s\' " % (attribute.getAttribute(), attribute.getComboBoxCurrentText())
    #     else:
    #         if attribute.getLineEditText() != self.uspesifisert:
    #             if len(expr_string) == 0:
    #                 expr_string = "\"%s\"%s\'%s\' " % (attribute.getAttribute(), attribute.getComboBoxCurrentText(), attribute.getLineEditText())
    #             else:
    #                 expr_string = expr_string + " AND " + "\"%s\"%s\'%s\' " % (attribute.getAttribute(), attribute.getComboBoxCurrentText(), attribute.getLineEditText())
    #     return expr_string

    def create_where_statement(self,attribute, where):
        """Create a where statement for search
        :param attribute:
        :type attribute:
        :param where:
        :type where:

        :returns: a where statement string sorted after given attributes
        :rtype: str
        """
        onde_atributter = ["dørtype", "terskelHøyde", "håndlist", "håndlistHøyde1", "håndlistHøyde2"]
        one_att_dict = {"dørtype" : "d_rtype", "terskelHøyde" : "terskelH_yde", "håndlist" : "h_ndlist", "håndlistHøyde1" : "h_ndlistH_yde1", "håndlistHøyde2" : "h_ndlistH_yde2"}
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

    def create_where_statement2(self,attribute, where):
        """Create an optinal where statement for search
        :param attribute:
        :type attribute:
        :param where:
        :type where:

        :returns: a where statement string sorted after given attributes
        :rtype: str
        """
        onde_atributter = ["dørtype", "terskelHøyde", "håndlist", "håndlistHøyde1", "håndlistHøyde2"]
        one_att_dict = {"dørtype" : "d_rtype", "terskelHøyde" : "terskelH_yde", "håndlist" : "h_ndlist", "håndlistHøyde1" : "h_ndlistH_yde1", "håndlistHøyde2" : "h_ndlistH_yde2"}
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



    def filtrer(self, attributes):
        """Goes throu all atributes in current tab, creates a where statement and create layer based on that"""
        print("Filtering Start")
    
        sok_metode = self.dlg.comboBox_sok_metode.currentText() #henter hvilke metode som benyttes(virtuelt eller memory)
        layer_name = self.dlg.lineEdit_navn_paa_sok #setter navn på laget
        search_type = self.dlg.tabWidget_tettsted.tabText(self.dlg.tabWidget_tettsted.currentIndex()) #henter hvilke søk som blir gjort (må spesifisere esenere for tettsted eller friluft)
        search_type_pomrade = self.dlg.tabWidget_tettsted.tabText(3) #setter egen for pområde pga problemer med norske bokstaver

        #setter baselayre basert på søketypen
        try:
            if search_type == "Vei":
                baselayer = QgsMapLayerRegistry.instance().mapLayersByName('TettstedVei')[0]
                attributes = self.attributes_vei
            elif search_type == "Inngang":
                baselayer = QgsMapLayerRegistry.instance().mapLayersByName('TettstedInngangBygg')[0]
                attributes = self.attributes_inngang
            elif search_type == "HC-Parkering":
                baselayer = QgsMapLayerRegistry.instance().mapLayersByName('TettstedHCparkering')[0]
                attributes = self.attributes_hcparkering
            elif search_type == search_type_pomrade:
                baselayer = QgsMapLayerRegistry.instance().mapLayersByName('TettstedParkeringsomr\xc3\xa5de')[0]
                attributes = self.attributes_pomrade
        except IndexError as e:
            self.show_message("Kan ikke filtrere uten data, venligst hent data og prøv igjen", msg_title="Manger Data", msg_type=QMessageBox.Warning)
            #QMessageBox.warning(self.iface.mainWindow(), "Mangler data, hent data før filtrering")
            return
        

        self.current_attributes = attributes
        #self.sourceMapTool = IdentifyGeometry(self.canvas, self.infoWidget, self.current_attributes, pickMode='selection') #For selecting abject in map and showing data
        
        fylke = self.dlg.comboBox_fylker.currentText()
        komune = self.dlg.comboBox_komuner.currentText()

        #genererer express string og where spørringer med komuner
        expr_string = ""
        if fylke != "Norge":
            if komune == self.uspesifisert:
                expr_string = expr_string + " (\"kommune\"={0}".format(self.fylke_dict[fylke][0])
                for komune_nr in range(1, len(self.fylke_dict[fylke])-1):
                    expr_string = expr_string + " OR \"kommune\"={0}".format(self.fylke_dict[fylke][komune_nr])
                expr_string = expr_string + ")"
            else:
                expr_string = expr_string + " \"kommune\"={0}".format(self.komm_dict_nm[komune])
        else:
            expr_string = " \"kommune\" > 0"
        where = "WHERE lokalId > 0"
        if fylke != "Norge":
            if komune == self.uspesifisert:
                where = where + " AND " + "(kommune = '{0}'".format(self.fylke_dict[fylke][0])
                for komune_nr in range(1, len(self.fylke_dict[fylke])-1):
                    where = where + " OR kommune = '{0}'".format(self.fylke_dict[fylke][komune_nr])
                where = where + ")"
            else:
                where = where + " AND " + "kommune = '{0}'".format(self.komm_dict_nm[komune])

        #genererer express string og where spørringer basert på tilstndte attributter
        for attribute in attributes:
            where = self.create_where_statement(attribute, where)
            expr_string = self.create_where_statement2(attribute, expr_string)

        #Genererer lag basert på virtuell metode eller memory metode
        if sok_metode == "virtual":
            
            layer_name_text = layer_name.text() + "Virtual"
            base_layer_name = baselayer.name()
            query = "SELECT * FROM " + base_layer_name + " " + where
            self.current_search_layer = QgsVectorLayer("?query=%s" % (query), layer_name_text, "virtual" )

            if self.current_search_layer.featureCount() > 0: #Lager lag hvis noen objecter er funnet
                if len(QgsMapLayerRegistry.instance().mapLayersByName(layer_name_text)) > 0:
                    try:
                        QgsMapLayerRegistry.instance().removeMapLayer( QgsMapLayerRegistry.instance().mapLayersByName(layer_name_text)[0].id() ) #Fjerner lag med samme navn, for å ungå duplicates
                    except (RuntimeError, AttributeError) as e:
                        print(str(e))

                QgsMapLayerRegistry.instance().addMapLayer(self.current_search_layer) #Legger inn nytt lag
                self.fill_infoWidget(attributes)
                self.canvas.setExtent(self.current_search_layer.extent()) #zoomer inn på nytt lag
                self.iface.addDockWidget( Qt.LeftDockWidgetArea , self.infoWidget ) #legger inn infowidget
                self.showResults(self.current_search_layer) #Legger inn tabell
                #self.sourceMapTool.setLayer(self.current_search_layer) #new layer target for tools

                self.search_history[layer_name_text] = SavedSearch(layer_name_text, self.current_search_layer, layer_name, self.dlg.tabWidget_main.currentIndex(), self.dlg.tabWidget_friluft.currentIndex(), self.dlg.tabWidget_tettsted.currentIndex()) #lagerer søkets tab indes, lagnavn og lag referanse
                for attribute in attributes: #lagrer valg av attributter
                    self.search_history[layer_name_text].add_attribute(attribute, int(attribute.getComboBox().currentIndex()), attribute.getLineEditText())

                self.search_history[layer_name_text].add_attribute(self.fylker, int(self.fylker.getComboBox().currentIndex()), None) #lagerer valg og fylter og komuner
                self.search_history[layer_name_text].add_attribute(self.kommuner, int(self.kommuner.getComboBox().currentIndex()), None)
                if self.infoWidget.comboBox_search_history.findText(layer_name_text) == -1: #Legger til ikke existerende søk i søk historien
                    self.infoWidget.comboBox_search_history.addItem(layer_name_text)
                self.dlg.close() #lukker hovedvindu for enklere se resultater
                
            else:
                self.show_message("Søket fullførte uten at noen objecter ble funnet", "ingen Objecter funnet", msg_info=None, msg_details=None, msg_type=None) #Melding som vises om søket feilet
        
        if sok_metode == "memory": #self.dlg.comboBox_sok_metode.currentText() == "memory":
            try:
                QgsMapLayerRegistry.instance().removeMapLayer( tempLayer )
            except (RuntimeError, AttributeError, UnboundLocalError):
                pass

            layer_name_text = layer_name.text()# + "Memory"

            if search_type == "Vei":
                tempLayer = QgsVectorLayer("LineString?crs=epsg:4326", layer_name_text, "memory")
            elif search_type == search_type_pomrade:
                tempLayer = QgsVectorLayer("Polygon?crs=epsg:4326", layer_name_text, "memory")
            else:
                tempLayer = QgsVectorLayer("Point?crs=epsg:4326", layer_name_text, "memory")

            if len(expr_string) == 0: #tester en liten ting med gitKrakken
                #expr_string = " \"kommune\" > 0"
                temp_data = mem_layer.dataProvider()
                attr = layer.dataProvider().fields().toList()
                temp_data.addAttributes(attr)
                tempLayer.updateFields()
                temp_data.addFeatures(feats)
            else:
                expr = QgsExpression(expr_string)
                it = baselayer.getFeatures( QgsFeatureRequest( expr ) )
                ids = [i.id() for i in it]
                baselayer.setSelectedFeatures( ids )
                selectedFeatures = baselayer.selectedFeatures()
                temp_data = tempLayer.dataProvider()
                attr = baselayer.dataProvider().fields().toList()
                temp_data.addAttributes(attr)
                tempLayer.updateFields()
                temp_data.addFeatures(selectedFeatures)

            if tempLayer.featureCount() > 0:
                existing_layers = self.iface.legendInterface().layers()
                try:
                    for layer in existing_layers: #Removing layers with same name
                        if layer.name() == tempLayer.name():
                            QgsMapLayerRegistry.instance().removeMapLayers( [layer.id()] )
                except Exception as e:
                    print(str(e))

                self.current_search_layer = tempLayer
                QgsMapLayerRegistry.instance().addMapLayer(self.current_search_layer)

                #self.canvas.setExtent(self.current_search_layer.extent())
                #self.canvas.refresh()
                tempLayer.triggerRepaint()
                self.iface.addDockWidget( Qt.LeftDockWidgetArea , self.infoWidget )
                #self.sourceMapTool.setLayer(self.current_search_layer)
                self.showResults(self.current_search_layer)
                self.fill_infoWidget(attributes)

                self.search_history[layer_name_text] = SavedSearch(layer_name_text, self.current_search_layer, layer_name, self.dlg.tabWidget_main.currentIndex(), self.dlg.tabWidget_friluft.currentIndex(), self.dlg.tabWidget_tettsted.currentIndex()) #lagerer søkets tab indes, lagnavn og lag referanse
                for attribute in attributes: #lagrer valg av attributter
                    self.search_history[layer_name_text].add_attribute(attribute, int(attribute.getComboBox().currentIndex()), attribute.getLineEditText())

                self.search_history[layer_name_text].add_attribute(self.fylker, int(self.fylker.getComboBox().currentIndex()), None) #lagerer valg og fylter og komuner
                self.search_history[layer_name_text].add_attribute(self.kommuner, int(self.kommuner.getComboBox().currentIndex()), None)

                self.dlg.close() #closing main window for easyer visualisation of results

            else: #no objects found
                self.show_message("Søket fullførte uten at noen objecter ble funnet", "ingen Objecter funnet", msg_info=None, msg_details=None, msg_type=QMessageBox.Information)
                QgsMapLayerRegistry.instance().removeMapLayer( tempLayer.id() )
        try:
            if self.current_search_layer is not None:
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

        print("Filtering End")


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

        self.cur_sel_obj+=1
        if self.cur_sel_obj >= self.number_of_objects:
            self.cur_sel_obj = 0
        self.obj_info()
        self.highlightSelected()

    def infoWidget_prev(self):
        """shows previus object in infoWidget"""
        self.cur_sel_obj-=1
        if self.cur_sel_obj < 0:
            self.cur_sel_obj = self.number_of_objects-1
        self.obj_info()
        self.highlightSelected()


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
                    if isinstance(selection[self.cur_sel_obj][self.to_unicode(self.current_attributes[i].getAttribute())], (int, float, long)):
                        self.infoWidget.gridLayout.itemAtPosition(i, 1).widget().setText(str(selection[self.cur_sel_obj][self.to_unicode(self.current_attributes[i].getAttribute())]))
                    elif isinstance(selection[self.cur_sel_obj][self.to_unicode(self.current_attributes[i].getAttribute())], (QPyNullVariant)):
                        self.infoWidget.gridLayout.itemAtPosition(i, 1).widget().setText("-")
                    else:
                        self.infoWidget.gridLayout.itemAtPosition(i, 1).widget().setText(selection[self.cur_sel_obj][self.to_unicode(self.current_attributes[i].getAttribute())])
                except Exception as e:
                    print(str(e))
                    self.infoWidget.gridLayout.itemAtPosition(i, 1).widget().setText("-")
                    print(self.current_attributes[i].getAttribute())
                    print(selection[self.cur_sel_obj][self.to_unicode(self.current_attributes[i].getAttribute())])
        else:
            for i in range(0, len(self.current_attributes)):
                self.infoWidget.gridLayout.itemAtPosition(i, 1).widget().setText("-")
                    
    

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
        ;type msg_type: QMessageBox.Icon
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
        """obtaind from xytools, author: Richard Duivenvoorde
        Saves features to excel format
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
