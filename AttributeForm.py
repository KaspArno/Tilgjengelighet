import operator

class AttributeForm(object):
    """Saves attributes and assosiated gui widgets"""


    def __init__(self, attribute, comboBox=None, lineEdit=None, comboBoxText=None, label=None):
        """Constructor

        :param attribute: The name of the attribute in layer
        :type attribute: str

        :param comboBox: The associated comboBox
        :type comboBox: QComboBox

        :param lineEdit: The associated lineEdit
        :type lineEdit: QLineEdit

        :param comboBoxText: Alternative text for combobox
        :type comboBoxText: dict
        """

        self.attribute = attribute
        self.comboBox = comboBox
        self.lineEdit = lineEdit
        self.label = label
        self.alt_comboboxText = comboBoxText

        self.opperatorDict = {u'=' : 'PropertyIsEqualTo', u'<' : 'PropertyIsLessThan', u'>' : 'PropertyIsGreaterThan', u'<=' : 'PropertyIsLessThanOrEqualTo', u'>=' : 'PropertyIsGreaterThanOrEqualTo'}

        #attribute.opperator(), attribute.valueReference(), attribute.value()

    def opperator(self):
        """
        :returns: the opperator for attriubutt qury
        :rtype: QString, None
        """

        if self.comboBox is not None:
            if self.comboBox.currentText() in self.opperatorDict:
                return self.opperatorDict[self.comboBox.currentText()]
            else:
                return self.opperatorDict[u'=']
        else:
            return self.opperatorDict[u'=']

    def valueReference(self):
        """Returns the objekt attribute
        
        :returns: name of object attribute in database
        :rtype: str
        """

        return self.attribute

    def value(self):
        """returns the value constraint, if alternative combobox is set, return that value, if lineedit, ruturn value freom line edit, else return from combobox
        
        :returns: the value constraint
        :rtype: str
        """

        if self.alt_comboboxText is not None:
            return self.alt_comboboxText[self.comboBox.currentText()]
        elif self.lineEdit is not None:
            return self.lineEdit.text()
        elif self.comboBox is not None:
            return self.comboBox.currentText()
        else:
            return None


    def setComboBox(self, comboBox):
        """Assigning comboBox

        :param comboBox: combobox assisiated to attribute
        :type comboBox: QComboBox
        """

        self.comboBox = comboBox

    def setLineEdit(self, lineEdit):
        """Assigning lineEdit

        :param lineEdit: Linedit assisiated to attribute
        :type lineEdit: QLineEdit
        """

        self.lineEdit = lineEdit

    def getComboBox(self):
        """ Returns the assosiated combobox widget

        :returns: returns the associated comboBox
        :rtype: QComboBox
        """

        return self.comboBox

    def getLineEdit(self):
        """Returns the assosiated lineEdit widget if any

        :returns: returns the associated lineEdit
        :rtype: QLineEdit
        """

        return self.lineEdit

    def getLabel(self):
        """Returns the assisiated label widget if any
        :returns: returns the associated label
        :rtype: QLabel
        """

        return self.label


    def getAttribute(self):
        """Returns the assosiated attriubte name

        :returns: returns the associated attribute name
        :rtype: str
        """

        return self.attribute

    def getComboBoxCurrentText(self):
        """Returns the assosoated combobox text

        :returns: returns the associated comboBox text, return None if no combobox is availeble
        :rtype: QString
        """

        if self.comboBox is not None:
            if self.alt_comboboxText: #If AttributForm has alternative text, return alternative text
                return self.alt_comboboxText[self.comboBox.currentText()]
            return self.comboBox.currentText()
        return None

    def getLineEditText(self):
        """Returns the lineEdit text

        :returns: returns the lineEdit text, return None if no lineEdit is availeble
        :rtype: QString
        """

        if self.lineEdit is not None:
            return self.lineEdit.text()
        return None

    def setLineEditText(self, string):
        """Sett text in AttributeForm lineEdit

        :param string: String to set in lineEdit
        :type string: str
        """

        if self.lineEdit is not None:
            self.lineEdit.setText(string)

    def valudeValid(self):
        """checks if the attribute is valid and search ready

        :returns: True if attrivute is valid, false if not
        :rtype: boolean
        """

        if self.lineEdit is not None:
            if self.opperator() != 'PropertyIsEqualTo' and len(self.getLineEditText()) == 0: #opperator chosen, but no value
                print("IsValid 1")
                return False
            elif self.opperator() == 'PropertyIsEqualTo' and len(self.getLineEditText()) > 0: #value chosen, bu no opperator
                print("IsValid 2")
                return False
            elif len(self.getLineEditText()) > 0:
                print("len: {}".format(len(self.getLineEditText())))
                print("IsValid 3")
                return self.is_number(self.getLineEditText()) #Valu not a number
        else:
            print("attribute is valid")
            return True


    def reset(self):
        """Resets form to defult"""

        if self.comboBox:
            self.comboBox.setCurrentIndex(0)
        if self.lineEdit:
            self.lineEdit.setText("")

    def is_number(self, s):
        """Sett text in AttributeForm lineEdit

        :param s: string to be change for being a number
        :type s: str
        :returns: tru if s is number, false if s in not a number
        :rtype: boolean
        """

        print("s: {}".format(s))
        print("type: {}".format(type(s)))
        try:
            float(s)
            return True
        except ValueError:
            return False