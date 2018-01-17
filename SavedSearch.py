class SavedSearch(object):

    def __init__(self, search_name, layer, lineEdit_seach, tabIndex_main, tabIndex_friluft, tabIndex_tettsted):
    	self.search_name = search_name
    	self.layer = layer
        self.lineEdit_seach = lineEdit_seach
        self.tabIndex_main = tabIndex_main
        self.tabIndex_friluft = tabIndex_friluft
        self.tabIndex_tettsted = tabIndex_tettsted
        self.attributes = {}


    def add_attribute(self, attribute, current_index, current_lineText):
    	self.attributes[attribute] = [current_index, current_lineText]

    def get_attributes(self):
    	return self.attributes

