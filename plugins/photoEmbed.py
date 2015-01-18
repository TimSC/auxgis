import conf, os, sqlitedict, time, json, web
import flickrapi, urllib2

def GetFlickrHandle():
	flickr = flickrapi.FlickrAPI(conf.flickrKey, conf.flickrSecret)
	return flickr

class FlickrPhotoInfo(object):
	def __init__(self, flickr, photo_id, enableCache=True):
		self.flickr = flickr

		self.title = None
		self.description = None
		self.ownerRealName = None
		self.ownerUserName = None
		self.ownerPathAlias = None
		self.usageCanShare = None
		self.ownerNsid = None

		if enableCache:
			curdir = os.path.dirname(__file__)
			self.cache = sqlitedict.SqliteDict(os.path.join(curdir, 'FlickrPhotoInfo.db'), autocommit=False)
		else:
			self.cache = None

		if self.cache:
			#Check if photo is available in cache			
			available = photo_id in self.cache
			if available:
				recordTime, recordData = self.cache[photo_id]
				ageSec = time.time() - recordTime

				#If not too old
				if ageSec < 24*60*60:
					#Use cached version
					self._ExtractFields(json.loads(recordData))
					return

		self._RetrieveViaWeb(photo_id)

	def __del__(self):
		if self.cache is not None:
			self.cache.commit()

	def _ExtractFields(self, result):
		photo = result["photo"]	

		self.title = photo["title"]["_content"]
		self.description = photo["description"]["_content"]
		self.ownerRealName = photo["owner"]["realname"]
		self.ownerUserName = photo["owner"]["username"]
		self.ownerPathAlias = photo["owner"]["path_alias"]
		self.ownerNsid = photo["owner"]["nsid"]
		self.usageCanShare = photo["usage"]["canshare"]
		self._raw = photo

	def _RetrieveViaWeb(self, photo_id):
		resultJson = self.flickr.photos.getInfo(photo_id=photo_id, format='json')
		result = json.loads(resultJson)
		self._ExtractFields(result)
		if self.cache is not None:
			self.cache[photo_id] = (time.time(), resultJson)

class FlickrPhotoSizes(object):
	def __init__(self, flickr, photo_id, enableCache=True):
		self.flickr = flickr	

		self.photoByWidth = {}
		self.photoByHeight = {}

		if enableCache:
			curdir = os.path.dirname(__file__)
			self.cache = sqlitedict.SqliteDict(os.path.join(curdir, 'FlickrPhotoSizes.db'), autocommit=False)
		else:
			self.cache = None

		if self.cache:
			#Check if photo is available in cache			
			available = photo_id in self.cache
			if available:
				recordTime, recordData = self.cache[photo_id]
				ageSec = time.time() - recordTime

				#If not too old
				if ageSec < 24*60*60:
					#Use cached version
					self._ExtractFields(json.loads(recordData))
					return

		self._RetrieveViaWeb(photo_id)

	def __del__(self):
		if self.cache is not None:
			self.cache.commit()

	def _ExtractFields(self, result):
		for size in result['sizes']['size']:
			height = int(size['height'])
			width = int(size['width'])
			self.photoByWidth[width] = size
			self.photoByHeight[height] = size

	def _RetrieveViaWeb(self, photo_id):
		sizeResultJson = self.flickr.photos.getSizes(photo_id=photo_id, format='json')
		sizeResult = json.loads(sizeResultJson)

		self._ExtractFields(sizeResult)

		if self.cache is not None:
			self.cache[photo_id] = (time.time(), sizeResultJson)

class FlickrSearch(object):
	def __init__(self, flickr, tags=None, lat=None, lon=None, text=None,radius=None):

		self.photos = []
		sort = "interestingness-desc"
		#sort = "date-posted-desc"

		resultJson = flickr.photos.search(tags=tags, format='json', lat = lat, lon = lon, sort=sort, radius=radius, text=text)
		result = json.loads(resultJson)
		for p in result["photos"]["photo"]:
			self.photos.append(p)
		
class Plugin(object):
	def __init__(self):
		pass

	def PrepareData(self, record):

		#Get stored flickr IDs
		flickrIds = set(record.current["flickr"].split(","))
		photos = []
		flickrHandle = GetFlickrHandle()

		#Search using flickr API for tags that match this ID
		tag = u"england_listed_building:entry={0}".format(record.current["ListEntry"])
		flickrSearch = FlickrSearch(flickrHandle, tag)
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
				photoInfo = FlickrPhotoInfo(flickrHandle, idClean)
				if int(photoInfo.usageCanShare) != 1: continue
				photoSizes = FlickrPhotoSizes(flickrHandle, idClean)
			#except Exception as err:
				#raise err			
			#	continue

			userPth = photoInfo.ownerNsid

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

		if webinput["action"] == "associate" and webinput["plugin"] == "photoEmbed":


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

			formData={'flickr': ", ".join(currentFlickrStrIds)}
			record.Update(db, time.time(), web.ctx.session.username, formData)

	def PluginPage(self, action):
		if action == "search":
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

			flickrHandle = GetFlickrHandle()
			photoSearch = FlickrSearch(flickrHandle, text=webinput["text"], lat=lat, lon=lon, radius=webinput["radius"])

			photos = []
			for photo in photoSearch.photos:
				photoId = int(photo["id"])

				photoInfo = FlickrPhotoInfo(flickrHandle, photoId)
				if int(photoInfo.usageCanShare) != 1: continue
				photoSizes = FlickrPhotoSizes(flickrHandle, photoId)

				userPth = photoInfo.ownerNsid

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

			out = {}
			out["lat"] = lat
			out["lon"] = lon
			out["photos"] = photos

			return ("searchflickr.html", out)

	def GetHeaderInclude(self):
		return

	def GetBodyInclude(self):
		return "inc-record-flickr.html"

if __name__=="__main__":
	print conf.flickrKey

	flickr = flickrapi.FlickrAPI(conf.flickrKey, conf.flickrSecret)

	if 0:
		photoInfo = FlickrPhotoInfo(flickr, 16060702179)
		print photoInfo.title
		print photoInfo.ownerRealName
		print photoInfo.ownerUserName
		print photoInfo.ownerPathAlias
	if 0:
		photoSizes = FlickrPhotoSizes(flickr, 6282944807)
		print photoSizes.photoByWidth.keys()

	if 0:
		search = FlickrSearch(flickr, "england_listed_building:entry=1377883")
		print search.photos
	if 1:
		search = FlickrSearch(flickr, lat = 51.2410774907, lon = -0.589782409589, text="Cathedral")
		print search.photos

