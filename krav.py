class Krav(object):

	def tilgjengelig_manRullestol(attribut, value):
		if attribut. == "avstandHC":
			if value <= 25:
				return True
			else:
				return False
		elif attribut. == u"stigningAdkomstvei":
			if value <= 2.9:
				return True
			else:
				return False
		elif attribut. == u"funksjon":
			pass
		elif attribut. == u"rampe":
			pass
		elif attribut. == u"dørtype":
			pass
		elif attribut. == u"døråpner":
			if value in ["automatisk", "halvautomatisk"]:
				return True:
			else:
				return False
		elif attribut. == u"manøverknappHøyde":
			if value > 80 and value < 110:
				return True
			else:
				return False
		elif attribut. == u"InngangBredde":
			if value >= 90:
				return True
			else:
				return False
		elif attribut. == u"terskelHøyde":
			if value <= 2.5:
				return True
			else:
				return False
		elif attribut. == u"kontrast":
			pass
		elif attribut. == u"rampeStigning":
			pass
		elif attribut. == u"rampeBredde":
			pass
		elif attribut. == u"håndlist":
			pass
		elif attribut. == u"håndlistHøyde1":
			pass
		elif attribut. == u"håndlistHøyde2":
			pass
		elif attribut. == u"rampeTilgjengelig":
			pass
		elif attribut. == u"tilgjengvurderingRullestol":
			pass
		elif attribut. == u"tilgjengvurderingElRull":
			pass
		elif attribut. == u"tilgjengvurderingSyn":
			pass

	def delvis_tilgjengelig_manRullestol(attribut, value):
		if attribut. == "avstandHC":
			if value > 25: #Eller ingen, sett inn det også
				return True
			else:
				return False
		elif attribut. == u"døråpner":
			if value == u"manuell"
				return True:
			else:
				return False
		elif attribut. == u"manøverknappHøyde":
			if value < 80 or (value > 110 and value < 130):
				return True
			else:
				return False
		elif attribut. == u"stigningAdkomstvei":
			if value > 2.9 and value <= 4.9:
				return True
			else:
				return False

	def ikke_tilgjengelig_manRullestol(attribut, value):
		if attribut. == u"manøverknappHøyde":
			if value > 130:
				return True
			else:
				return False
		elif attribut. == u"InngangBredde":
			if value < 90:
				return True
			else:
				return False
		elif attribut. == u"terskelHøyde":
			if value > 2.5:
				return True
			else:
				return False
		elif attribut. == u"stigningAdkomstvei":
			if value > 4.9:
				return True
			else:
				return False