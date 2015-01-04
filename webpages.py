import web, app, math, json, time, copy
import photoEmbed

class DistLatLon(object):
	#Based on http://stackoverflow.com/a/1185413/4288232

	def __init__(self, latDeg, lonDeg):
		self.R = 6371.
		lat = math.radians(latDeg)
		lon = math.radians(lonDeg)
		self.x = self.R * math.cos(lat) * math.cos(lon)
		self.y = self.R * math.cos(lat) * math.sin(lon)
		self.z = self.R * math.sin(lat)

	def Dist(self, latDeg, lonDeg):
		lat = math.radians(latDeg)
		lon = math.radians(lonDeg)
		x2 = self.R * math.cos(lat) * math.cos(lon)
		y2 = self.R * math.cos(lat) * math.sin(lon)
		z2 = self.R * math.sin(lat)
		
		dist2 = math.pow(self.x - x2, 2.) + math.pow(self.y - y2, 2.) + math.pow(self.z - z2, 2.)
		if dist2 < 0.:
			return 0.
		return math.pow(dist2, 0.5)

def GetRecordsNear(db, lat, lon):
	latHWidth = 0.05
	lonHWidth = 0.1
	vrs = {}
	conds = []

	if lat is not None:
		conds.append("minLat>=$minLat AND maxLat<=$maxLat")
		vrs['minLat'] = lat-latHWidth
		vrs['maxLat'] = lat+latHWidth

	if lon is not None:
		conds.append("minLon>=$minLon AND maxLon<=$maxLon")
		vrs['minLon'] = lon-lonHWidth
		vrs['maxLon'] = lon+lonHWidth
	
	if len(conds) > 0:
		cond = " AND ".join(conds)
	else:
		cond = "1=1"

	results = db.select("pos", where=cond, vars=vrs, limit = 1000)
	sortableResults = []

	if lat is not None and lon is not None:
		calcDist = DistLatLon(lat, lon)
	else:
		calcDist = None

	for record in results:
		rowId = record["id"]
		
		vars2 = {"id": rowId}
		dataResults = db.select("data", where="id=$id", vars= vars2, limit = 100)
		dataResults = list(dataResults)
		if len(dataResults) == 0: continue
		record = dict(dataResults[0])
		if calcDist is not None:
			dist = calcDist.Dist(record["lat"], record["lon"])
		else:
			dist = None

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
		try:
			lat = float(webinput["lat"])
		except:
			lat = None
		try:
			lon = float(webinput["lon"])
		except:
			lon = None
		records = GetRecordsNear(db, lat, lon)
		
		return app.RenderTemplate("nearby.html", records=records[:100], 
			webinput=webinput, lat=lat, lon=lon)

class Record(object):
	def __init__(self, db, rowId):
		self.rowId = rowId
		self.extendedFields = ["description", "flickr"]

		vars2 = {"id": rowId}
		dataResults = db.select("data", where="id=$id", vars=vars2, limit = 1)
		dataResults = list(dataResults)
		self.current = dict(dataResults[0])

		extendedData = json.loads(self.current["extended"])
		for key in extendedData:
			self.current[key] = extendedData[key]
		del self.current["extended"]

		if self.current["edits"] is not None:
			self.edits = json.loads(self.current["edits"])
		else:
			self.edits = []
		del self.current["edits"]

		#Combine edits into current record
		self.editLog = copy.deepcopy(self.edits)
		for (editMeta, editData), log in zip(self.edits, self.editLog):
			for key in editData:
				if key in self.current:
					old = self.current[key]
				else:
					old = None
				self.current[key] = editData[key]
				log[1][key] = (editData[key], old)

		#Separate special fixed fields into separate store
		self.fixedData = {}
		fixedFields = ["lat", "lon", "id", "source"]
		for fixedField in fixedFields:
			if fixedField in self.current:
				self.fixedData[fixedField] = self.current[fixedField]
				del self.current[fixedField]

		#If necessary, add extended fields
		for field in self.extendedFields:
			if field not in self.current:
				self.current[field] = ""
		
	def Update(self, db, updateTime, user, newValues):
		#See what has been changed
		changedData = {}
		for key in newValues:
			if newValues[key] != self.current[key]:
				changedData[key] = newValues[key]

		#Return if nothing changed
		if len(changedData) == 0:
			return

		vars2 = {"id": self.rowId}
		self.edits.append(((user, updateTime), changedData))
		changedFieldsJosn = json.dumps(self.edits)
		db.update("data", where="id=$id", vars=vars2, edits=changedFieldsJosn)

class RecordPage:
	def GET(self):
		return self.Render()

	def POST(self):
		db = web.ctx.db
		webinput = web.input()
		rowId = int(webinput["record"])
		record = Record(db, rowId)

		formData = {}		
		for key in webinput:
			if key[:6] != "field_": continue
			keyName = key[6:]
			formData[keyName] = webinput[key]

		record.Update(db, time.time(), "TimSC", formData)

		return self.Render()

	def Render(self):
		db = web.ctx.db
		webinput = web.input()
		rowId = int(webinput["record"])

		record = Record(db, rowId)

		flickrIds = record.current["flickr"].split(",")
		photos = []
		flickrHandle = photoEmbed.GetFlickrHandle()

		for flickrPhotoId in flickrIds:
			photoInfo = photoEmbed.FlickrPhotoInfo(flickrHandle, flickrPhotoId)
			if int(photoInfo.usageCanShare) != 1: continue
			photoSizes = photoEmbed.FlickrPhotoSizes(flickrHandle, flickrPhotoId)

			photos.append({'link':'https://www.flickr.com/photos/{0}/{1}'.format(photoInfo.ownerRealName, flickrPhotoId),
				'text':'{0} by {1}, on Flickr'.format(photoInfo.title, photoInfo.ownerRealName),
				'url': photoSizes.photoByWidth[150]["source"],
				'alt':'Cardwells Keep, Guildford',
				'height': 150,
				'width': 150
				})

		return app.RenderTemplate("record.html", record=record, webinput=webinput, photos=photos)

class SearchNear:
	def GET(self):
		db = web.ctx.db
		webinput = web.input()

		lat = 53.
		lon = -1.2
		if "lat" in webinput:
			try:
				lat = float(webinput["lat"])
			except:
				pass
		if "lon" in webinput:
			try:
				lon = float(webinput["lon"])
			except:
				pass

		return app.RenderTemplate("searchnear.html", webinput=webinput, lat=lat, lon=lon)

