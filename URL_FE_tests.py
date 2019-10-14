http://wfs.geonorge.no/skwms1/wfs.tilgjengelighet_tettsted?service=WFS&request=GetFeature&version=2.0.0&srsName=urn:ogc:def:crs:EPSG::3857&typeNames=app:TettstedInngangBygg&

http://wfs.geonorge.no/skwms1/wfs.tilgjengelighet_tettsted?service=WFS&request=GetFeature&version=2.0.0&srsName=urn:ogc:def:crs:EPSG::3857&typeNames=app:TettstedInngangBygg&resultType=Hits&

FILTER=<fes:Filter><fes:PropertyIsEqualTo><fes:ValueReference>app:kommune</fes:ValueReference><fes:Literal>0301</fes:Literal></fes:PropertyIsEqualTo></fes:Filter>


FILTER=<fes:Filter><fes:PropertyIsEqualTo><fes:ValueReference>app:Rampe//app:rampeLengde</fes:ValueReference><fes:Literal>800</fes:Literal></fes:PropertyIsEqualTo></fes:Filter>

FILTER=<fes:Filter>
    <fes:PropertyIsEqualTo>
        <fes:ValueReference>app:rampe/app:Rampe/app:rampeLengde</fes:ValueReference>
        <fes:Literal>0301</fes:Literal>
    </fes:PropertyIsEqualTo>
</fes:Filter>

FILTER=<fes:Filter><fes:PropertyIsGreaterThan><fes:ValueReference>'app:rampe/app:Rampe/app:rampeLengde'</fes:ValueReference><fes:Literal>800</fes:Literal></fes:PropertyIsGreaterThan></fes:Filter>

FILTER=<fes:Filter><fes:PropertyIsGreaterThan><fes:ValueReference><app:rampe><app:Rampe>rampeLengde</app:Rampe></app:rampe></fes:ValueReference><fes:Literal>800</fes:Literal></fes:PropertyIsGreaterThan></fes:Filter>


resultType=result (defult) sender alle resultatene
resultType=Hits sender antall resultater


FILTER=<fes:Filter><And><fes:PropertyIsEqualTo><fes:ValueReference>app:kommune</fes:ValueReference><fes:Literal>0301</fes:Literal></fes:PropertyIsEqualTo><fes:PropertyIsEqualTo><fes:ValueReference>app:rampe</fes:ValueReference><fes:Literal>Ja</fes:Literal></fes:PropertyIsEqualTo><fes:PropertyIsGreaterThan><fes:ValueReference>'app:rampe/app:Rampe/app:rampeStigning'</fes:ValueReference><fes:Literal>200</fes:Literal></fes:PropertyIsGreaterThan></And></fes:Filter>

FILTER=<fes:Filter><And><fes:PropertyIsEqualTo><fes:ValueReference>app:kommune</fes:ValueReference><fes:Literal>0301</fes:Literal></fes:PropertyIsEqualTo><fes:PropertyIsEqualTo><fes:ValueReference>app:rampe</fes:ValueReference><fes:Literal>Ja</fes:Literal></fes:PropertyIsEqualTo><fes:PropertyIsGreaterThan><fes:ValueReference><app:rampe><app:Rampe>app:rampeStigning</app:Rampe></app:rampe></fes:ValueReference><fes:Literal>200</fes:Literal></fes:PropertyIsGreaterThan></And></fes:Filter>

FILTER=<fes:Filter><And><fes:PropertyIsEqualTo><fes:ValueReference>app:kommune</fes:ValueReference><fes:Literal>0301</fes:Literal></fes:PropertyIsEqualTo><fes:PropertyIsEqualTo><fes:ValueReference>app:rampe</fes:ValueReference><fes:Literal>Ja</fes:Literal></fes:PropertyIsEqualTo><fes:PropertyIsGreaterThan><fes:ValueReference>app:rampe/app:Rampe/app:rampeStigning</fes:ValueReference><fes:Literal>200</fes:Literal></fes:PropertyIsGreaterThan></And></fes:Filter>


http://wfs.geonorge.no/skwms1/wfs.tilgjengelighet_tettsted?service=WFS&request=GetFeature&version=2.0.0&srsName=urn:ogc:def:crs:EPSG::3857&typeNames=app:TettstedInngangBygg&resultType=Hits&FILTER=<fes:Filter><fes:PropertyIsGreaterThan><fes:ValueReference><app:rampe><app:Rampe>rampeLengde</app:Rampe></app:rampe></fes:ValueReference><fes:Literal>800</fes:Literal></fes:PropertyIsGreaterThan></fes:Filter>

http://wfs.geonorge.no/skwms1/wfs.tilgjengelighet_tettsted?service=WFS&request=GetFeature&version=2.0.0&srsName=urn:ogc:def:crs:EPSG::3857&typeNames=app:TettstedInngangBygg&resultType=Hits&FILTER=<fes:Filter xmlns:app="http://skjema.geonorge.no/SOSI/produktspesifikasjon/TilgjengelighetTettsted/1.2"><fes:PropertyIsGreaterThan><fes:ValueReference>app:rampe/app:Rampe/app:rampeLengde</fes:ValueReference><fes:Literal>800</fes:Literal></fes:PropertyIsGreaterThan></fes:Filter>


