class FeatureType(object):

	feature_type = ['app:TettstedHCparkering', 'app:TettstedInngangBygg', u'app:TettstedParkeringsomr\xe5de', 'app:TettstedVei']
	index = 0

	def next(self):
		self.index = self.index + 1

	def getFeatureType(self):
		if self.index < len(self.feature_type):
			return self.feature_type[self.index]
		return None