import web, app, math, json, time, copy, gpxutils, StringIO
import photoEmbed, wikiEmbed
from xml.sax.saxutils import escape, unescape
import urllib2

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

class FrontPage(object):
	def GET(self):
		db = web.ctx.db
		webinput = web.input()
		
		return "Front page"

class Nearby(object):
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
			webinput=webinput, lat=lat, lon=lon, session = web.session)

class NearbyGpx(object):
	def GET(self):
		db = web.ctx.db
		webinput = web.input()
		buff = StringIO.StringIO()
		gw = gpxutils.GpxWriter(buff)

		try:
			lat = float(webinput["lat"])
		except:
			lat = None
		try:
			lon = float(webinput["lon"])
		except:
			lon = None
		records = GetRecordsNear(db, lat, lon)

		vowels = ('a', 'e', 'i', 'o', 'u')		


		for record in records[:100]:
			devwl = ''.join([l for l in record["name"] if l not in vowels]);

			gw.Waypoint(record["lat"], record["lon"], devwl)

		del gw

		web.header('Content-Type', 'application/gpx+xml')
		web.header('Content-Disposition', 'attachment; filename="nearby.gpx"')

		return buff.getvalue()

class Record(object):
	def __init__(self, db, rowId):
		self.rowId = rowId
		self.extendedFields = ["description", "flickr", "wikipedia"]

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

def SplitTextByParagraph(text, targetNumChars):
	textPar = text.split("\n")
	cumul = 0
	cumulLi = []
	for par in textPar:
		cumul += len(par)
		cumulLi.append(cumul)

	bestSc = None
	best = []
	for i, l in enumerate(cumulLi):
		err = abs(targetNumChars - l)
		if bestSc is None or err < bestSc:
			best = "\n".join(textPar[:i+1])
			bestSc = err

	return best

class FlickrPlugin(object):
	def __init__(self):
		pass

	def PrepareData(self, record):

		#Get stored flickr IDs
		flickrIds = set(record.current["flickr"].split(","))
		photos = []
		flickrHandle = photoEmbed.GetFlickrHandle()

		#Search using flickr API for tags that match this ID
		tag = u"england_listed_building:entry={0}".format(record.current["ListEntry"])
		flickrSearch = photoEmbed.FlickrSearch(flickrHandle, tag)
		for p in flickrSearch.photos[:25]: #Limit to 25 photos
			flickrIds.add(p["id"])
		
		#Process flickr IDs into a gallery
		for flickrPhotoId in flickrIds:
			idStrip = flickrPhotoId.strip()

			if not unicode(idStrip).isnumeric():
				continue

			if 1:
			#try:
				idClean = int(idStrip)
				photoInfo = photoEmbed.FlickrPhotoInfo(flickrHandle, idClean)
				if int(photoInfo.usageCanShare) != 1: continue
				photoSizes = photoEmbed.FlickrPhotoSizes(flickrHandle, idClean)
			#except Exception as err:
				#raise err			
			#	continue

			userPth = photoInfo.ownerUserName
			if photoInfo.ownerPathAlias is not None:
				userPth = photoInfo.ownerPathAlias

			displayName = photoInfo.ownerUserName
			if photoInfo.ownerRealName is not None and len(photoInfo.ownerRealName) > 0:
				displayName = photoInfo.ownerRealName

			photos.append({'link':u'https://www.flickr.com/photos/{0}/{1}'.format(urllib2.quote(userPth), idClean),
				'text':u'{0} by {1}, on Flickr'.format(photoInfo.title, displayName),
				'url': photoSizes.photoByWidth[150]["source"],
				'alt':photoInfo.title,
				'height': 150,
				'width': 150
				})

		return {'photos': photos}

	def ProcessWebPost(self, db, webinput, record):
		
		if webinput["action"] == "Associate with record":

			photoIds = []
			for key in webinput:
				prefix = key[:16]
				if prefix != "checkbox-flickr-": continue
				photoId = int(key[16:])
				photoIds.append(photoId)

			splitFlickrIds = record.current["flickr"].split(",")
			currentFlickrIds = set()
			for photoId in splitFlickrIds:
				ps = unicode(photoId.strip())
				if not ps.isnumeric(): continue
				p = int(ps)
				currentFlickrIds.add(p)

			for photoId in photoIds:
				currentFlickrIds.add(photoId)

			currentFlickrIdsSortable = list(currentFlickrIds)
			currentFlickrIdsSortable.sort()

			currentFlickrStrIds = map(str, currentFlickrIdsSortable)

			formData={'flickr': ",".join(currentFlickrStrIds)}
			record.Update(db, time.time(), web.ctx.session.username, formData)

