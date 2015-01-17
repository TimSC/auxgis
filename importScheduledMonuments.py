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

import sqlite3, bz2, json
import xml.parsers.expat
from shapely.geometry import Polygon, LineString, LinearRing, Point, MultiPolygon, MultiPoint
import shapely.wkt

def TitleCase(txt):
	txtSpl = txt.split(" ")
	txtSpl = [tmp.capitalize() for tmp in txtSpl]
	return " ".join(txtSpl)

class Db(object):
	def __init__(self):
		self.conn = sqlite3.connect('auxgis.db')
		self.cursor = self.conn.cursor()
		self.source = "ScheduledMonuments"

	def __del__(self):
		self.conn.commit()

	def HandlePlacemark(self, placeName, shape, extendedData):
		#print placeName, shape
		#print extendedData
		
		#Remove unnecessary info
		del extendedData["Easting"]
		del extendedData["Northing"]
		del extendedData["NGR"]

		repPoint = None
		if shape is not None:
			tmp = shape.representative_point()
			repPoint = tuple(tmp.coords[0])

#		print placeName
#		print repPoint
#		print shapely.wkt.dumps(shape)

		extendedData["lat"] = repPoint[1]
		extendedData["lon"] = repPoint[0]
		extendedJson = json.dumps(extendedData)

		sql = "INSERT INTO data (name, source, lat, lon, extended) VALUES (?,?,?,?,?);"
		self.cursor.execute(sql, (placeName, self.source, repPoint[1], repPoint[0], extendedJson))

		lid = self.cursor.lastrowid
		sql = "INSERT INTO pos (id, minLat, maxLat, minLon, maxLon) VALUES (?,?,?,?,?);"
		self.cursor.execute(sql, (lid, repPoint[1], repPoint[1], repPoint[0], repPoint[0]))

class ParseKml(object):
	def __init__(self):
		self.depth = 0
		self.count = 0
		self.dataBuffer = []
		self.extendedData = {}
		self.lastAttr = None
		self.placeName = None
		self.shapePoints = []
		self.shapeLineStrings = []
		self.shapeLinearRings = []
		self.shapeOuterPolys = []
		self.shapeInnerPolys = []
		self.shapeType = None
		self.shapeSubType = None
		self.db = None
		self.kmlGeoms = ["Point","LineString","LinearRing",
			"Polygon","MultiGeometry","Model",
			"gx:Track"]
		self.geomDepth = 0

	def StartEl(self, name, attrs):
		#print self.depth, name, attrs
		if name in ["SimpleData", "coordinates", "name"]:
			self.dataBuffer = []

		if name == "ExtendedData":
			self.extendedData = {}

		if name in self.kmlGeoms:
			if self.geomDepth == 0:
				self.shapeType = name
			self.geomDepth += 1

		if name in ["outerBoundaryIs", "innerBoundaryIs"]:
			self.shapeSubType = name

		if name == "Placemark":
			self.count += 1
			if self.count % 1000 == 0:
				print self.count

		self.depth += 1
		self.lastAttr = attrs

	def EndEl(self, name):
		if name == "SimpleData":
			txt = "".join(self.dataBuffer)
			self.dataBuffer = []
			self.extendedData[self.lastAttr["name"]] = txt

		if name == "coordinates":
			txt = "".join(self.dataBuffer)

			txtSp1 = txt.split(" ")
			ptList = []
			for pttxt in txtSp1:

				txtSp2 = pttxt.split(",")
				nums = tuple(map(float, txtSp2))
				ptList.append(nums)

			if self.shapeType == "Point":
				self.shapePoints.extend(ptList)
			if self.shapeType == "LineString":
				self.shapeLineStrings.append(ptList)
			if self.shapeType == "LinearRing":
				self.shapeLinearRings.append(ptList)
			if self.shapeSubType == "outerBoundaryIs":
				self.shapeOuterPolys.append(ptList)
			if self.shapeSubType == "innerBoundaryIs":
				self.shapeInnerPolys.append(ptList)

			self.dataBuffer = []

		if name == "name":
			txt = "".join(self.dataBuffer)
			self.placeName = txt
			self.dataBuffer = []

		if name == "Placemark":
			pn = None
			if self.placeName is not None:
				pn = TitleCase(self.placeName)
				pn = pn.replace("\n", "")
				pn = pn.replace("\r", "")

			shape = None
	
			if self.shapeType in ["Polygon"]:
				#print self.shapeType, len(self.shapeOuterPolys), len(self.shapeInnerPolys)
				shape = Polygon(self.shapeOuterPolys[0], self.shapeInnerPolys)

			if self.shapeType in ["MultiGeometry"]:
				outer = map(Polygon, self.shapeOuterPolys)
				inner = map(Polygon, self.shapeInnerPolys)

				poly = []
				for o in outer:
					ihit = []
					for i in inner:
						if o.intersects(i):
							ihit.append(i.exterior.coords)
					poly.append(Polygon(o.exterior.coords, ihit))
				shape = MultiPolygon(poly)

			if self.shapeType == "LineString":
				shape = LineString(self.shapeLineStrings[0])

			if self.shapeType == "LinearRing":
				shape = LinearRing(self.shapeLinearRings[0])

			if self.shapeType == "Point":
				if len(self.shapePoints) == 1:
					shape = Point(self.shapePoints[0])
				else:
					shape = MultiPoint(self.shapePoints)

			if shape is None:
				raise RuntimeError("Unknown shape type: "+str(self.shapeType))

			#print self.placeName, self.shape, self.extendedData
			self.db.HandlePlacemark(pn, shape, self.extendedData)
			self.extendedData = {}
			self.placeName = None
			self.shapePoints = []
			self.shapeOuterPolys = []
			self.shapeInnerPolys = []
			self.shapeLineStrings = []
			self.shapeLinearRings = []
			self.shapeType = None

		if name in self.kmlGeoms:
			self.geomDepth -= 1

		if name in ["outerBoundaryIs", "innerBoundaryIs"]:
			self.shapeSubType = None

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
	

	inFi = bz2.BZ2File("SM.kml.bz2", "r")
	db = Db()

	ep = ParseKml()
	ep.db = db
	ep.ParseFile(inFi)

	ep.db = None
	del db

