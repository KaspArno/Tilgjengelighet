import operator

class AttributeForm(object):
	"""Saves attributes and assosiated gui widgets"""


	def __init__(self, attribute, comboBox=None, lineEdit=None, comboBoxText=None):
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
		self.alt_comboboxText = comboBoxText

		self.opperatorDict = {u'=' : 'PropertyIsEqualTo', u'<' : 'PropertyIsLessThan', u'>' : 'PropertyIsGreaterThan', u'<=' : 'PropertyIsLessThanOrEqualTo', u'>=' : 'PropertyIsGreaterThanOrEqualTo'}

		#attribute.opperator(), attribute.valueReference(), attribute.value()

	def opperator(self):
		if self.comboBox is not None:
			if self.comboBox.currentText() in self.opperatorDict:
				return self.opperatorDict[self.comboBox.currentText()]
			else:
				return self.opperatorDict[u'=']
		else:
			return None

	def valueReference(self):
		return self.attribute

	def value(self):
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
		:param comboNox:
		:type comboBox: QComboBox
		"""
		self.comboBox = comboBox

	def setLineEdit(self, lineEdit):
		"""Assigning lineEdit
		:param lineEdit:
		:type lineEdit: QLineEdit
		"""
		self.lineEdit = lineEdit

	def getComboBox(self):
		""":returns: returns the associated comboBox
        :rtype: QComboBox
        """
		return self.comboBox

	def getLineEdit(self):
		""":returns: returns the associated lineEdit
        :rtype: QLineEdit
        """
		return self.lineEdit

	def getAttribute(self):
		""":returns: returns the associated attribute name
        :rtype: str
        """
		return self.attribute

	def getComboBoxCurrentText(self):
		""":returns: returns the associated comboBox text, return None if no combobox is availeble
        :rtype: QString, None
        """
		if self.comboBox is not None:
			if self.alt_comboboxText: #If AttributForm has alternative text, return alternative text
				return self.alt_comboboxText[self.comboBox.currentText()]
			return self.comboBox.currentText()
		return None

	def getLineEditText(self):
		""":returns: returns the lineEdit comboBox text, return None if no lineEdit is availeble
        :rtype: QString
        """
		if self.lineEdit is not None:
			return self.lineEdit.text()
		return None

	def setLineEditText(self, string):
		"""Sett text in AttributeForm lineEdit
		:param string:
		:type str:
		"""
		if self.lineEdit is not None:
			self.lineEdit.setText(string)

	def reset(self):
		"""Resets form to defult"""
		if self.comboBox:
			self.comboBox.setCurrentIndex(0)
		if self.lineEdit:
			self.lineEdit.setText("")