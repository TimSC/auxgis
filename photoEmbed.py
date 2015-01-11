import conf, os, sqlitedict, time, json
import flickrapi

def GetFlickrHandle():
	flickr = flickrapi.FlickrAPI(conf.flickrKey, conf.flickrSecret)
	return flickr

class FlickrPhotoInfo(object):
	def __init__(self, flickr, photo_id, enableCache=True):
		self.flickr = flickr
		
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
		self.usageCanShare = photo["usage"]["canshare"]

	def _RetrieveViaWeb(self, photo_id):
		resultJson = self.flickr.photos.getInfo(photo_id=photo_id, format='parsed-json')
		self.title = None
		self.description = None

		self._ExtractFields(resultJson)
		if self.cache is not None:
			self.cache[photo_id] = (time.time(), json.dumps(resultJson))

class FlickrPhotoSizes(object):
	def __init__(self, flickr, photo_id):
		sizeResult = flickr.photos.getSizes(photo_id=photo_id)
	
		self.photoByWidth = {}
		self.photoByHeight = {}
		if len(sizeResult) > 0:

			photoSizes = sizeResult[0]
			for size in photoSizes:
				height = int(size.attrib['height'])
				width = int(size.attrib['width'])
				self.photoByWidth[width] = size.attrib
				self.photoByHeight[height] = size.attrib

class FlickrSearch(object):
	def __init__(self, flickr, tags):

		self.photos = []
		result = flickr.photos.search(tags=tags)
		for grp in result:
			for p in grp:
				self.photos.append(p.attrib)
		
if __name__=="__main__":
	print conf.flickrKey

	flickr = flickrapi.FlickrAPI(conf.flickrKey, conf.flickrSecret)

	if 1:
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


