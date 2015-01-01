import web, app, math

class DistLatLon(object):
	#Based on http://stackoverflow.com/a/1185413/4288232

	def __init__(self, latDeg, lonDeg):
		R = 6371.
		lat = math.radians(latDeg)
		lon = math.radians(lonDeg)
		self.x = R * math.cos(lat) * math.cos(lon)
		self.y = R * math.cos(lat) * math.sin(lon)
		self.z = R * math.sin(lat)

	def Dist(self, latDeg, lonDeg):
		R = 6371.
		lat = math.radians(latDeg)
		lon = math.radians(lonDeg)
		x2 = R * math.cos(lat) * math.cos(lon)
		y2 = R * math.cos(lat) * math.sin(lon)
		z2 = R * math.sin(lat)
		
		dist2 = math.pow(self.x - x2, 2.) + math.pow(self.y - y2, 2.) + math.pow(self.z - z2, 2.)
		if dist2 < 0.:
			return 0.
		return math.pow(dist2, 0.5)

def GetRecordsNear(db, lat, lon):
	latHWidth = 0.05
	lonHWidth = 0.1

	vrs = {'minLat':lat-latHWidth, 'maxLat':lat+latHWidth, 'minLon':lon-lonHWidth, 'maxLon': lon+lonHWidth}
	cond = "minLat>=$minLat AND maxLat<=$maxLat AND minLon>=$minLon AND maxLon<=$maxLon"
	#cond = "1=1"
	results = db.select("pos", where=cond, vars=vrs, limit = 1000)
	sortableResults = []

	calcDist = DistLatLon(lat, lon)

	for record in results:
		rowId = record["id"]
		
		vars2 = {"id": rowId}
		dataResults = db.select("data", where="id=$id", vars= vars2, limit = 100)
		dataResults = list(dataResults)
		if len(dataResults) == 0: continue
		record = dict(dataResults[0])
		dist = calcDist.Dist(record["lat"], record["lon"])
		record["dist"] = dist

		sortableResults.append((dist, record))

	sortableResults.sort()
	records = [tmp[1] for tmp in sortableResults]
	return records

class FrontPage:
	def GET(self):
		db = web.ctx.db
		webinput = web.input()
		
		return "Front page"

class Nearby:
	def GET(self):
		db = web.ctx.db
		webinput = web.input()
		lat = float(webinput["lat"])
		lon = float(webinput["lon"])
		records = GetRecordsNear(db, lat, lon)
		
		return app.RenderTemplate("nearby.html", records=records, webinput=webinput)

class Record:
	def GET(self):
		db = web.ctx.db
		webinput = web.input()
		rowId = float(webinput["record"])

		vars2 = {"id": rowId}
		dataResults = db.select("data", where="id=$id", vars=vars2, limit = 1)
		dataResults = list(dataResults)
		record = dict(dataResults[0])

		return app.RenderTemplate("record.html", record=record, webinput=webinput)


