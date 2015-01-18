import web, app, math, json, time, copy, gpxutils, StringIO
import urllib2

def GetPlugins(source = None):
	
	return ['rawEdit',
			'photoEmbed', 
			'wikiEmbed', 			
			'mapEmbed',
			'editLog',
			'attribution',
		]

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

	recordMeta = {}
	for record in results:
		rowId = record["id"]
		
		#vars2 = {"id": rowId}
		#dataResults = db.select("data", where="id=$id", vars= vars2, limit = 100)
		#dataResults = list(dataResults)
		#if len(dataResults) == 0: continue
		#record = dict(dataResults[0])

		record = Record(db, rowId)

		if calcDist is not None:
			dist = calcDist.Dist(record.current["lat"], record.current["lon"])
		else:
			dist = None

		recordMeta[rowId] = {}
		recordMeta[rowId]["dist"] = dist
		sortableResults.append((dist, record))

	sortableResults.sort()
	records = [tmp[1] for tmp in sortableResults]

	for record in records:
		source = record.fixedData["source"]
		rowId = record.fixedData["id"]
		recordMeta[rowId]["marker"] = "red"

		if source == "ListedBuildings":
			recordMeta[rowId]["marker"] = "red"

		if source == "ScheduledMonuments":
			recordMeta[rowId]["marker"] = "blue"

	return records, recordMeta

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
		records, recordsMeta = GetRecordsNear(db, lat, lon)

		#Only consider a limited number of records
		records=records[:100]

		#Enumerate plugins
		plugins = GetPlugins()
		pluginInstances = []
		for plugin in plugins:
			baseModule = __import__("plugins."+plugin)
			pluginModule = getattr(baseModule, plugin)
			pluginInstance = pluginModule.Plugin()
			pluginInstances.append(pluginInstance)

		#Allow plugins to add extra info
		for record in records:
			rowId = record.fixedData["id"]
			recMeta = recordsMeta[rowId]
			recMeta["pluginData"] = []
			for instance in pluginInstances:
				instance.GetRecordSummary(record, recMeta)

		#Collect plugin data into a string
		for record in records:
			rowId = record.fixedData["id"]
			recMeta = recordsMeta[rowId]
			recMeta["pluginStr"] = " ".join(recMeta["pluginData"])

		return app.RenderTemplate("nearby.html", records=records, 
			recordsMeta = recordsMeta,
			webinput=webinput, lat=lat, lon=lon, session = web.ctx.session)

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
		records, recordsMeta = GetRecordsNear(db, lat, lon)

		vowels = ('a', 'e', 'i', 'o', 'u')		


		for record in records[:100]:
			devwl = ''.join([l for l in record.current["name"] if l not in vowels]);

			gw.Waypoint(record.current["lat"], record.current["lon"], devwl)

		del gw

		web.header('Content-Type', 'application/gpx+xml')
		web.header('Content-Disposition', 'attachment; filename="nearby.gpx"')

		return buff.getvalue()

class Record(object):
	def __init__(self, db, rowId, recentChangeTracker = None):
		self.rowId = rowId
		self.recentChangeTracker = recentChangeTracker
		self.extendedFields = ["description", "flickr", "wikipedia"]

		vars2 = {"id": rowId}
		dataResults = db.select("data", where="id=$id", vars=vars2, limit = 1)
		dataResults = list(dataResults)
		if len(dataResults) == 0:
			raise RuntimeError("Record not found")
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
		fixedFields = ["id", "source"]
		for fixedField in fixedFields:
			if fixedField in self.current:
				self.fixedData[fixedField] = self.current[fixedField]
				del self.current[fixedField]

		#If necessary, add extended fields
		for field in self.extendedFields:
			if field not in self.current:
				self.current[field] = ""
		
	def Update(self, db, updateTime, user, newValues):
		#Validate lat, lon
		if "lat" in newValues:
			newValues["lat"] = float(newValues["lat"])
			if newValues["lat"] < -90.: newValues["lat"] = -90.
			if newValues["lat"] > 90.: newValues["lat"] = 90.

		if "lon" in newValues:
			newValues["lon"] = float(newValues["lon"])
			if newValues["lon"] < -180.: newValues["lon"] = -180.
			if newValues["lon"] > 180.: newValues["lon"] = 180.

		#See what has been changed
		changedData = {}
		for key in newValues:
			if newValues[key] != self.current[key]:
				changedData[key] = newValues[key]

		#Return if nothing changed
		if len(changedData) == 0:
			return

		#Track recent changes
		updateJosn = json.dumps(changedData)
		if self.recentChangeTracker is not None:
			self.recentChangeTracker.Updated(user, updateTime, updateJosn, self.rowId)

		#Update record in database
		vars2 = {"id": self.rowId}
		self.edits.append(((user, updateTime), changedData))
		changedFieldsJosn = json.dumps(self.edits)
		db.update("data", where="id=$id", vars=vars2, edits=changedFieldsJosn)

		#Update spatial table in database
		spatialChange = {}
		if "lat" in changedData:
			spatialChange["minLat"] = changedData["lat"]
			spatialChange["maxLat"] = changedData["lat"]
		if "lon" in changedData:
			spatialChange["minLon"] = changedData["lon"]
			spatialChange["maxLon"] = changedData["lon"]

		if len(spatialChange) > 0:
			db.update("pos", where="id=$id", vars=vars2, **spatialChange)

