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
import time

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
        
        
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        self.plugin_dir = os.path.dirname(__file__)
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

        
        
        #Settnings
        self.settings.setValue("/Qgis/dockAttributeTable", True) 

        #WFS URLS
        self.namespace = "http://skjema.geonorge.no/SOSI/produktspesifikasjon/TilgjengelighetTettsted/4.5"
        self.namespace_prefix = "app"
        self.online_resource = "https://wfs.geonorge.no/skwms1/wfs.tilgjengelighettettsted"

        #GUI dropdown (may not be in use)
        self.uspesifisert = u"" #For emty comboboxses and lineEdtis
        self.mer = u">" #for combobokser linked to more or less iterations
        self.mindre = u"<"
        self.mer_eller_lik = u">="
        self.mindre_eller_lik = u"<="

        #layers and search
        self.layers = [] #gather all baselayers (may not be in use)

        self.current_search_layer = None #The last searched layer
        self.current_attributes = None #The attributes for current search layer
        self.search_history = {} #history of all search
        self.rubberHighlight = None #Marking the object currently visulised in infoWidget

        self.feature_type_tettsted = { u"HC-Parkering" : u'TettstedHCparkering', u"Inngang" : u'TettstedInngangBygg', u'Parkeringsomr\xe5de' : u'TettstedParkeringsomr\xe5de', u"Vei" : u'TettstedVei'} #use this to get featuretype based on current tab

        #Icons (may not be in use)
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

        #to hide layers (may not be in use)
        self.ltv = self.iface.layerTreeView()
        self.model = self.ltv.model()
        self.root = QgsProject.instance().layerTreeRoot()

        #Open Layers, background layers

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


        ### main window ###
        self.dlg.tabWidget_main.setTabIcon(0, QIcon(":/plugins/Tilgjengelighet/icons/friluft.png"))
        self.dlg.tabWidget_main.setTabIcon(1, QIcon(":/plugins/Tilgjengelighet/icons/tettsted.png"))

        self.dlg.pushButton_filtrer.clicked.connect(self.filtrer)

        #change search name based on tab
        self.dlg.tabWidget_main.currentChanged.connect(self.change_search_name) #change search name based on tab
        self.dlg.tabWidget_friluft.currentChanged.connect(self.change_search_name)
        self.dlg.tabWidget_tettsted.currentChanged.connect(self.change_search_name)

        self.dlg.pushButton_reset.clicked.connect(self.reset) #resett all choses made by user

        self.dlg.label_Progress.setVisible(False) #label_prgress currently not in use

        self.change_search_name() #Initiate a search name


        ### table window ###
        self.dock = TableDialog(self.iface.mainWindow())
        self.dock.tableWidget.setSelectionBehavior(QAbstractItemView.SelectRows) #select entire row in table
        self.dock.tableWidget.setEditTriggers(QAbstractItemView.NoEditTriggers) #Making table unediteble
        
        self.iface.addDockWidget( Qt.BottomDockWidgetArea , self.dock ) #adding seartch result Widget
        self.dock.close() #Start pløugin without this dialog

        ### info window ###
        self.infoWidget = infoWidgetDialog(self.iface.mainWindow())
        self.infoWidget.pushButton_filtrer.clicked.connect(lambda x: self.dlg.show()) #open main window
        self.infoWidget.pushButton_filtrer.clicked.connect(self.get_previus_search_activeLayer) #setting main window to match search for active layer
        self.infoWidget.pushButton_next.clicked.connect(self.infoWidget_next) #itterate the selected objekts
        self.infoWidget.pushButton_prev.clicked.connect(self.infoWidget_prev)
        self.infoWidget.pushButton_tabell.clicked.connect(self.show_tabell) #open tableWiddget

        self.selectPolygon = QAction(QIcon(":/plugins/Tilgjengelighet/icons/Select_polygon.gif"),
                                       QCoreApplication.translate("MyPlugin", "Polygon"),
                                       self.iface.mainWindow()) #Change therese icons
        self.selectPoint = QAction(QIcon(":/plugins/Tilgjengelighet/icons/Select_point_1.gif"),
                                       QCoreApplication.translate("MyPlugin", u"Punkt/Frihånd"),
                                       self.iface.mainWindow()) #Change therese icons
        self.selectPolygon.triggered.connect(lambda x: self.iface.actionSelectPolygon().trigger()) #select objects by polygon
        self.selectPoint.triggered.connect(lambda x: self.iface.actionSelectFreehand().trigger()) #select objects by freehand

        self.infoWidget.toolButton_velgikart.addAction(self.selectPolygon)
        self.infoWidget.toolButton_velgikart.addAction(self.selectPoint)

        self.exportExcel = QAction(QIcon(":/plugins/Tilgjengelighet/icons/black-ms-excel-16.png"),
                                       QCoreApplication.translate("MyPlugin", "Excel"),
                                       self.iface.mainWindow()) #Change therese icons
        self.exportImage = QAction(QIcon(":/plugins/Tilgjengelighet/icons/Export_map.gif"),
                                       QCoreApplication.translate("MyPlugin", "Bilde"),
                                       self.iface.mainWindow()) #Change therese icons
        self.exportExcel.triggered.connect(self.excelSave) #export tp excel
        self.exportImage.triggered.connect(self.imageSave) #ecport image

        self.infoWidget.toolButton_eksporter.addAction(self.exportExcel)
        self.infoWidget.toolButton_eksporter.addAction(self.exportImage)

        self.iface.addDockWidget( Qt.BottomDockWidgetArea , self.infoWidget ) #adding seartch result Widget
        self.infoWidget.close() #Start plugin with infoWidget dialog closed


        ### Export window ###
        self.export_layer = exportLayerDialog()
        self.export_layer.pushButton_bla.clicked.connect(self.OpenBrowser)
        self.export_layer.pushButton_lagre.clicked.connect(self.lagre_lag)
        self.export_layer.pushButton_lagre.clicked.connect(lambda x: self.export_layer.close()) #close winwo when you have saved layer
        self.export_layer.pushButton_avbryt.clicked.connect(lambda x: self.export_layer.close())
        
        
        ### Fill gui ###
        self.fill_fylker() #fill fylker combobox
        self.fylke_valgt()

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

        
        self.openLayer_background_init() #Activate open layers
        

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

        #fill combobox
        path = ":/plugins/Tilgjengelighet/" #Mey not need this
        for attributt in self.attributes_inngang_mer_mindre:
            self.fill_combobox(attributt.getComboBox(), self.plugin_dir + '\mer_mindre.txt')

        self.fill_combobox(self.rampe.getComboBox(), self.plugin_dir + r'\boolean.txt')
        self.fill_combobox(self.byggningstype.getComboBox(), self.plugin_dir + r"\tettstedInngangByggningstype.txt")
        self.fill_combobox(self.dortype.getComboBox(), self.plugin_dir + r"\tettstedInngangdortype.txt")
        self.fill_combobox(self.dorapner.getComboBox(), self.plugin_dir + r"\tettstedInngangDorapner.txt")
        self.fill_combobox(self.kontrast.getComboBox(), self.plugin_dir + r"\tettstedKontrast.txt")
        self.fill_combobox(self.handlist.getComboBox(), self.plugin_dir + r"\tettstedInngangHandlist.txt")

        self.fill_combobox(self.rmp_tilgjengelig.getComboBox(), self.plugin_dir + r"\tilgjengvurdering.txt")
        self.fill_combobox(self.manuellRullestol.getComboBox(), self.plugin_dir + r"\tilgjengvurdering.txt")
        self.fill_combobox(self.elektriskRullestol.getComboBox(), self.plugin_dir + r"\tilgjengvurdering.txt")
        self.fill_combobox(self.synshemmet.getComboBox(), self.plugin_dir + r"\tilgjengvurdering.txt")

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

        #fill combobox
        for attributt in self.attributes_vei_mer_mindre:
            self.fill_combobox(attributt.getComboBox(), self.plugin_dir + '\mer_mindre.txt')

        self.fill_combobox(self.gatetype.getComboBox(), self.plugin_dir + r'\tettstedVeiGatetype.txt')
        self.fill_combobox(self.dekke_vei_tettsted.getComboBox(), self.plugin_dir + r"\tettstedDekke.txt")
        self.fill_combobox(self.dekkeTilstand_vei_tettsted.getComboBox(), self.plugin_dir + r"\tettstedDekkeTilstand.txt")
        self.fill_combobox(self.ledelinje.getComboBox(), self.plugin_dir + r"\tettstedVeiLedelinje.txt")
        self.fill_combobox(self.ledelinjeKontrast.getComboBox(), self.plugin_dir + r"\tettstedKontrast.txt")
        
        self.fill_combobox(self.manuell_rullestol_vei.getComboBox(), self.plugin_dir + r"\tilgjengvurdering.txt")
        self.fill_combobox(self.electrisk_rullestol_vei.getComboBox(), self.plugin_dir + r"\tilgjengvurdering.txt")
        self.fill_combobox(self.syn_vei.getComboBox(), self.plugin_dir + r"\tilgjengvurdering.txt")

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

        #fill combobox
        for attributt in self.attributes_hcparkering:
            self.fill_combobox(attributt.getComboBox(), self.plugin_dir + '\mer_mindre.txt')

        self.fill_combobox(self.overbygg.getComboBox(), self.plugin_dir + r'\boolean.txt')
        self.fill_combobox(self.skiltet.getComboBox(), self.plugin_dir + r"\boolean.txt")
        self.fill_combobox(self.merket.getComboBox(), self.plugin_dir + r"\boolean.txt")
        
        self.fill_combobox(self.manuell_rullestol_hcparkering.getComboBox(), self.plugin_dir + r"\tilgjengvurdering.txt")
        self.fill_combobox(self.elektrisk_rullestol_hcparkering.getComboBox(), self.plugin_dir + r"\tilgjengvurdering.txt")

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

        #fill combobox
        for attributt in self.attributes_pomrade_mer_mindre:
            self.fill_combobox(attributt.getComboBox(), self.plugin_dir + '\mer_mindre.txt')

        self.fill_combobox(self.overbygg_pomrade.getComboBox(), self.plugin_dir + r'\boolean.txt')
        self.fill_combobox(self.dekke_pomrade.getComboBox(), self.plugin_dir + r"\tettstedDekke.txt")
        self.fill_combobox(self.dekkeTilstand_pomrade.getComboBox(), self.plugin_dir + r"\tettstedDekkeTilstand.txt")
        
        self.fill_combobox(self.manuell_rullestol_pomrade.getComboBox(), self.plugin_dir + r"\tilgjengvurdering.txt")


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


    #TODO: make generic hide/show modules
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


    def fill_combobox(self, combobox, filename):
        combobox.clear()
        combobox.addItem(self.uspesifisert)
        with open(filename, 'r') as file:
            for line in file:
                combobox.addItem(self.to_unicode(line).rstrip('\n'))


    def fill_infoWidget(self, attributes):
        """Filling infowidget with attributes name and no value. Also ajustes size of infowidget

        :param attributes: List of gui attriibutes
        :type attributes: list<AttributeForms>
        """

        for i in range(0, len(attributes)):
            self.infoWidget.gridLayout.itemAtPosition(i, 0).widget().setText(attributes[i].getAttribute())
            self.infoWidget.gridLayout.itemAtPosition(i, 1).widget().setText("-")

            self.infoWidget.gridLayout.itemAtPosition(i, 0).widget().setVisible(True)
            self.infoWidget.gridLayout.itemAtPosition(i, 1).widget().setVisible(True)

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
        """Fill up komune combobox with kommune in chosen fylke"""

        fylke = self.dlg.comboBox_fylker.currentText()
        self.dlg.comboBox_komuner.clear()
        self.dlg.comboBox_komuner.addItem(self.uspesifisert)
        if fylke != "Norge":
            try:
                for komune_nr in self.fylke_dict[fylke]:
                    self.dlg.comboBox_komuner.addItem(self.komm_dict_nr[komune_nr])
            except Exception as e:
                print(str(e))
        else:
            filename = self.plugin_dir + "\komm.txt"
            try:
                with io.open(filename, 'r', encoding='utf-8') as f:
                    for line in f:
                        komm_nr, komune, fylke = line.rstrip('\n').split(("\t"))
                        self.dlg.comboBox_komuner.addItem(self.komm_dict_nr[komm_nr])
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

        if self.dlg.comboBox_komuner.currentText() != "":
            self.dlg.lineEdit_navn_paa_sok.setText(self.dlg.lineEdit_navn_paa_sok.text() + ": " + self.dlg.comboBox_komuner.currentText())
        else:
            self.dlg.lineEdit_navn_paa_sok.setText(self.dlg.lineEdit_navn_paa_sok.text() + ": " + self.dlg.comboBox_fylker.currentText())


    def save_search(self):
        """"Saves the search to search history so it can set choises in GUI bac to preveus desisions"""

        self.search_history[self.layer_name] = SavedSearch(self.layer_name, self.current_search_layer, self.dlg.tabWidget_main.currentIndex(), self.dlg.tabWidget_friluft.currentIndex(), self.dlg.tabWidget_tettsted.currentIndex()) #lagerer søkets tab indes, lagnavn og lag referanse
        for attribute in self.current_attributes: #lagrer valg av attributter
            self.search_history[self.layer_name].add_attribute(attribute, int(attribute.getComboBox().currentIndex()), attribute.getLineEditText())

        self.search_history[self.layer_name].add_attribute(self.fylker, int(self.fylker.getComboBox().currentIndex()), None) #lagerer valg og fylter og komuner
        self.search_history[self.layer_name].add_attribute(self.kommuner, int(self.kommuner.getComboBox().currentIndex()), None)


    def create_filter(self, opperator, valueReference, value):
        """creates FE based on input, made to take less space in other method"""

        constraint = u"<fes:{0}><fes:ValueReference>app:{1}</fes:ValueReference><fes:Literal>{2}</fes:Literal></fes:{0}>".format(opperator,valueReference,value)
        return constraint


    def create_filtherencoding(self, attributeList):
        """creates FE based on user choices
        :param attributeList:
        :type attributeList:list<AttributeForms>

        :returns: Filter Encoding
        :rtype: str
        """

        fylke = self.dlg.comboBox_fylker.currentText()
        komune = self.dlg.comboBox_komuner.currentText()
        constraint = []
        query = ""
        if fylke != "Norge" and  komune == self.uspesifisert:
            for komune_nr in range(0, len(self.fylke_dict[fylke])):
                valueReference = "kommune"
                if len(self.fylke_dict[fylke][komune_nr]) < 4:
                    value = "0" + self.fylke_dict[fylke][komune_nr]
                else:
                    value = self.fylke_dict[fylke][komune_nr]
                query += "<fes:PropertyIsEqualTo><fes:ValueReference>app:{0}</fes:ValueReference><fes:Literal>{1}</fes:Literal></fes:PropertyIsEqualTo>".format(valueReference,value)
                    
            if len(self.fylke_dict[fylke]) > 1: #Oslo har kun en kommune
                query = "<Or>{0}</Or>".format(query)
        elif komune != self.uspesifisert:
            valueReference = "kommune"
            if len(self.komm_dict_nm[komune]) < 4:
                        value = "0" + self.komm_dict_nm[komune]
            else:
                value = self.komm_dict_nm[komune]
            query += "<fes:PropertyIsEqualTo><fes:ValueReference>app:{0}</fes:ValueReference><fes:Literal>{1}</fes:Literal></fes:PropertyIsEqualTo>".format(valueReference,value)



        if len(query) > 0:
            constraint.append(query)
        
        for attribute in attributeList:
            if attribute.getComboBoxCurrentText() != self.uspesifisert:
                valueReference = attribute.valueReference()
                value = attribute.value()
                opperator = attribute.opperator()
                constraint.append(self.create_filter(opperator, valueReference, value))

        query = ""
        filterString = ""
        if len(constraint) > 1:
            for q in constraint:
                query += q
            filterString = u"<fes:Filter><And>{0}</And></fes:Filter>".format(query)
            return ("FILTER=" + self.to_unicode(filterString))
        elif len(constraint) == 1:
            filterString = "<fes:Filter>{0}</fes:Filter>".format(constraint[0])
            return ("FILTER=" + self.to_unicode(filterString))

        return filterString
        
        
    def filtrer(self):
        """Makes FE and layer based on choises from user an current tab"""

        print (u"NewFilterStart")

        if not self.current_search_layer is None:
            self.current_search_layer.removeSelection()

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

        filter_encoding = self.create_filtherencoding(self.current_attributes)#= "FILTER=<fes:Filter><fes:PropertyIsEqualTo><fes:ValueReference>app:kommune</fes:ValueReference><fes:Literal>0301</fes:Literal></fes:PropertyIsEqualTo></fes:Filter>"

        new_layer = QgsVectorLayer(url + filter_encoding, self.layer_name, "ogr")
        if new_layer.isValid():
            existing_layers = self.iface.legendInterface().layers()
            try:
                for lyr in existing_layers: #Removing layers with same name
                    if lyr.name() == new_layer.name():
                        QgsMapLayerRegistry.instance().removeMapLayers( [lyr.id()] )
            except Exception as e:
                print(str(e))
            QgsMapLayerRegistry.instance().addMapLayer(new_layer)
            self.current_search_layer = new_layer
            self.current_search_layer.selectionChanged.connect(self.selectedObjects) #Filling infoWidget when objects are selected
            
            self.canvas.setExtent(self.current_search_layer.extent())
            self.canvas.zoomOut()

            self.fill_infoWidget(self.current_attributes)
            self.infoWidget.label_typeSok.setText(self.dlg.tabWidget_tettsted.tabText(self.dlg.tabWidget_tettsted.currentIndex()))
            self.infoWidget.show()
            
            if self.rubberHighlight is not None: #removing previus single highlight
                self.canvas.scene().removeItem(self.rubberHighlight)
            self.save_search()
            self.dlg.close() #closing main window for easyer visualisation of results

        else:
            self.show_message("Ingen objekter funnet", msg_title="layer not valid", msg_type=QMessageBox.Warning)


        print(u"NewFilterEnd")


    def selectedObjects(self, selFeatures):
        """changing number of selected objects in infowidget and settning current selected object
        :param selFeatures: Selected features of layer
         """
        self.selFeatures = selFeatures
        self.number_of_objects = len(selFeatures)
        self.cur_sel_obj = 0
        self.selection = self.current_search_layer.selectedFeatures()

        #self.infoWidget.label_object_number.setText("{0}/{1}".format(self.cur_sel_obj+1, self.number_of_objects))
        self.obj_info()

        self.highlightSelected()


    def highlightSelected(self):
        """Highlights the object viewed in infowidget"""

        if self.rubberHighlight is not None:
            self.canvas.scene().removeItem(self.rubberHighlight)

        #selection = self.iface.activeLayer().selectedFeatures()
        if len(self.selection) > 0:
            self.rubberHighlight = QgsRubberBand(self.canvas,QGis.Polygon)
            self.rubberHighlight.setBorderColor(QColor(255,0,0))
            self.rubberHighlight.setFillColor(QColor(255,0,0,255))
            #self.rubberHighlight.setLineStyle(Qt.PenStyle(Qt.DotLine))
            self.rubberHighlight.setWidth(4)
            self.rubberHighlight.setToGeometry(self.selection[self.cur_sel_obj].geometry(), self.current_search_layer)
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
        """Shows or hide tableWidget"""

        if self.infoWidget.pushButton_tabell.isChecked():
            self.iface.showAttributeTable(self.iface.activeLayer())
        else:
            attrTables = [d for d in QApplication.instance().allWidgets() if d.objectName() == u'QgsAttributeTableDialog' or d.objectName() == u'AttributeTable']
            for x in attrTables:
                x.close()
        


    def obj_info(self):
        """Fills infowidget with info of current object"""
    
        self.infoWidget.label_object_number.setText("{0}/{1}".format(self.cur_sel_obj+1, self.number_of_objects))
    
        #selection = self.current_search_layer.selectedFeatures()
        
        if len(self.selection) > 0:
            for i in range(0, len(self.current_attributes)):
                try:
                    value = self.selection[self.cur_sel_obj][self.to_unicode(self.current_attributes[i].getAttribute())]
                    try:
                        if isinstance(value, (int, float, long)):
                            self.infoWidget.gridLayout.itemAtPosition(i, 1).widget().setText(str(value))
                        elif isinstance(value, (QPyNullVariant)):
                            self.infoWidget.gridLayout.itemAtPosition(i, 1).widget().setText("-")
                        else:
                            self.infoWidget.gridLayout.itemAtPosition(i, 1).widget().setText(value)
                    except Exception as e:
                        self.infoWidget.gridLayout.itemAtPosition(i, 1).widget().setText("-")
                except KeyError as e: #Rampe Stigning forsvinner...
                    pass
        else:
            for i in range(0, len(self.current_attributes)):
                self.infoWidget.gridLayout.itemAtPosition(i, 1).widget().setText("-")

    
    def tilgjengelighetsvurdering(self, value, notAcceceble=None, acceceble=None, relate_notAccec=None, relate_acces=None): #Not currently in use
        #["tilgjengelig", "ikkeTilgjengelig", "vanskeligTilgjengelig", "ikkeVurdert"]
        if self.is_float(value):
            value = float(value)
        elif self.is_int(value):
            value = int(value)
            
        if value is None or value == "-" or isinstance(value, QPyNullVariant):
            print("ikkeVurdert")
            return "ikkeVurdert"
        elif notAcceceble:
            if relate_notAccec(value, notAcceceble):
                return "ikkeTilgjengelig"
        elif acceceble:
            if relate_acces(value, acceceble):
                return "tilgjengelig"
        else:
            return "vanskeligTilgjengelig"
        return "ikkeVurdert"

    def is_float(self, value):
        """Checks if an object is float"""

        try:
            float(value)
            return True
        except (ValueError, TypeError) as e:
            return False

    def is_int(self, value):
        """checks if an object is int"""

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

        retval = msg.exec_()
        print(("value of pressed message box button:", retval))


    


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
        """saves a screenshot of canvas"""

        dirPath, filename = self.savePath("Image", ".png")

        size = self.canvas.size()
        image = QImage(size, QImage.Format_RGB32)

        painter = QPainter(image)
        settings = self.canvas.mapSettings()

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
        all_attributes = []

        all_attributes.extend(self.attributes_inngang)
        all_attributes.extend(self.attributes_vei)
        all_attributes.extend(self.attributes_hcparkering)
        all_attributes.extend(self.attributes_pomrade)

        for attribute in all_attributes:
            attribute.reset()



    ###############################################Xy-tools#####################################################
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
            from xytools.providers import excel
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

  ########################### Open Lyaers Plugin ##########################################
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
        mapCanvas = self.canvas # self.iface.mapCanvas()
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
                mapCanvas.setDestinationCrs(coordRefSys)
                #pass
            elif QGis.QGIS_VERSION_INT >= 10900:
                mapCanvas.mapRenderer().setDestinationCrs(coordRefSys)
                #pass
            else:
                mapCanvas.mapRenderer().setDestinationSrs(coordRefSys)
                #pass
            mapCanvas.freeze(False)
            mapCanvas.setMapUnits(coordRefSys.mapUnits())
            mapCanvas.setExtent(extMap)

            




    ###########################################################################


    def run(self):
        #reloadPlugin('Tilgjengelighet')
        """Run method that performs all the real work"""

        self.dlg.show()

        result = self.dlg.exec_()
        # See if OK was pressed
        if result:
            # Do something useful here - delete the line containing pass and
            # substitute with your code.
            pass
