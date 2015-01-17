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

import sqlite3, bz2, json, importScheduledMonuments
import xml.parsers.expat

def TitleCase(txt):
	txtSpl = txt.split(" ")
	txtSpl = [tmp.capitalize() for tmp in txtSpl]
	return " ".join(txtSpl)

class Db(object):
	def __init__(self):
		self.conn = sqlite3.connect('auxgis.db')
		self.cursor = self.conn.cursor()
		self.source = "ListedBuildings"

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

		extendedData["lat"] = repPoint[1]
		extendedData["lon"] = repPoint[0]
		extendedJson = json.dumps(extendedData)

		sql = "INSERT INTO data (name, source, lat, lon, extended) VALUES (?,?,?,?,?);"
		self.cursor.execute(sql, (placeName, self.source, repPoint[1], repPoint[0], extendedJson))

		lid = self.cursor.lastrowid
		sql = "INSERT INTO pos (id, minLat, maxLat, minLon, maxLon) VALUES (?,?,?,?,?);"
		self.cursor.execute(sql, (lid, repPoint[1], repPoint[1], repPoint[0], repPoint[0]))



if __name__=="__main__":
	

	inFi = bz2.BZ2File("LB.kml.bz2", "r")
	db = Db()

	ep = importScheduledMonuments.ParseKml()
	ep.db = db
	ep.ParseFile(inFi)

	ep.db = None
	del db