class RecentChangeTracker(object):
	def __init__(self, db):
		self.db = db

	def Updated(self, user, updateTime, changedFieldsJosn, recordId):
		results = self.db.insert("recentchanges", username = user, modifyTime = updateTime, 
			edits = changedFieldsJosn, recordId = recordId)

class RecordPage(object):
	def GET(self):
		return self.Render()

	def POST(self):
		db = web.ctx.db
		webinput = web.input()
		rowId = int(webinput["record"])

		if web.ctx.session.get("username", None) == None:
			return self.Render("Log in first")

		recentChangeTracker = RecentChangeTracker(db)
		record = Record(db, rowId, recentChangeTracker)

		#Enumerate plugins
		plugins = GetPlugins(record.fixedData["source"])
		pluginInstances = []
		for plugin in plugins:
			baseModule = __import__("plugins."+plugin)
			pluginModule = getattr(baseModule, plugin)
			pluginInstance = pluginModule.Plugin()
			pluginInstances.append(pluginInstance)

		for pluginInstance in pluginInstances:
			pluginInstance.ProcessWebPost(db, webinput, record)

		return self.Render()

	def Render(self, actionMessage = None):
		db = web.ctx.db
		webinput = web.input()
		rowId = int(webinput["record"])

		recentChangeTracker = RecentChangeTracker(db)
		record = Record(db, rowId, recentChangeTracker)
		collectedPluginResults = {}
		pluginHeaderIncs = []
		pluginIncs = []

		#Enumerate plugins
		plugins = GetPlugins(record.fixedData["source"])
		pluginInstances = []
		for plugin in plugins:
			baseModule = __import__("plugins."+plugin)
			pluginModule = getattr(baseModule, plugin)
			pluginInstance = pluginModule.Plugin()
			pluginInstances.append(pluginInstance)

		#Call plugins to prepare data
		for pluginInstance in pluginInstances:
			pluginResults = pluginInstance.PrepareData(record)
			collectedPluginResults.update(pluginResults)

		#Get header includes from plugins
		for pluginInstance in pluginInstances:
			hdrInc = pluginInstance.GetHeaderInclude()
			if hdrInc is not None:
				pluginHeaderIncs.append(hdrInc)

		#Get body includes from plugins
		for pluginInstance in pluginInstances:
			bdyInc = pluginInstance.GetBodyInclude()
			if bdyInc is not None:
				pluginIncs.append(bdyInc)

		return app.RenderTemplate("record.html", record=record, 
			webinput=webinput, pluginIncs = pluginIncs,
			pluginHeaderIncs = pluginHeaderIncs,
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

class PluginPage(object):
	def GET(self):
		db = web.ctx.db
		webinput = web.input()
		pluginArg = webinput["plugin"]
		action = webinput["action"]
		rowId = int(webinput["record"])

		record = Record(db, rowId)

		#Enumerate plugins
		plugins = GetPlugins(record.fixedData["source"])
		pluginInstances = {}
		for plugin in plugins:
			baseModule = __import__("plugins."+plugin)
			pluginModule = getattr(baseModule, plugin)
			pluginInstance = pluginModule.Plugin()
			pluginInstances[plugin] = pluginInstance

		#Check if specified plugin exists
		if pluginArg in pluginInstances:
			instance = pluginInstances[pluginArg]
			response = instance.PluginPage(action)
			if response is None: return

			#Request page from plugin
			template, params = response
			return app.RenderTemplate(template, webinput=webinput, session = web.ctx.session, **params)

	def POST(self):
		return GET(self)

class RecentChanges(object):
	def GET(self):
		db = web.ctx.db
		webinput = web.input()

		changes = db.select("recentchanges", order="modifyTime DESC", limit = 100)
		changes = list(changes)
		recordDict = {}

		for change in changes:
			recordId = change["recordId"]
			if recordId in recordDict: continue

			record = Record(db, recordId)	
			recordDict[recordId] = record

		return app.RenderTemplate("recentchanges.html", webinput=webinput, session = web.ctx.session, 
			changes = changes, recordDict = recordDict)





