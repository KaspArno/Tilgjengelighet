class Krav(object):

    def __init__(self):
        rullestol = "ikkeVurdert"
        rullestol_el = "ikkeVurdert"
        synshemmed = "ikkeVurdert"

    def tilgjenglighet_rullestol(self):
    	return rullstol

    def tilgjenglighet_rullestol_el(self):
    	return rullestol_el

    def tilgjengelighet_synshemmed(self):
    	return synshemmed
    	

    def is_float(slef, value):
        try:
            float(value)
            return True
        except ValueError:
            return False

    def is_int(value):
        try:
            int(value)
            return True
        except ValueError:
            return False
