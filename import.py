#ogr2ogr -f KML output.kml input.shp

import sqlite3, bz2
import xml.parsers.expat

class ParseKml(object):
	def __init__(self):
		self.depth = 0

	def StartEl(self, name, attrs):
		print self.depth, name
		self.depth += 1

	def EndEl(self, name):

		self.depth -= 1

	def CharData(self, data):
		pass

	def ParseFile(self, ha):
		parser = xml.parsers.expat.ParserCreate()

		parser.StartElementHandler = self.StartEl
		parser.EndElementHandler = self.EndEl
		#parser.CharacterDataHandler = self.CharData

		parser.ParseFile(ha)


if __name__=="__main__":
	conn = sqlite3.connect('auxgis.db')

	inFi = bz2.BZ2File("LB.kml.bz2", "r")

	ep = ParseKml()
	ep.ParseFile(inFi)


