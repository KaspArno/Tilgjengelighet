from qgis.PyQt.QtCore import pyqtSignal, QPyNullVariant
from qgis.PyQt.QtGui import QPixmap, QCursor
from qgis.core import QgsVectorLayer, QgsFeature, QgsExpression, QgsFeatureRequest
from qgis.gui import QgsMapToolIdentify

from infoWidgetDialog import infoWidgetDialog



class IdentifyGeometry(QgsMapToolIdentify):
    geomIdentified = pyqtSignal(QgsVectorLayer, QgsFeature)

    def __init__(self, canvas, infoWidget, attributes, pickMode = 'selection'):
        self.canvas = canvas
        QgsMapToolIdentify.__init__(self, canvas)
        self.setCursor(QCursor())
        self.layer = None

        self.current_attributes = attributes

        self.infoWidget = infoWidget
        if pickMode == 'all':
            self.selectionMode = self.TopDownStopAtFirst
        elif pickMode == 'selection':
            self.selectionMode = self.LayerSelection
        elif pickMode == 'active':
            self.selectionMode = self.ActiveLayer

    def canvasReleaseEvent(self, mouseEvent):
        '''
        try:
            results = self.identify(mouseEvent.x(), mouseEvent.y(), self.LayerSelection, self.VectorLayer)
        except:
        '''
        results = self.identify(mouseEvent.x(), mouseEvent.y(), self.selectionMode, self.VectorLayer)
        # print dir(results[0].mFeature.attributes())
        # print results[0].mFeature.fields().field(0).displayName()
        # print results[0].mFeature.attributes()[0]
        # print dir(results[0].mFeature.fields().field(0))
        if len(results) > 0:
            self.fillInfoWidget(results)
            #for i in range(0, len(results[0].mFeature.attributes())):
            #    print results[0].mFeature.fields().field(i).displayName(), " ", results[0].mFeature.attributes()[i]
            self.geomIdentified.emit(results[0].mLayer, QgsFeature(results[0].mFeature))

    def setLayer(self, layer):
        self.layer = layer

        self.feature_id = {}
        feat = layer.getFeatures() #resetting iterator
        for f in feat:
            self.feature_id[f['gml_id']] = f.id()

    def to_unicode(self, in_string):
        if isinstance(in_string,str):
            out_string = in_string.decode('utf-8')
        elif isinstance(in_string,unicode):
            out_string = in_string
        else:
            raise TypeError('not stringy')
        return out_string

    def fillInfoWidget(self, results):
        expr = QgsExpression( "\"gml_id\"=\'{0}\'".format(results[0].mFeature.attributes()[0]) )
        it = self.layer.getFeatures( QgsFeatureRequest( expr ) )
        ids = [i.id() for i in it]
        self.layer.setSelectedFeatures(ids)
        #self.layer.setSelectedFeatures([self.feature_id[results[0].mFeature.attributes()[0]]])
        #print("feature_id; ", "Key: ", results[0].mFeature.attributes()[0], " Value: ", self.feature_id[results[0].mFeature.attributes()[0]])
        selection = self.layer.selectedFeatures()

        for feature in selection:
            for i in range(0, len(self.current_attributes)): #self.infoWidget.gridLayout.rowCount()):
                try:
                    if isinstance(feature[self.to_unicode(self.current_attributes[i].getAttribute())], (int, float, long)):
                        self.infoWidget.gridLayout.itemAtPosition(i, 1).widget().setText(str(feature[self.to_unicode(self.current_attributes[i].getAttribute())]))
                    elif isinstance(feature[self.to_unicode(self.current_attributes[i].getAttribute())], (QPyNullVariant)):
                        self.infoWidget.gridLayout.itemAtPosition(i, 1).widget().setText("-")
                    else:
                        self.infoWidget.gridLayout.itemAtPosition(i, 1).widget().setText(feature[self.to_unicode(self.current_attributes[i].getAttribute())])
                except Exception as e:
                    self.infoWidget.gridLayout.itemAtPosition(i, 1).widget().setText("-")
                    print(self.current_attributes[i].getAttribute())
                    print(feature[self.to_unicode(self.current_attributes[i].getAttribute())])
                    print(str(e))

        # infoWidget_label_list = [self.infoWidget.label_avstand_hc_text, self.infoWidget.label_byggningstype_text, self.infoWidget.label_ank_vei_stigning_text, self.infoWidget.label_dortype_text, self.infoWidget.label_dorapner_text, self.infoWidget.label_ringeklokke_text, self.infoWidget.label_ringeklokke_hoyde_text, self.infoWidget.label_terskelhoyde_text, self.infoWidget.label_inngang_bredde_text, self.infoWidget.label_kontrast_text, self.infoWidget.label_rampe_text]
        # values = [results[0].mFeature.attributes()[17], results[0].mFeature.attributes()[10], results[0].mFeature.attributes()[25], results[0].mFeature.attributes()[19], results[0].mFeature.attributes()[20], results[0].mFeature.attributes()[24], results[0].mFeature.attributes()[32], results[0].mFeature.attributes()[21], results[0].mFeature.attributes()[26], results[0].mFeature.attributes()[18]]
        # for i in range(0, len(values)):
        #     #infoWidget_label_list[i].setText(values[i])
        #     try:
        #         if isinstance(values[i], (int, float, long)):
        #             infoWidget_label_list[i].setText(str(values[i]))
        #             #infoWidget_label_list[i].setText((str(feature[self.att_info_list[i]])))
        #         elif isinstance(values[i], (QPyNullVariant)):
        #             infoWidget_label_list[i].setText("-")
        #         else:
        #             infoWidget_label_list[i].setText(values[i])
        #             #infoWidget_label_list[i].setText((feature[self.att_info_list[i]]))
        #     except Exception as e:
        #         infoWidget_label_list[i].setText("-")
        #         print(e)