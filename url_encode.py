def url_encode(url):
	replace_list ={'<' : '%3C', '>' : '%3E', ' ' : '%20', '"' : '%22'}

	for x in replace_list:
		url = url.replace(x, replace_list[x])

	return url


test = 'http://wfs.geonorge.no/skwms1/wfs.tilgjengelighet_tettsted?service=WFS&request=GetFeature&version=2.0.0&srsName=urn:ogc:def:crs:EPSG::3857&typeNames=app:TettstedInngangBygg&resultType=Hits&FILTER=<fes:Filter xmlns:app="http://skjema.geonorge.no/SOSI/produktspesifikasjon/TilgjengelighetTettsted/1.2"><fes:PropertyIsGreaterThan><fes:ValueReference>app:rampe/app:Rampe/app:rampeLengde</fes:ValueReference><fes:Literal>800</fes:Literal></fes:PropertyIsGreaterThan></fes:Filter>'
test = url_encode(test)


FrankText = 'http://wfs.geonorge.no/skwms1/wfs.tilgjengelighet_tettsted?service=WFS&request=GetFeature&version=2.0.0&srsName=urn:ogc:def:crs:EPSG::3857&typeNames=app:TettstedInngangBygg&resultType=Hits&FILTER=%3Cfes:Filter%20xmlns:app=%22http://skjema.geonorge.no/SOSI/produktspesifikasjon/TilgjengelighetTettsted/1.2%22%3E%3Cfes:PropertyIsGreaterThan%3E%3Cfes:ValueReference%3Eapp:rampe/app:Rampe/app:rampeLengde%3C/fes:ValueReference%3E%3Cfes:Literal%3E800%3C/fes:Literal%3E%3C/fes:PropertyIsGreaterThan%3E%3C/fes:Filter%3E'


if test == FrankText:
	print('Text Match! :)')