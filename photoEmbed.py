import conf
import flickrapi

def DumpFlickrResult(result):
	for photo in result:
		for t in photo:
			print t, t.attrib, t.text
			for a in t:
				print "\t", a, a.attrib

def GetFlickrHandle():
	flickr = flickrapi.FlickrAPI(conf.flickrKey, conf.flickrSecret)
	return flickr

class FlickrPhotoInfo(object):
	def __init__(self, flickr, photo_id):
		result = flickr.photos.getInfo(photo_id=photo_id)
		self.title = None
		self.description = None
	
		#DumpFlickrResult(result)	

		#DumpResult(result)
		if len(result) > 0:
			photo = result[0]
			self.title = photo.find("title").text
			self.description = photo.find("description").text
			self.ownerRealName = photo.find("owner").attrib["realname"]
			self.ownerUserName = photo.find("owner").attrib["username"]
			self.ownerPathAlias = photo.find("owner").attrib["path_alias"]
			self.usageCanShare = photo.find("usage").attrib["canshare"]
			print photo.find("owner").attrib

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


