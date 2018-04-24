class KravVei(Krav):

    def __init__(self):
        super(Krav, self).__init__()





    def generisk(self, value, notAcceceble=None, acceceble=None, relate_notAccec=None, relate_acces=None):
        if self.is_float(value):
            value = float(value)
        elif self.is_int(value):
            value = int(value)

        if value is None or value == "-":
            return "ikkeVurdert"
        elif notAcceceble
            if relate_notAccec(value, notAcceceble):
                return "ikkeTilgjengelig"
        elif acceceble
            if relate_acces(value, acceceble):
                return "Tilgjengelig"
        else:
            return "vanskeligTilgjengelig"


    def bredde(self, value):
        if value is None or value == "-":
            return "ikkeVurdert"
        elif int(value) < 130:
            return "ikkeTilgjengelig"
        elif int(value) >= 180:
            return "Tilgjengelig"
        else:
            return "vanskeligTilgjengelig"


    def stigning(self, value):
        if value is None or value == "-":
            return "ikkeVurdert"
        elif float(value) > 4.9:
            return "ikkeTilgjengelig"
        elif float(value) <= 2.9:
            return "Tilgjengelig"
        else:
            return "vanskeligTilgjengelig"

    def treverfall(self, value):