http://wfs.geonorge.no/skwms1/wfs.tilgjengelighet_tettsted?service=WFS&request=GetFeature&version=2.0.0&srsName=urn:ogc:def:crs:EPSG::3857&typeNames=app:TettstedInngangBygg&resultType=Hits&FILTER=%3Cfes:Filter%20xmlns:app=%22http://skjema.geonorge.no/SOSI/produktspesifikasjon/TilgjengelighetTettsted/1.2%22%3E%3Cfes:PropertyIsGreaterThan%3E%3Cfes:ValueReference%3Eapp:rampe/app:Rampe/app:rampeLengde%3C/fes:ValueReference%3E%3Cfes:Literal%3E800%3C/fes:Literal%3E%3C/fes:PropertyIsGreaterThan%3E%3C/fes:Filter%3E

http://wfs.geonorge.no/skwms1/wfs.tilgjengelighet_tettsted?service=WFS&request=GetFeature&version=2.0.0&srsName=urn:ogc:def:crs:EPSG::3857&typeNames=app:TettstedInngangBygg&resultType=Hits&

FILTER=%3Cfes:Filter%20xmlns:app=%22http://skjema.geonorge.no/SOSI/produktspesifikasjon/TilgjengelighetTettsted/1.2%22%3E%3Cfes:PropertyIsGreaterThan%3E%3Cfes:ValueReference%3Eapp:rampe/app:Rampe/app:rampeLengde%3C/fes:ValueReference%3E%3Cfes:Literal%3E800%3C/fes:Literal%3E%3C/fes:PropertyIsGreaterThan%3E%3C/fes:Filter%3E

FILTER=%3D%3Cfes%3AFilter%3E%3Cfes%3APropertyIsGreaterThan%3E%3Cfes%3AValueReference%3E%27app%3Arampe%2Fapp%3ARampe%2Fapp%3ArampeLengde%27%3C%2Ffes%3AValueReference%3E%3Cfes%3ALiteral%3E800%3C%2Ffes%3ALiteral%3E%3C%2Ffes%3APropertyIsGreaterThan%3E%3C%2Ffes%3AFilter%3E


http://wfs.geonorge.no/skwms1/wfs.tilgjengelighet_tettsted?service=WFS&request=GetFeature&version=2.0.0&srsName=urn:ogc:def:crs:EPSG::3857&typeNames=app:TettstedInngangBygg&resultType=Hits&FILTER=<fes:Filter xmlns:app="http://skjema.geonorge.no/SOSI/produktspesifikasjon/TilgjengelighetTettsted/1.2"><fes:PropertyIsGreaterThan><fes:ValueReference>app:rampe/app:Rampe/app:rampeLengde</fes:ValueReference><fes:Literal>800</fes:Literal></fes:PropertyIsGreaterThan></fes:Filter



Frank URL encoded
http://wfs.geonorge.no/skwms1/wfs.tilgjengelighet_tettsted?service=WFS&request=GetFeature&version=2.0.0&srsName=urn:ogc:def:crs:EPSG::3857&typeNames=app:TettstedInngangBygg&resultType=Hits&FILTER=%3Cfes:Filter%20xmlns:app=%22http://skjema.geonorge.no/SOSI/produktspesifikasjon/TilgjengelighetTettsted/1.2%22%3E%3Cfes:PropertyIsGreaterThan%3E%3Cfes:ValueReference%3Eapp:rampe/app:Rampe/app:rampeLengde%3C/fes:ValueReference%3E%3Cfes:Literal%3E800%3C/fes:Literal%3E%3C/fes:PropertyIsGreaterThan%3E%3C/fes:Filter%3E

QGIS (partly URL encoded)
http://wfs.geonorge.no/skwms1/wfs.tilgjengelighet_tettsted?service=WFS&request=GetFeature&version=2.0.0&srsName=urn:ogc:def:crs:EPSG::3857&typeNames=app:TettstedInngangBygg&resultType=Hits&FILTER=%3Cfes:Filter%20xmlns:app=%22http://skjema.geonorge.no/SOSI/produktspesifikasjon/TilgjengelighetTettsted/1.2%22%3E%3Cfes:PropertyIsGreaterThan%3E%3Cfes:ValueReference%3Eapp:rampe/app:Rampe/app:rampeLengde%3C/fes:ValueReference%3E%3Cfes:Literal%3E800%3C/fes:Literal%3E%3C/fes:PropertyIsGreaterThan%3E%3C/fes:Filter%3E




Frank plane
http://wfs.geonorge.no/skwms1/wfs.tilgjengelighet_tettsted?service=WFS&request=GetFeature&version=2.0.0&srsName=urn:ogc:def:crs:EPSG::3857&typeNames=app:TettstedInngangBygg&resultType=Hits&FILTER=<fes:Filter xmlns:app="http://skjema.geonorge.no/SOSI/produktspesifikasjon/TilgjengelighetTettsted/1.2"><fes:PropertyIsGreaterThan><fes:ValueReference>app:rampe/app:Rampe/app:rampeLengde</fes:ValueReference><fes:Literal>800</fes:Literal></fes:PropertyIsGreaterThan></fes:Filter>

Frank URL encodet
http://wfs.geonorge.no/skwms1/wfs.tilgjengelighet_tettsted?service=WFS&request=GetFeature&version=2.0.0&srsName=urn:ogc:def:crs:EPSG::3857&typeNames=app:TettstedInngangBygg&resultType=Hits&FILTER=%3Cfes:Filter%20xmlns:app=%22http://skjema.geonorge.no/SOSI/produktspesifikasjon/TilgjengelighetTettsted/1.2%22%3E%3Cfes:PropertyIsGreaterThan%3E%3Cfes:ValueReference%3Eapp:rampe/app:Rampe/app:rampeLengde%3C/fes:ValueReference%3E%3Cfes:Literal%3E800%3C/fes:Literal%3E%3C/fes:PropertyIsGreaterThan%3E%3C/fes:Filter%3E


Plane text -> URL encoded

< : %3C
space : %20

" : 