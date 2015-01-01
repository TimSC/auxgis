#ogr2ogr -f KML output.kml input.shp

#0 kml
#1 Document
#2 Folder
#3 name
#3 Placemark
#4 name
#4 ExtendedData
#5 SchemaData
#6 SimpleData

import sqlite3, bz2
import xml.parsers.expat

class Db(object):
	def __init__(self):
		self.conn = sqlite3.connect('auxgis.db')
		self.cursor = self.conn.cursor()

	def HandlePlacemark(self, placeName, shape, extendedData):
		print placeName

class ParseKml(object):
	def __init__(self):
		self.depth = 0
		self.count = 0
		self.dataBuffer = []
		self.extendedData = {}
		self.lastAttr = None
		self.placeName = None
		self.shape = None
		self.db = Db()

	def StartEl(self, name, attrs):
		#print self.depth, name, attrs
		if name in ["SimpleData", "coordinates", "name"]:
			self.dataBuffer = []

		if name == "ExtendedData":
			self.extendedData = {}

		self.depth += 1
		self.count += 1
		self.lastAttr = attrs
		#if self.count >= 100:
		#	exit(0)

	def EndEl(self, name):
		if name == "SimpleData":
			txt = "".join(self.dataBuffer)
			self.dataBuffer = []
			self.extendedData[self.lastAttr["name"]] = txt

		if name == "coordinates":
			txt = "".join(self.dataBuffer)
			txtSp = txt.split(",")
			nums = map(float, txtSp)
			if len(nums) == 2:
				nums = [(nums[1], nums[0])]

			self.shape = nums
			self.dataBuffer = []

		if name == "name":
			txt = "".join(self.dataBuffer)
			self.placeName = txt
			self.dataBuffer = []

		if name == "Placemark":
			#print self.placeName, self.shape, self.extendedData
			self.db.HandlePlacemark(self.placeName, self.shape, self.extendedData)
			self.extendedData = {}
			self.placeName = None
			self.shape = None

		self.depth -= 1

	def CharData(self, data):
		self.dataBuffer.append(data)
		#print data

	def ParseFile(self, ha):
		parser = xml.parsers.expat.ParserCreate()

		parser.StartElementHandler = self.StartEl
		parser.EndElementHandler = self.EndEl
		parser.CharacterDataHandler = self.CharData

		parser.ParseFile(ha)


if __name__=="__main__":
	

	inFi = bz2.BZ2File("LB.kml.bz2", "r")

	ep = ParseKml()
	ep.ParseFile(inFi)


