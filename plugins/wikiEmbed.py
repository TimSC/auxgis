import urllib2, json, sqlitedict, time, os
import mwparserfromhell

class MediawikiArticle(object):
	def __init__(self, articleName, enableCache=True):

		self.text = None

		if enableCache:
			curdir = os.path.dirname(__file__)
			self.cache = sqlitedict.SqliteDict(os.path.join(curdir, 'WikipediaArticles.db'), autocommit=False)
		else:
			self.cache = None

		if self.cache is not None:

			#Check if photo is available in cache			
			available = articleName in self.cache
			if available:
				recordTime, recordData = self.cache[articleName]
				ageSec = time.time() - recordTime

				#If not too old
				if ageSec < 24*60*60:
					#Use cached version
					self._ExtractFields(recordData)
					return

		self._RetrieveViaWeb(articleName)

	def __del__(self):
		if self.cache is not None:
			self.cache.commit()

	def _RetrieveViaWeb(self, articleName):

		url = u"https://en.wikipedia.org/w/api.php?format=json&action=query&titles={0}&prop=revisions&rvprop=content&continue=".format(urllib2.quote(articleName))
		#print url
		ha = urllib2.urlopen(url)
		result = ha.read()
		#print result

		self._ExtractFields(result)

		if self.cache is not None:
			self.cache[articleName] = (time.time(), result)

	def _ExtractFields(self, result):

		decodedResult = json.loads(result)	

		pageIds = decodedResult["query"]["pages"].keys()

		if pageIds > 0:
			pageData = decodedResult["query"]["pages"][pageIds[0]]
			self.wikicode = pageData["revisions"][0]["*"]
			wp = mwparserfromhell.parse(self.wikicode)
			self.text = wp.strip_code()

class MediawikiSearch(object):
	def __init__(self, lat, lon, radius):

		url = u"https://en.wikipedia.org/w/api.php?format=json&action=query&list=geosearch&gsradius={2}&gscoord={0}|{1}&continue=".format(lat,lon,radius)
		#print url
		ha = urllib2.urlopen(url)
		result = ha.read()
		#print result
		decodedResult = json.loads(result)	

		self.results = []
		geoResults = decodedResult["query"]["geosearch"]
		for result in geoResults:
			self.results.append(result)


if __name__ == "__main__":
	if 0:
		wiki = MediawikiArticle("Stoughton Barracks")
		print wiki.text
	if 1:
		wiki = MediawikiSearch(37.786971, -122.399677, 10000)
		for result in wiki.results:
			print result