class RecordPage(object):
	def GET(self):
		return self.Render()

	def POST(self):
		db = web.ctx.db
		webinput = web.input()
		rowId = int(webinput["record"])

		if web.ctx.session.get("username", None) == None:
			return self.Render("Log in first")

		record = Record(db, rowId)

		if webinput["action"] == "Update record":
			formData = {}		
			for key in webinput:
				if key[:6] != "field_": continue
				keyName = key[6:]
				formData[keyName] = webinput[key]
			
			record.Update(db, time.time(), web.ctx.session.username, formData)

		flickrPlugin = FlickrPlugin()
		results = flickrPlugin.ProcessWebPost(db, webinput, record)

		if webinput["action"] == "Associate article with record":

			formData={'wikipedia': webinput["article"]}
			record.Update(db, time.time(), web.ctx.session.username, formData)

		return self.Render()

	def Render(self, actionMessage = None):
		db = web.ctx.db
		webinput = web.input()
		rowId = int(webinput["record"])

		record = Record(db, rowId)
		collectedPluginResults = {}

		flickrPlugin = FlickrPlugin()
		pluginResults = flickrPlugin.PrepareData(record)
		collectedPluginResults.update(pluginResults)

		#Process wikipedia link into embeded text
		wikipediaArticle = record.current["wikipedia"]
		wikis = []

		if wikipediaArticle is not None and len(wikipediaArticle) > 0:
			article = wikiEmbed.MediawikiArticle(wikipediaArticle)
			wikiEntry = {}
			textExtract = SplitTextByParagraph(article.text, 1000)
			wikiEntry["text"] = escape(textExtract).replace("\n", "<br/>")
			wikiEntry["url"] = u"https://en.wikipedia.org/wiki/{0}".format(urllib2.quote(wikipediaArticle))
			wikiEntry["credit"] = "Wikipedia"
			wikiEntry["article"] = wikipediaArticle

			wikis.append(wikiEntry)

		return app.RenderTemplate("record.html", record=record, 
			webinput=webinput, wikis=wikis, 
			actionMessage = actionMessage,
			session = web.ctx.session, **collectedPluginResults)

class SearchNear(object):
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

		return app.RenderTemplate("searchnear.html", webinput=webinput, lat=lat, lon=lon, session = web.ctx.session)

class SearchFlickr(object):
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

		if "limitarea" not in webinput or webinput["limitarea"] != "on":
			lat = None
			lon = None
			radius = None

		flickrHandle = photoEmbed.GetFlickrHandle()
		photoSearch = photoEmbed.FlickrSearch(flickrHandle, text=webinput["text"], lat=lat, lon=lon, radius=webinput["radius"])

		photos = []
		for photo in photoSearch.photos:
			photoId = int(photo["id"])

			photoInfo = photoEmbed.FlickrPhotoInfo(flickrHandle, photoId)
			if int(photoInfo.usageCanShare) != 1: continue
			photoSizes = photoEmbed.FlickrPhotoSizes(flickrHandle, photoId)

			userPth = photoInfo.ownerUserName
			if photoInfo.ownerPathAlias is not None:
				userPth = photoInfo.ownerPathAlias

			displayName = photoInfo.ownerUserName
			if photoInfo.ownerRealName is not None and len(photoInfo.ownerRealName) > 0:
				displayName = photoInfo.ownerRealName

			photos.append({'link':u'https://www.flickr.com/photos/{0}/{1}'.format(urllib2.quote(userPth), photoId),
				'text':u'{0} by {1}, on Flickr'.format(photoInfo.title, displayName),
				'url': photoSizes.photoByWidth[150]["source"],
				'alt': photoInfo.title,
				'height': 150,
				'width': 150,
				'description': photoInfo.description,
				'id': photoId,
				})

			if len(photos) >= 25: break

		return app.RenderTemplate("searchflickr.html", webinput=webinput, lat=lat, lon=lon, session = web.ctx.session, photos=photos)


class SearchWikipedia(object):
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

		photos = []

		searchResult = wikiEmbed.MediawikiSearch(lat, lon, webinput["radius"])
		result = []
		for r in searchResult.results:
			r["url"] = u"https://en.wikipedia.org/wiki/{0}".format(urllib2.quote(r["title"]))
			result.append(r)

		return app.RenderTemplate("searchwikipedia.html", webinput=webinput, lat=lat, lon=lon, session = web.ctx.session, photos=photos, result=result)

