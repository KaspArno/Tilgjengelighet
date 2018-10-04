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
from functools import partial


# Initialize Qt resources from file resources.py
import resources_rc

# Import the code for the dialog
from Tilgjengelighet_dialog import TilgjengelighetDialog
from tabledialog import TableDialog
from infowidgetdialog import infoWidgetDialog

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
        self.iface = iface #Accsess to QGIS interface
        self.canvas = self.iface.mapCanvas() #Access to QGIS canvas
        self.settings = QSettings() #Access to QGIS settings
        
        
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        self.plugin_dir = os.path.dirname(__file__) #Plugin path
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
        self.settings.setValue("/Qgis/dockAttributeTable", True) #Get attribute table at bottom of screen

        #Layer and attributes
        self.current_search_layer = None #The last searched layer
        self.current_attributes = None #The attributes for current search layer
        self.search_history = {} #history of all search
        self.rubberHighlight = None #Marking the object currently visulised in infoWidget
        self.unspecified = u"" #unspecified attributes

       #Lists of feature types for tettested and friluft, key equeals name of tabs
        self.feature_type_tettsted = {
            u"HC-Parkering" : u'TettstedHCparkering', u"Inngang" : u'TettstedInngangBygg', 
            u'Parkeringsomr\xe5de' : u'TettstedParkeringsomr\xe5de', u"Vei" : u'TettstedVei'
            } #use this to get featuretype based on current tab
        self.feature_type_friluft = {
            u'Baderampe' : u'FriluftBaderampe', u'Fiskeplass' : u'FriluftFiskeplass', 
            u'Turvei' : u'FriluftTurvei', u'HC-Parkeringsplass' : u'FriluftHCparkering', 
            u'Parkeringsområde' : u'FriluftParkeringsområde', u'Friluftsområder' : u'FriluftFriluftsområde',
            u'Gapahuk' : u'FriluftGapahuk', u'Grill-/Bålplass' : u'FriluftGrillBålplass',
            u'Sittegruppe' : u'FriluftSittegruppe', u'Toalett' : u'FriluftToalett'}

        #Path to combobox values
        self.path_tilgjenglighetsvurdering = self.plugin_dir + r"\combobox_values\tilgjengvurdering.txt"
        self.path_more_less = self.plugin_dir + r'\combobox_values\mer_mindre.txt'
        self.path_boolean = self.plugin_dir + r'\combobox_values\boolean.txt'
        self.path_dortype = self.plugin_dir + r"\combobox_values\tettstedInngangByggningstype.txt"
        self.path_dorapner = self.plugin_dir + r"\combobox_values\dorapner.txt"
        self.path_kontrast = self.plugin_dir + r"\combobox_values\kontrast.txt"
        self.path_handlist = self.plugin_dir + r"\combobox_values\handlist.txt"
        self.path_ledelinje = self.plugin_dir + r"\combobox_values\ledelinje.txt"

        self.path_byggfunksjon = self.plugin_dir + r"\combobox_values\dortype.txt"
        self.path_gatetype = self.plugin_dir + r'\combobox_values\tettstedVeiGatetype.txt'
        self.path_dekke_tettsted = self.plugin_dir + r"\combobox_values\tettstedDekke.txt"
        self.path_dekketilstand = self.plugin_dir + r"\combobox_values\dekkeTilstand.txt"

        self.path_dekke_friluft = self.plugin_dir + r'\combobox_values\dekkeTilstand.txt'



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

        #Set Icons main tab
        self.dlg.tabWidget_main.setTabIcon(0, QIcon(":/plugins/Tilgjengelighet/icons/friluft.png"))
        self.dlg.tabWidget_main.setTabIcon(1, QIcon(":/plugins/Tilgjengelighet/icons/tettsted.png"))

        #change search name based on tab
        self.dlg.tabWidget_main.currentChanged.connect(self.change_search_name) #change search name based on tab
        self.dlg.tabWidget_friluft.currentChanged.connect(self.change_search_name)
        self.dlg.tabWidget_tettsted.currentChanged.connect(self.change_search_name)
        self.change_search_name() #Initiate a search name

        #Connect pushbuttons
        self.dlg.pushButton_filtrer.clicked.connect(self.filtrer) #Connect pushbytton filtrer action
        self.dlg.pushButton_reset.clicked.connect(self.reset) #resett all choses made by user

        ### table window ###
        ## NB: Table window changed to attribute table
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

        # Set tools an icons
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
        self.fylke_valgt() #Filling up kommune combobox

        #set combobox functions
        self.dlg.comboBox_fylker.currentIndexChanged.connect(self.fylke_valgt) #Filling cityes from county
        self.dlg.comboBox_fylker.currentIndexChanged.connect(self.change_search_name) #setting search name based on fylke
        self.dlg.comboBox_kommuner.currentIndexChanged.connect(self.change_search_name) #setting search name based on komune

        #Assign fylker and kommuner to AttributeForm
        self.fylker = AttributeForm("fylker", self.dlg.label_fylke)
        self.fylker.setComboBox(self.dlg.comboBox_fylker)
        self.kommuner = AttributeForm("komune", self.dlg.label_kommune)
        self.kommuner.setComboBox(self.dlg.comboBox_kommuner)

        #Create attributes object tettsted
        self.assign_combobox_inngang()
        self.assign_combobox_vei()
        self.assign_combobox_hc_parkering()
        self.assign_combobox_parkeringsomraade()

        #Create attributes object friluft (Needs futher methods for filling rest of friluft)
        self.assign_combobox_baderampe()
        self.assign_combobox_fiskeplass()

        #Dictionarys for all attributes in different object type. Key equals name of tab
        self.attributes_tettsted = {
            u"HC-Parkering" : self.attributes_hcparkering, u"Inngang" : self.attributes_inngang, 
            u'Parkeringsområde' : self.attributes_pomrade, u"Vei" : self.attributes_vei}

        self.attributes_friluft = {
            u"Baderampe" : self.attributes_baderampe, u"Fiskeplass" : self.attributes_fiskeplass
        }

        
        self.openLayer_background_init() #Activate open layers
        

    ############################# Assign widget to attributeform and fill comboboxes #################################

    def assign_combobox_inngang(self):
        """Assigning a AttributeForm object to each option in inngang"""
        
        self.avstandHC = AttributeForm("avstandHC", self.dlg.comboBox_avstand_hc, self.dlg.lineEdit_avstand_hc)
        self.ank_stigning = AttributeForm("stigningAdkomstvei", self.dlg.comboBox_ank_stigning, self.dlg.lineEdit_ank_stigning)
        self.byggningstype = AttributeForm("byggningsfunksjon", self.dlg.comboBox_byggningstype)
        self.rampe = AttributeForm("rampe", self.dlg.comboBox_rampe, comboBoxText={"" : "", "Ja" : "1", "Nei" : "0"})
        self.dortype = AttributeForm(u'dørtype', self.dlg.comboBox_dortype)
        self.dorapner = AttributeForm(u'døråpner', self.dlg.comboBox_dorapner)
        self.man_hoyde = AttributeForm(u'manøverknappHøyde', self.dlg.comboBox_man_hoyde, self.dlg.lineEdit_man_hoyde)
        self.dorbredde = AttributeForm("InngangBredde", self.dlg.comboBox_dorbredde, self.dlg.lineEdit_dorbredde)
        self.terskel = AttributeForm(u'terskelH\xf8yde', self.dlg.comboBox_terskel, self.dlg.lineEdit_terskel)
        self.kontrast = AttributeForm("kontrast", self.dlg.comboBox_kontrast)
        self.rampe_stigning = AttributeForm("rampeStigning", self.dlg.comboBox_rmp_stigning, self.dlg.lineEdit_rmp_stigning, label=self.dlg.label_rmp_stigning)
        self.rampe_bredde = AttributeForm("rampeBredde", self.dlg.comboBox_rmp_bredde, self.dlg.lineEdit_rmp_bredde, label=self.dlg.label_rmp_bredde)
        self.handlist = AttributeForm(u'h\xe5ndlist', self.dlg.comboBox_handliste, label=self.dlg.label_handliste)
        self.handlist1 = AttributeForm(u'håndlistHøydeØvre', self.dlg.comboBox_hand1, self.dlg.lineEdit_hand1, label=self.dlg.label_hand1)
        self.handlist2 = AttributeForm(u'håndlistHøydeNedre', self.dlg.comboBox_hand2, self.dlg.lineEdit_hand2, label=self.dlg.label_hand2)
        self.rmp_tilgjengelig = AttributeForm("rampeTilgjengelig", self.dlg.comboBox_rmp_tilgjengelig, label=self.dlg.label_rmp_tilgjengelig)
        self.manuellRullestol = AttributeForm("tilgjengvurderingRulleAuto", self.dlg.comboBox_manuell_rullestol)
        self.elektriskRullestol = AttributeForm("tilgjengvurderingElRull", self.dlg.comboBox_el_rullestol)
        self.synshemmet = AttributeForm("tilgjengvurderingSyn", self.dlg.comboBox_syn)

        self.attributes_inngang = [self.avstandHC, self.ank_stigning, self.byggningstype, self.rampe, self.dortype, self.dorapner, self.man_hoyde, self.dorbredde, self.terskel, self.kontrast, self.rampe_stigning, self.rampe_bredde, self.handlist, self.handlist1, self.handlist2, self.rmp_tilgjengelig, self.manuellRullestol, self.elektriskRullestol, self.synshemmet]
        self.attributes_inngang_gui = [self.byggningstype, self.dortype, self.dorapner, self.kontrast, self.handlist, self.rmp_tilgjengelig, self.manuellRullestol, self.elektriskRullestol, self.synshemmet]
        self.attributes_inngang_mer_mindre = [self.avstandHC, self.ank_stigning, self.man_hoyde, self.dorbredde, self.terskel, self.rampe_stigning, self.rampe_bredde, self.handlist1, self.handlist2]
        self.attributes_rampe = [self.rampe_stigning, self.rampe_bredde, self.handlist, self.handlist1, self.handlist2, self.rmp_tilgjengelig]

        #fill combobox
        path = ":/plugins/Tilgjengelighet/" #Mey not need this
        for attributt in self.attributes_inngang_mer_mindre:
            self.fill_combobox(attributt.getComboBox(), self.path_more_less)

        self.fill_combobox(self.rampe.getComboBox(), self.path_boolean)
        self.fill_combobox(self.byggningstype.getComboBox(), self.path_byggfunksjon)
        self.fill_combobox(self.dortype.getComboBox(), self.path_dortype)
        self.fill_combobox(self.dorapner.getComboBox(), self.path_dorapner)
        self.fill_combobox(self.kontrast.getComboBox(), self.path_kontrast)
        self.fill_combobox(self.handlist.getComboBox(), self.path_kontrast)

        self.fill_combobox(self.rmp_tilgjengelig.getComboBox(), self.path_tilgjenglighetsvurdering)
        self.fill_combobox(self.manuellRullestol.getComboBox(), self.path_tilgjenglighetsvurdering)
        self.fill_combobox(self.elektriskRullestol.getComboBox(), self.path_tilgjenglighetsvurdering)
        self.fill_combobox(self.synshemmet.getComboBox(), self.path_tilgjenglighetsvurdering)

        #Set what to be hidden in form and conditions for showing parts
        self.hide_show_gui(self.attributes_rampe, self.dlg.comboBox_rampe.currentText() == u"Ja", [self.dlg.label_rampe_boxs, self.dlg.line_inngang_rampe, self.dlg.line])
        self.dlg.comboBox_rampe.currentIndexChanged.connect(lambda: self.hide_show_gui(self.attributes_rampe, self.dlg.comboBox_rampe.currentText() == u"Ja", [self.dlg.label_rampe_boxs, self.dlg.line_inngang_rampe, self.dlg.line]))
        #self.dlg.comboBox_rampe.currentIndexChanged.connect(self.hide_show_rampe)


    def assign_combobox_vei(self):
        """Assigning a AttributeForm object to each option in vei"""

        gatetype = AttributeForm("gatetype", self.dlg.comboBox_gatetype)
        nedsenkning1 = AttributeForm("nedsenk1", self.dlg.comboBox_nedsenkning1, self.dlg.lineEdit_nedsenkning1, label=self.dlg.label_nedsenkning1)
        nedsenkning2 = AttributeForm("nedsenk2", self.dlg.comboBox_nedsenkning2, self.dlg.lineEdit_nedsenkning2, label=self.dlg.label_nedsenkning2)
        dekke_vei_tettsted = AttributeForm("dekke", self.dlg.comboBox_dekke_vei_tettsted)
        dekkeTilstand_vei_tettsted = AttributeForm("dekkeTilstand", self.dlg.comboBox_dekkeTilstand_vei_tettsted)
        bredde = AttributeForm("bredde", self.dlg.comboBox_bredde, self.dlg.lineEdit_bredde)
        stigning = AttributeForm("stigning", self.dlg.comboBox_stigning, self.dlg.lineEdit_stigning)
        tverfall = AttributeForm("tverrfall", self.dlg.comboBox_tverfall, self.dlg.lineEdit_tverfall)
        ledelinje = AttributeForm("ledelinje", self.dlg.comboBox_ledelinje)
        ledelinjeKontrast = AttributeForm("ledelinjeKontrast", self.dlg.comboBox_ledelinjeKontrast)

        manuell_rullestol_vei = AttributeForm("tilgjengvurderingRulleAuto", self.dlg.comboBox_manuell_rullestol_vei)
        electrisk_rullestol_vei = AttributeForm("tilgjengvurderingElRull", self.dlg.comboBox_electrisk_rullestol_vei)
        syn_vei = AttributeForm("tilgjengvurderingSyn", self.dlg.comboBox_syn_vei)

        self.attributes_vei = [gatetype, nedsenkning1, nedsenkning2, dekke_vei_tettsted, dekkeTilstand_vei_tettsted, bredde, stigning, tverfall, ledelinje, ledelinjeKontrast, manuell_rullestol_vei, electrisk_rullestol_vei, syn_vei]
        attributes_vei_gui = [gatetype, dekke_vei_tettsted, dekkeTilstand_vei_tettsted, ledelinje, ledelinjeKontrast, manuell_rullestol_vei, electrisk_rullestol_vei, syn_vei]
        attributes_vei_mer_mindre = [nedsenkning1,nedsenkning2,bredde,stigning,tverfall]
        attributes_nedsenkning = [nedsenkning1, nedsenkning2]

        #fill combobox
        for attributt in attributes_vei_mer_mindre:
            self.fill_combobox(attributt.getComboBox(), self.path_more_less)

        self.fill_combobox(gatetype.getComboBox(), self.path_gatetype)
        self.fill_combobox(dekke_vei_tettsted.getComboBox(), self.path_dekke_tettsted)
        self.fill_combobox(dekkeTilstand_vei_tettsted.getComboBox(), self.path_dekketilstand)
        self.fill_combobox(ledelinje.getComboBox(), self.path_ledelinje)
        self.fill_combobox(ledelinjeKontrast.getComboBox(), self.path_kontrast)
        
        self.fill_combobox(manuell_rullestol_vei.getComboBox(), self.path_tilgjenglighetsvurdering)
        self.fill_combobox(electrisk_rullestol_vei.getComboBox(), self.path_tilgjenglighetsvurdering)
        self.fill_combobox(syn_vei.getComboBox(), self.path_tilgjenglighetsvurdering)

        #Set what to be hidden in form and conditions for showing parts
        self.hide_show_gui(attributes_nedsenkning, self.dlg.comboBox_gatetype.currentText() != self.unspecified)
        self.dlg.comboBox_gatetype.currentIndexChanged.connect(lambda: self.hide_show_gui(attributes_nedsenkning, self.dlg.comboBox_gatetype.currentText() != self.unspecified))


    def assign_combobox_hc_parkering(self):
        """Assigning a AttributeForm object to each option in hc parkering"""

        avstandServicebygg = AttributeForm("avstandServicebygg", self.dlg.comboBox_avstandServicebygg, self.dlg.lineEdit_avstandServicebygg)

        overbygg = AttributeForm("overbygg", self.dlg.comboBox_overbygg, comboBoxText={"" : "", "Ja" : "1", "Nei" : "0"})
        skiltet = AttributeForm("skiltet", self.dlg.comboBox_skiltet, comboBoxText={"" : "", "Ja" : "1", "Nei" : "0"})
        merket = AttributeForm("merket", self.dlg.comboBox_merket, comboBoxText={"" : "", "Ja" : "1", "Nei" : "0"})

        bredde_hcp_merke = AttributeForm("bredde", self.dlg.comboBox_bredde_hcp_merke, self.dlg.lineEdit_bredde_hcp_merke, label=self.dlg.label_bredde_hcp_merke)
        lengde_hcp_merke = AttributeForm("lengde", self.dlg.comboBox_lengde_hcp_merke, self.dlg.lineEdit_lengde_hcp_merke, label=self.dlg.label_lengde_hcp_merke)

        manuell_rullestol_hcparkering = AttributeForm("tilgjengvurderingRulleAuto", self.dlg.comboBox_manuell_rullestol_hcparkering)
        elektrisk_rullestol_hcparkering = AttributeForm("tilgjengvurderingElRull", self.dlg.comboBox_elektrisk_rullestol_hcparkering)

        self.attributes_hcparkering = [avstandServicebygg, overbygg, skiltet, merket, bredde_hcp_merke, lengde_hcp_merke, manuell_rullestol_hcparkering, elektrisk_rullestol_hcparkering]
        attributes_hcparkering_gui = [manuell_rullestol_hcparkering, elektrisk_rullestol_hcparkering]
        attributes_hcparkering_mer_mindre = [avstandServicebygg, bredde_hcp_merke, lengde_hcp_merke]

        #fill combobox
        for attributt in self.attributes_hcparkering:
            self.fill_combobox(attributt.getComboBox(), self.path_more_less)

        self.fill_combobox(overbygg.getComboBox(), self.path_boolean)
        self.fill_combobox(skiltet.getComboBox(), self.path_boolean)
        self.fill_combobox(merket.getComboBox(), self.path_boolean)
        
        self.fill_combobox(manuell_rullestol_hcparkering.getComboBox(), self.path_tilgjenglighetsvurdering)
        self.fill_combobox(elektrisk_rullestol_hcparkering.getComboBox(), self.path_tilgjenglighetsvurdering)

        #Set what to be hidden in form and conditions for showing parts
        self.hide_show_gui([bredde_hcp_merke, lengde_hcp_merke], self.dlg.comboBox_merket.currentText() == "Ja")
        self.dlg.comboBox_merket.currentIndexChanged.connect(lambda: self.hide_show_gui([bredde_hcp_merke, lengde_hcp_merke], self.dlg.comboBox_merket.currentText() == "Ja"))


    def assign_combobox_parkeringsomraade(self):
        """Assigning a AttributeForm object to each option in parkeringsområde"""

        self.overbygg_pomrade = AttributeForm("overbygg", self.dlg.comboBox_overbygg_pomrade, comboBoxText={"" : "", "Ja" : "1", "Nei" : "0"})
        self.kapasitetPersonbiler = AttributeForm("kapasitetPersonbiler", self.dlg.comboBox_kapasitetPersonbiler, self.dlg.lineEdit_kapasitetPersonbiler)
        self.kapasitetUU = AttributeForm("antallUU", self.dlg.comboBox_kapasitetUU, self.dlg.lineEdit_kapasitetUU)
        self.dekke_pomrade = AttributeForm("dekke", self.dlg.comboBox_dekke_pomrade)
        self.dekkeTilstand_pomrade = AttributeForm("dekkeTilstand", self.dlg.comboBox_dekkeTilstand_pomrade)

        self.manuell_rullestol_pomrade = AttributeForm("tilgjengvurderingRulleAuto", self.dlg.comboBox_manuell_rullestol_pomrade)

        self.attributes_pomrade = [self.overbygg_pomrade, self.kapasitetPersonbiler, self.kapasitetUU, self.dekke_pomrade, self.dekkeTilstand_pomrade, self.manuell_rullestol_pomrade]
        self.attributes_pomrade_gui = [self.dekke_pomrade, self.dekkeTilstand_pomrade, self.manuell_rullestol_pomrade]
        self.attributes_pomrade_mer_mindre = [self.kapasitetPersonbiler, self.kapasitetUU]

        #fill combobox
        for attributt in self.attributes_pomrade_mer_mindre:
            self.fill_combobox(attributt.getComboBox(), self.path_more_less)

        self.fill_combobox(self.overbygg_pomrade.getComboBox(), self.path_boolean)
        self.fill_combobox(self.dekke_pomrade.getComboBox(), self.path_dekke_tettsted)
        self.fill_combobox(self.dekkeTilstand_pomrade.getComboBox(), self.path_dekketilstand)
        
        self.fill_combobox(self.manuell_rullestol_pomrade.getComboBox(), self.path_tilgjenglighetsvurdering)


    def assign_combobox_baderampe(self):
        """Assigning a AttributeForm object to each option in Baderampe"""

        rampe = AttributeForm(u"rampe", self.dlg.comboBox_baderampe_rampe, comboBoxText={"" : "", "Ja" : "1", "Nei" : "0"})
        rampeBredde = AttributeForm(u"rampeBredde", self.dlg.comboBox_baderampe_rampeBredde, self.dlg.lineEdit_baderampe_rampeBredde)
        rampeStigning = AttributeForm(u"rampeStigning", self.dlg.comboBox_baderampe_rampeStigning, self.dlg.lineEdit_baderampe_rampeStigning)
        handlist = AttributeForm(u"håndlist", self.dlg.comboBox_baderampe_handliste)
        handlistHoyde1 = AttributeForm(u"håndlistHøyde1", self.dlg.comboBox_baderampe_handlistHoyde1, self.dlg.lineEdit_baderampe_handlistHoyde1)
        handlistHoyde2 = AttributeForm(u"håndlistHøyde2", self.dlg.comboBox_baderampe_handlistHoyde2, self.dlg.lineEdit_baderampe_handlistHoyde2)
        rampeTilgjengelig =  AttributeForm(u"rampeTilgjengelig", self.dlg.comboBox_baderampe_rampeTilgjengelig)

        tilgjengvurderingRullestol = AttributeForm(u"tilgjengvurderingRulleAuto", self.dlg.comboBox_baderampe_tilgjengvurderingRullestol)
        tilgjengvurderingSyn = AttributeForm(u"tilgjengvurderingSyn", self.dlg.comboBox_baderampe_tilgjengvurderingSyn)

        self.attributes_baderampe = [rampe, rampeBredde, rampeStigning, handlist, handlistHoyde1, handlistHoyde2, rampeTilgjengelig, tilgjengvurderingRullestol, tilgjengvurderingSyn]
        attributes_mer_mindre = [rampeBredde, rampeStigning, handlistHoyde1, handlistHoyde2]

        #Fill combobox
        for attributt in attributes_mer_mindre:
            self.fill_combobox(attributt.getComboBox(), self.path_more_less)

        self.fill_combobox(rampe.getComboBox(), self.path_boolean)
        self.fill_combobox(handlist.getComboBox(), self.path_handlist)
        self.fill_combobox(rampeTilgjengelig.getComboBox(), self.path_tilgjenglighetsvurdering)
        self.fill_combobox(tilgjengvurderingRullestol.getComboBox(), self.path_tilgjenglighetsvurdering)
        self.fill_combobox(tilgjengvurderingSyn.getComboBox(), self.path_tilgjenglighetsvurdering)

    def assign_combobox_fiskeplass(self):
        """Assigning a AttributeForm object to each option in Baderampe"""

        rampe = AttributeForm(u"rampe", self.dlg.comboBox_fiskeplass_rampe, label=self.dlg.label_fiskeplass_rampe, comboBoxText={"" : "", "Ja" : "1", "Nei" : "0"})
        dekke = AttributeForm(u"dekke", self.dlg.comboBox_fiskeplass_dekke)
        plankeavstand =  AttributeForm(u"plankeavstand  ", self.dlg.comboBox_fiskeplass_plankeavstand, self.dlg.lineEdit_fiskeplass_plankeavstand,  label=self.dlg.label_fiskeplass_plankeavstand)
        dekkeTilstand = AttributeForm(u"dekkeTilstand", self.dlg.comboBox_fiskeplass_dekke_tilstand)
        diameter = AttributeForm(u"diameter", self.dlg.comboBox_fiskeplass_snusirkel, self.dlg.lineEdit_fiskeplass_snusirkel)
        rekkverk = AttributeForm(u"rekkverk", self.dlg.comboBox_fiskeplass_rekkverk, comboBoxText={"" : "", "Ja" : "1", "Nei" : "0"})
        stoppkant = AttributeForm(u"stoppkant", self.dlg.comboBox_fiskeplass_stoppkant, comboBoxText={"" : "", "Ja" : "1", "Nei" : "0"})
        stoppkantHoyde = AttributeForm(u"stoppkantHøyde", self.dlg.comboBox_fiskeplass_stoppkant_hoyde, self.dlg.lineEdit_fiskeplass_stoppkant_hoyde, label=self.dlg.label_fiskeplass_stoppkant_hoyde)

        rampeBredde = AttributeForm(u"rampeBredde", self.dlg.comboBox_fiskeplass_rampe_bredde, self.dlg.lineEdit_fiskeplass_rampe_bredde, label=self.dlg.label_fiskeplass_rampe_bredde)
        rampeStigning = AttributeForm(u"rampeStigning", self.dlg.comboBox_fiskeplass_rampe_stigning, self.dlg.lineEdit_fiskeplass_rampe_stigning, label=self.dlg.label_fiskeplass_rampe_stigning)
        handlist = AttributeForm(u"håndlist", self.dlg.comboBox_fiskeplass_handliste, label=self.dlg.label_fiskeplass_handliste)
        handlistHoyde1 = AttributeForm(u"håndlistHøyde1", self.dlg.comboBox_fiskeplass_handlist1, self.dlg.lineEdit_fiskeplass_handlist1, label=self.dlg.label_fiskeplass_handlist1)
        handlistHoyde2 = AttributeForm(u"håndlistHøyde2", self.dlg.comboBox_fiskeplass_handlist2, self.dlg.lineEdit_fiskeplass_handlist2, label=self.dlg.label_fiskeplass_handlist2)
        rampeTilgjengelig =  AttributeForm(u"rampeTilgjengelig", self.dlg.comboBox_fiskeplass_rampe_tilgjengelig, label=self.dlg.label_fiskeplass_rampe_tilgjengelig)

        tilgjengvurderingRullestol = AttributeForm(u"tilgjengvurderingRulleAuto", self.dlg.comboBox_fiskeplass_manuell_rullestol)
        tilgjengvurderingElRullestol = AttributeForm(u"tilgjengvurderingElRullestol", self.dlg.comboBox_fiskeplass_el_rullestol)
        tilgjengvurderingSyn = AttributeForm(u"tilgjengvurderingSyn", self.dlg.comboBox_fiskeplass_syn)

        self.attributes_fiskeplass = [rampe, dekke, plankeavstand, dekkeTilstand, diameter, rekkverk, stoppkant, stoppkantHoyde, rampeBredde, rampeStigning, handlist, handlistHoyde1, handlistHoyde2, rampeTilgjengelig, tilgjengvurderingRullestol, tilgjengvurderingElRullestol, tilgjengvurderingSyn]
        attributes_mer_mindre = [plankeavstand, diameter, stoppkantHoyde, rampeBredde, rampeStigning, handlistHoyde1, handlistHoyde2]
        attributes_rampe = [rampeBredde, rampeStigning, handlist, handlistHoyde1, handlistHoyde2, rampeTilgjengelig]

        #Fill combobox
        for attributt in attributes_mer_mindre:
            self.fill_combobox(attributt.getComboBox(), self.path_more_less)

        self.fill_combobox(rampe.getComboBox(), self.path_boolean)
        self.fill_combobox(dekke.getComboBox(), self.path_dekke_friluft)
        self.fill_combobox(dekkeTilstand.getComboBox(), self.path_dekketilstand)
        self.fill_combobox(rekkverk.getComboBox(), self.path_boolean)
        self.fill_combobox(stoppkant.getComboBox(), self.path_boolean)

        self.fill_combobox(handlist.getComboBox(), self.path_handlist)
        self.fill_combobox(rampeTilgjengelig.getComboBox(), self.path_tilgjenglighetsvurdering)
        self.fill_combobox(tilgjengvurderingRullestol.getComboBox(), self.path_tilgjenglighetsvurdering)
        self.fill_combobox(tilgjengvurderingElRullestol.getComboBox(), self.path_tilgjenglighetsvurdering)
        self.fill_combobox(tilgjengvurderingSyn.getComboBox(), self.path_tilgjenglighetsvurdering)

        #Set what to be hidden in form and conditions for showing parts
        self.hide_show_gui(attributes_rampe, self.dlg.comboBox_fiskeplass_rampe.currentText() == u"Ja", [self.dlg.label_fiskeplass_rampe, self.dlg.line_fiskeplass_rampe, self.dlg.line_fiskeplass])
        self.dlg.comboBox_fiskeplass_rampe.currentIndexChanged.connect(lambda: self.hide_show_gui(attributes_rampe, self.dlg.comboBox_fiskeplass_rampe.currentText() == u"Ja", [self.dlg.label_fiskeplass_rampe, self.dlg.line_fiskeplass_rampe, self.dlg.line_fiskeplass]))
        
        self.hide_show_gui([plankeavstand], self.dlg.comboBox_fiskeplass_dekke.currentText() != self.unspecified)
        self.dlg.comboBox_fiskeplass_dekke.currentIndexChanged.connect(lambda: self.hide_show_gui([plankeavstand], self.dlg.comboBox_fiskeplass_dekke.currentText() != self.unspecified))

        self.hide_show_gui([stoppkantHoyde], self.dlg.comboBox_fiskeplass_stoppkant.currentText() == u"Ja")
        self.dlg.comboBox_fiskeplass_stoppkant.currentIndexChanged.connect(lambda: self.hide_show_gui([stoppkantHoyde], self.dlg.comboBox_fiskeplass_stoppkant.currentText() == u"Ja"))




    ################################# Automate tools ####################################

    def resolve(name, basepath=None):
        if not basepath:
          basepath = os.path.dirname(os.path.realpath(__file__))
        return os.path.join(basepath, name)


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


    def hide_show_gui(self, attributeForms, condition, extra = None):
        """Shows parts of GUI if conditions are meat, hids it if not

        :param attributeForms: A list of witch attributes to hide in GUI
        :type attributeForms: list<AttributeForm>
        :param condition: The condition to show GUI parts
        :type condition: boolean
        :param extra: include if gui consists of more than attributes that needs to be showed/hidden
        :type extra: list<QtWidgets>
        """

        #Itterate throu alle attributes that need to be hidden or showd
        for attribute in attributeForms:
            attribute.getComboBox().setVisible(condition)
            if attribute.getLineEdit():
                attribute.getLineEdit().setVisible(condition)
            if attribute.getLabel():
                attribute.getLabel().setVisible(condition)
        
        if extra: #Hide/Show additional widgets
            for widget in extra:
                widget.setVisible(condition)

    def fill_combobox(self, combobox, filename):
        """Fikks combobox with lines from filename

        :param combobox: The combobox to be filled
        :type combobox: QComboBox
        :param filename: name of file with info to be filled in combobox
        :type filename: str, QString
        """

        combobox.clear() #Clear possible information in combobox
        combobox.addItem(self.unspecified) #Include an empty, unspesifised field for combobox
        with open(filename, 'r') as file:
            for line in file:
                combobox.addItem(self.to_unicode(line).rstrip('\n')) #Add line to combobox


    def fill_infoWidget(self, attributes):
        """Filling infowidget with attributes name and no value. Also ajustes size of infowidget

        :param attributes: List of gui attriibutes
        :type attributes: list<AttributeForms>
        """

        for i in range(0, len(attributes)):
            self.infoWidget.gridLayout.itemAtPosition(i, 0).widget().setText(attributes[i].getAttribute()) #Sets attribute name
            self.infoWidget.gridLayout.itemAtPosition(i, 1).widget().setText("-") #Set sign for no value

            #Show line in case the line is hidden
            self.infoWidget.gridLayout.itemAtPosition(i, 0).widget().setVisible(True)
            self.infoWidget.gridLayout.itemAtPosition(i, 1).widget().setVisible(True)

        for i in range(len(attributes), self.infoWidget.gridLayout.rowCount()): #Hides rows that are not used
            self.infoWidget.gridLayout.itemAtPosition(i, 0).widget().setVisible(False)
            self.infoWidget.gridLayout.itemAtPosition(i, 1).widget().setVisible(False)


    def fill_fylker(self):
        """Fill up the combobox fylker with fylker from komm.txt"""

        self.dlg.comboBox_fylker.clear()
        self.dlg.comboBox_fylker.addItem("Norge") #Option for not chosing a single county

        filename = self.plugin_dir + "\komm.txt"

        #Inititate dictionarys for fylke and kommune
        self.komm_dict_nr = {}
        self.komm_dict_nm = {}
        self.fylke_dict = {}

        with io.open(filename, 'r', encoding='utf-8') as f:
            for line in f:
                komm_nr, kommune, fylke = line.rstrip('\n').split(("\t")) #remove linebreak, spilt on tab

                #translate text to unicode
                komm_nr = self.to_unicode(komm_nr)
                kommune = self.to_unicode(kommune)
                fylke = self.to_unicode(fylke)

                #Fill dictionarys
                self.komm_dict_nr[komm_nr] = kommune
                self.komm_dict_nm[kommune] = komm_nr

                #If fylke is not in combobox, add fylke and list to fylke_dict
                if not fylke in self.fylke_dict:
                    self.fylke_dict[fylke] = []
                    self.dlg.comboBox_fylker.addItem(fylke)

                self.fylke_dict[fylke].append(komm_nr) #add kommune numbers to fylke list in fylke dict


    ############################ Actions ##################################

    def get_previus_search_activeLayer(self):
        """Open filtering window set to preweus choises"""

        activeLayer = self.iface.activeLayer()
        #if self.search_history[activeLayer.name()]:
        if activeLayer is not None and activeLayer.name() in self.search_history: #Check that actice layers is in search history
            try:
                pre_search = self.search_history[activeLayer.name()] #Get previus search
                for key, value in pre_search.attributes.iteritems(): #key: AttributeForm, value[0]: combobox index, value[1]; lineEdit text
                    key.getComboBox().setCurrentIndex(int(value[0])) #Set combobx to given index
                    if value[1]: #if attribute has lineEdit and text
                        key.getLineEdit().setText(value[1]) #Fill lineEdit with given text
                self.dlg.tabWidget_main.setCurrentIndex(pre_search.tabIndex_main) #set main tab to given index
                self.dlg.tabWidget_friluft.setCurrentIndex(pre_search.tabIndex_friluft) #Set friluft tab to given index
                self.dlg.tabWidget_tettsted.setCurrentIndex(pre_search.tabIndex_tettsted) #Set tettsted tab to given index
                self.dlg.lineEdit_search_name.setText(self.layer_name) #Sett search name to given text
                self.dlg.show() #Open filtrer window

            except KeyError:
                raise



    def fylke_valgt(self):
        """Fill up kommune combobox with kommune in chosen fylke"""

        fylke = self.dlg.comboBox_fylker.currentText()
        self.dlg.comboBox_kommuner.clear() #Clear combobox to fill with new values
        self.dlg.comboBox_kommuner.addItem(self.unspecified) #Add unspesified value
        if fylke != "Norge": #If value other that Norge was chosen
            try:
                for kommune_nr in self.fylke_dict[fylke]: #Fill combobx with all values given county
                    self.dlg.comboBox_kommuner.addItem(self.komm_dict_nr[kommune_nr]) #Get kommune name from kommune nummber
            except Exception as e:
                print(str(e))
        else: #No spesific county chosen, add all kommuner
            filename = self.plugin_dir + "\komm.txt"
            try:
                with io.open(filename, 'r', encoding='utf-8') as f:
                    for line in f:
                        komm_nr, komune, fylke = line.rstrip('\n').split(("\t"))
                        self.dlg.comboBox_kommuner.addItem(self.komm_dict_nr[komm_nr])
            except Exception as e:
                print(str(e))


    def kommune_valgt(self):
        """Alter the name on seach after a kommune is chosen"""

        if self.dlg.comboBox_kommuner.currentText() != "": #A kommune is chocen
            self.dlg.lineEdit_search_name.setText(self.dlg.lineEdit_search_name.text() + ": " + self.dlg.comboBox_kommuner.currentText()) #Set searchname with name of kommune as ending
        else:
            self.dlg.lineEdit_search_name.setText(self.dlg.lineEdit_search_name.text() + ": " + self.dlg.comboBox_fylker.currentText()) #Set searchname with name of county as ending


    def change_search_name(self):
        """Changes the name of search based on current tab and fyle and kommune"""

        self.dlg.lineEdit_search_name.setText(self.dlg.tabWidget_main.tabText(self.dlg.tabWidget_main.currentIndex()))
        if self.dlg.tabWidget_main.currentIndex() == 0: #If main tab is in friluft
            self.dlg.lineEdit_search_name.setText(self.dlg.lineEdit_search_name.text() + " " + self.dlg.tabWidget_friluft.tabText(self.dlg.tabWidget_friluft.currentIndex()))
        else: #if main tab is in tettsted
            self.dlg.lineEdit_search_name.setText(self.dlg.lineEdit_search_name.text() + " " + self.dlg.tabWidget_tettsted.tabText(self.dlg.tabWidget_tettsted.currentIndex()))

        self.kommune_valgt()
        # if self.dlg.comboBox_kommuner.currentText() != "":
        #     self.dlg.lineEdit_search_name.setText(self.dlg.lineEdit_search_name.text() + ": " + self.dlg.comboBox_kommuner.currentText())
        # else:
        #     self.dlg.lineEdit_search_name.setText(self.dlg.lineEdit_search_name.text() + ": " + self.dlg.comboBox_fylker.currentText())


    def save_search(self):
        """"Saves the search to search history so it can set choises in GUI bac to preveus desisions"""

        self.search_history[self.layer_name] = SavedSearch(self.layer_name, self.current_search_layer, self.dlg.tabWidget_main.currentIndex(), self.dlg.tabWidget_friluft.currentIndex(), self.dlg.tabWidget_tettsted.currentIndex()) #saves search tab index, layer name and layer referense
        for attribute in self.current_attributes: #Stores the choises made in current form
            self.search_history[self.layer_name].add_attribute(attribute, int(attribute.getComboBox().currentIndex()), attribute.getLineEditText()) #Attributes are stored as key in dictionary, index and tex are stored as value

        self.search_history[self.layer_name].add_attribute(self.fylker, int(self.fylker.getComboBox().currentIndex()), None) #stores the choises of fylke and kommune
        self.search_history[self.layer_name].add_attribute(self.kommuner, int(self.kommuner.getComboBox().currentIndex()), None)


    def show_tabell(self):
        """Shows or hide tableWidget"""

        if self.infoWidget.pushButton_tabell.isChecked(): #If pushbutton tabell is check, open attributetable, if not, close attributetable
            self.iface.showAttributeTable(self.iface.activeLayer())
        else:
            attrTables = [d for d in QApplication.instance().allWidgets() if d.objectName() == u'QgsAttributeTableDialog' or d.objectName() == u'AttributeTable']
            for x in attrTables:
                x.close()


    def create_filter(self, opperator, valueReference, value):
        """creates FE based on input, made to take less space in other method create_filtherencoding

        :param opperator: opperator for FE
        :type opperator: str
        :param valueReference: name of attribute for FE
        :type valueReference: str
        :param value: value for FE
        :type value: str
        """

        constraint = u"<fes:{0}><fes:ValueReference>app:{1}</fes:ValueReference><fes:Literal>{2}</fes:Literal></fes:{0}>".format(opperator,valueReference,value)
        return constraint


    def create_filtherencoding(self, attributeList):
        """creates FE based on user choices

        :param attributeList: list of all attriubtes for filterencoding
        :type attributeList: list<AttributeForms>

        :returns: FilterEncoding
        :rtype: str
        """

        fylke = self.dlg.comboBox_fylker.currentText()
        kommune = self.dlg.comboBox_kommuner.currentText()
        constraint = []
        query = ""
        if fylke != "Norge" and  kommune == self.unspecified: #County is chosen, not kommune
            for kommune_nr in range(0, len(self.fylke_dict[fylke])): #itterate all kommune numbers in fylke
                valueReference = "kommune" 
                if len(self.fylke_dict[fylke][kommune_nr]) < 4: #Syntax demands 4 numbers in kommune number
                    value = "0" + self.fylke_dict[fylke][kommune_nr]
                else:
                    value = self.fylke_dict[fylke][kommune_nr]
                query += "<fes:PropertyIsEqualTo><fes:ValueReference>app:{0}</fes:ValueReference><fes:Literal>{1}</fes:Literal></fes:PropertyIsEqualTo>".format(valueReference,value) #Input values to FE
                    
            if len(self.fylke_dict[fylke]) > 1: #Oslo only has 1 kommune, and can't use 'OR' opperators
                query = "<Or>{0}</Or>".format(query) #Add string within 'OR' to include all kommune numbers
        elif kommune != self.unspecified: #Kommune is chosen
            valueReference = "kommune"
            if len(self.komm_dict_nm[kommune]) < 4: #Syntax demands 4 numbers in kommune number
                        value = "0" + self.komm_dict_nm[kommune]
            else:
                value = self.komm_dict_nm[kommune]
            query += "<fes:PropertyIsEqualTo><fes:ValueReference>app:{0}</fes:ValueReference><fes:Literal>{1}</fes:Literal></fes:PropertyIsEqualTo>".format(valueReference,value) #Input values to FE



        if len(query) > 0: #A fylke or kommune is chocen
            constraint.append(query)
        
        for attribute in attributeList: #Itterate all attributes in search
            if attribute.getComboBoxCurrentText() != self.unspecified: #Combobox  value defined
                valueReference = attribute.valueReference() #Get valueReference
                value = attribute.value() #Get FE value
                opperator = attribute.opperator() #Get FE opperator
                constraint.append(self.create_filter(opperator, valueReference, value)) #Add contraint to list of constraints

        query = ""
        filterString = ""
        if len(constraint) > 1: #More than one constraint, contraint must be withing 'AND'
            for q in constraint:
                query += q #Create constraint string
            filterString = u"<fes:Filter><And>{0}</And></fes:Filter>".format(query)
            return ("FILTER=" + self.to_unicode(filterString))
        elif len(constraint) == 1: #One constraint, contraint cabn't be withing And
            filterString = u"<fes:Filter>{0}</fes:Filter>".format(self.to_unicode(constraint[0]))
            return ("FILTER=" + self.to_unicode(filterString))

        return filterString #return empty filsterString (without "Filter=")
        
        
    def filtrer(self):
        """Makes FE and layer based on choises from user an current tab"""

        if self.current_search_layer is not None: #Remove selection for previus search layer
            self.current_search_layer.removeSelection()

        self.layer_name = self.dlg.lineEdit_search_name.text() #gives search layer a name

        if self.dlg.tabWidget_main.currentIndex() < 1: #Maintab is set at friluft, gets values for friluft
            tilgjDB = "friluft"
            featuretype = self.feature_type_friluft[self.dlg.tabWidget_friluft.tabText(self.dlg.tabWidget_friluft.currentIndex())] #gets feature type based on freaturetype tab in friluft
            self.current_attributes = self.attributes_friluft[self.dlg.tabWidget_friluft.tabText(self.dlg.tabWidget_friluft.currentIndex())] #gets attributes based on freaturetype tab in friluft
            infoWidget_title = self.dlg.tabWidget_friluft.tabText(self.dlg.tabWidget_friluft.currentIndex()) #gets infowidget title based on freaturetype tab in friluft
        else: #Main tab is set at tettsted, gets values for tettsted
            tilgjDB = "tettsted"
            featuretype = self.feature_type_tettsted[self.dlg.tabWidget_tettsted.tabText(self.dlg.tabWidget_tettsted.currentIndex())] #gets feature type based on freaturetype tab in tettsted
            self.current_attributes = self.attributes_tettsted[self.dlg.tabWidget_tettsted.tabText(self.dlg.tabWidget_tettsted.currentIndex())] #gets attributes based on freaturetype tab in tettsted
            infoWidget_title = self.dlg.tabWidget_tettsted.tabText(self.dlg.tabWidget_tettsted.currentIndex()) #gets infowidget title based on freaturetype tab in tettsted

        #Create url
        url = u"http://wfs.geonorge.no/skwms1/wfs.tilgjengelighet{0}?service=WFS&request=GetFeature&version=2.0.0&srsName=urn:ogc:def:crs:EPSG::4258&typeNames=app:{1}&".format(tilgjDB, featuretype)
        #print("url: {}".format(url))
        #Create FE
        filter_encoding = self.create_filtherencoding(self.current_attributes)#= "FILTER=<fes:Filter><fes:PropertyIsEqualTo><fes:ValueReference>app:kommune</fes:ValueReference><fes:Literal>0301</fes:Literal></fes:PropertyIsEqualTo></fes:Filter>"
        #print("FE: {}".format(filter_encoding))
        #Create new layer
        new_layer = QgsVectorLayer(url + filter_encoding, self.layer_name, "ogr")

        if new_layer.isValid(): #If new layer is valid/contains objekcts, add to canvas
            existing_layers = self.iface.legendInterface().layers()
            try:
                for lyr in existing_layers: #Removing layers with same name
                    if lyr.name() == new_layer.name():
                        QgsMapLayerRegistry.instance().removeMapLayers( [lyr.id()] )
            except Exception as e:
                print(str(e))
            QgsMapLayerRegistry.instance().addMapLayer(new_layer) #Add new layer

            self.current_search_layer = new_layer #Sett current layer
            self.current_search_layer.selectionChanged.connect(self.selectedObjects) #Filling infoWidget when objects are selected
            
            #Zoom to layer
            self.canvas.setExtent(self.current_search_layer.extent())
            self.canvas.zoomOut()

            #inititate new infowidget
            self.fill_infoWidget(self.current_attributes)
            self.infoWidget.label_typeSok.setText(infoWidget_title)
            self.infoWidget.show()

            #Close old atribute table
            attrTables = [d for d in QApplication.instance().allWidgets() if d.objectName() == u'QgsAttributeTableDialog' or d.objectName() == u'AttributeTable']
            for x in attrTables:
                x.close()
            self.show_tabell() #Show or hide new attribute table
            
            if self.rubberHighlight is not None: #removing previus single highlight
                self.canvas.scene().removeItem(self.rubberHighlight)
            
            self.save_search() #Store search attributes
            self.dlg.close() #closing main window for easyer visualisation of results

        else:
            #self.show_message("Ingen objekter funnet", msg_title="layer not valid", msg_type=QMessageBox.Warning) #Messeage if layer is not valid/not objects was found
            self.show_message("WFS client currently down", msg_title="WFS-Client down", msg_type=QMessageBox.Warning)
            self.infoWidget.show()
            self.show_tabell()
            self.dlg.close()


        print(u"NewFilterEnd")


    ############################## Selection and info of Objects ################################################
    
    def selectedObjects(self, selFeatures):
        """changing number of selected objects in infowidget and settning current selected object

        :param selFeatures: Selected features of layer
         """
        self.selFeatures = selFeatures
        self.number_of_objects = len(selFeatures) #number of objects selected
        self.cur_sel_obj = 0 #Current selected object
        self.selection = self.current_search_layer.selectedFeatures() #Set selected features


        self.obj_info() #Fill infowidget with info on current selected object

        self.highlightSelected() #highligt current selected object viewd in infowidget


    def highlightSelected(self):
        """Highlights the object viewed in infowidget"""

        if self.rubberHighlight is not None:
            self.canvas.scene().removeItem(self.rubberHighlight) #remove previus rubberband

        if len(self.selection) > 0: #objects selected is more than 0
            self.rubberHighlight = QgsRubberBand(self.canvas,QGis.Polygon) #create new rubberband
            self.rubberHighlight.setBorderColor(QColor(255,0,0)) #Set birder color for new rubberband (red)
            self.rubberHighlight.setFillColor(QColor(255,0,0,255)) #set fill color for new rubberband (red)
            #self.rubberHighlight.setLineStyle(Qt.PenStyle(Qt.DotLine))
            self.rubberHighlight.setWidth(4) #Set widht of new rubberband
            self.rubberHighlight.setToGeometry(self.selection[self.cur_sel_obj].geometry(), self.current_search_layer) #set geometry of rubberband equal to current selected object
            self.rubberHighlight.show() #Show rubberband

    def infoWidget_next(self):
        """shows next object in infoWidget"""
        try:
            self.cur_sel_obj+=1
            if self.cur_sel_obj >= self.number_of_objects: #when exiding objects, go back to first
                self.cur_sel_obj = 0
            self.obj_info() #Fill infowidget with new info
            self.highlightSelected() #set new rubberband to highlight new object
        except AttributeError as e:
            pass
        except Exception as e:
            raise e
        

    def infoWidget_prev(self):
        """shows previus object in infoWidget"""
    
        try:
            self.cur_sel_obj-=1
            if self.cur_sel_obj < 0: #when exiding objects, go to last
                self.cur_sel_obj = self.number_of_objects-1
            self.obj_info() #Fill infowidget with new info
            self.highlightSelected() #set new rubberband to highlight new object
        except AttributeError as e:
            pass
        except Exception as e:
            raise e


    def obj_info(self):
        """Fills infowidget with info of current object"""
    
        self.infoWidget.label_object_number.setText("{0}/{1}".format(self.cur_sel_obj+1, self.number_of_objects)) #Show current object, and number of objects selected
    
        
        if len(self.selection) > 0:
            for i in range(0, len(self.current_attributes)):
                try:
                    value = self.selection[self.cur_sel_obj][self.to_unicode(self.current_attributes[i].getAttribute())] #Get attribute value of current selected objects for 
                    try: #insert valu to infowidget
                        if isinstance(value, (int, float, long)):
                            self.infoWidget.gridLayout.itemAtPosition(i, 1).widget().setText(str(value)) #make value str
                        elif isinstance(value, (QPyNullVariant)): #No value
                            self.infoWidget.gridLayout.itemAtPosition(i, 1).widget().setText("-")
                        else:
                            self.infoWidget.gridLayout.itemAtPosition(i, 1).widget().setText(value)
                    except Exception as e:
                        self.infoWidget.gridLayout.itemAtPosition(i, 1).widget().setText("-") #No value
                except KeyError as e: #attribute not in layer do to no value in any objects
                    pass
        else: #No objects chocen, set value to "-"
            for i in range(0, len(self.current_attributes)):
                self.infoWidget.gridLayout.itemAtPosition(i, 1).widget().setText("-")


    def show_message(self, msg_text, msg_title=None, msg_info=None, msg_details=None, msg_type=None):
        """Show the user a message
        :param msg_text: the tekst to show the user
        :type msg_text: str

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


    


    def savePath(self, saveType, saveExtension): #find savepath
        """Find the save path

        :param saveType: The type of file to be saved
        :type saveType: str
        :param saveExtension: File extention (e.g .xls .png)
        :type saveExtension: str
        :returns: direktory path and file namle
        :rtype: (str,str)
        """

        dirPath = self.settings.value("/Tilgjengelighet/savePath", ".", type=str)
        #Open file expoorer and save file
        (filename, filter) = QFileDialog.getSaveFileNameAndFilter(self.iface.mainWindow(),
                    "Please save {0} file as...".format(saveType),
                    dirPath,
                    "{0} files (*{1})".format(saveType, saveExtension),
                    "Filter list for selecting files from a dialog box")
        fn, fileExtension = os.path.splitext(unicode(filename))
        if len(fn) == 0: # user choose cancel
            return None, None
        self.settings.setValue("/Tilgjengelighet/savePath", QFileInfo(filename).absolutePath())
        if fileExtension != saveExtension: #set file extention to filename
            filename = filename + saveExtension

        return dirPath, filename #return path to save folder and filname


    def imageSave(self):
        """saves a screenshot of canvas"""

        dirPath, filename = self.savePath("Image", ".png")
        if dirPath is None: #user chose cansel
            return

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

        #add all attributes to list
        for attributeList in self.attributes_tettsted:
            all_attributes.extend(self.attributes_tettsted[attributeList])
        for attributeList in self.attributes_friluft:
            all_attributes.extend(self.attributes_friluft[attributeList])

        for attribute in all_attributes:
            attribute.reset() #resets attribute value



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

        dirPath, filename = self.savePath("Excel", ".xls")
       
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
