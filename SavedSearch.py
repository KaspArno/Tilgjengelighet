class SavedSearch(object):

    def __init__(self, search_name, layer, tabIndex_main, tabIndex_friluft, tabIndex_tettsted):
        """Constructor.

        :param search_name: The name of the search made (layer name)
        :param layer: The layer or result from search
        :param tabIndex_main: Main tab index at search
        :param tabIndex_friluft: friluft tab index at search
        :param tabIndex_tettsted: tettsted tab index at search

        :type searchname: str
        :type layer: QgsVectorLayer
        :type tabIndex_main: int
        :type tabIndex_friluft: int
        :type tabIndex_tettsted: int
        """

        self.search_name = search_name #Name of layer
        self.layer = layer #Layer
        #self.lineEdit_seach = lineEdit_seach
        self.tabIndex_main = tabIndex_main #Main tab index
        self.tabIndex_friluft = tabIndex_friluft #Friluft tab index
        self.tabIndex_tettsted = tabIndex_tettsted #Tettsted tab index
        self.attributes = {} #attributes used in search (combobx index and lineEdit text stored in list as dictionary valu, AttributeForm is stored as Key)


    def add_attribute(self, attribute, current_index, current_lineText):
        """Add attribute with current index for combobx and current text for lineText Attributes are stored in dictionarys as key, while value is list of combobox indes and lintEdtid text
        :param attribute: one attribute from filter interface
        :param current_index: index of combobx at search
        :param current_lineText: text of lineEdit at search

        :type attribute: AttributeForm
        :type current_intex: int
        :type current_lineText: str
        """

        self.attributes[attribute] = [current_index, current_lineText]


    def get_attributes(self):
        """Returns dictionary of attributes"""
        return self.attributes

