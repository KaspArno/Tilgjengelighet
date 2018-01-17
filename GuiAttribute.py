class GuiAttribute(object):

	def __init__(self, attribute, comboBox=None, lineEdit=None, comboBoxText=None):
		self.attribute = attribute
		self.comboBox = comboBox
		self.lineEdit = lineEdit
		self.alt_comboboxText = comboBoxText

	def setComboBox(self, comboBox):
		self.comboBox = comboBox

	def setLineEdit(self, lineEdit):
		self.lineEdit = lineEdit

	def getComboBox(self):
		return self.comboBox

	def getLineEdit(self):
		return self.lineEdit

	def getAttribute(self):
		return self.attribute

	def getComboBoxCurrentText(self):
		if self.comboBox is not None:
			if self.alt_comboboxText:
				return self.alt_comboboxText[self.comboBox.currentText()]
			return self.comboBox.currentText()
		return None

	def getLineEditText(self):
		if self.lineEdit is not None:
			return self.lineEdit.text()
		return None

	def setLineEditText(self, string):
		if self.lineEdit is not None:
			self.lineEdit.setText(string)

	def reset(self):
		if self.comboBox:
			self.comboBox.setCurrentIndex(0)
		if self.lineEdit:
			self.lineEdit.setText("")