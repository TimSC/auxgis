import urllib2, json
import mwparserfromhell

class MediawikiArticle(object):
	def __init__(self, articleName):

		url = u"https://en.wikipedia.org/w/api.php?format=json&action=query&titles={0}&prop=revisions&rvprop=content&continue=".format(urllib2.quote(articleName))
		#print url
		ha = urllib2.urlopen(url)
		result = ha.read()
		print result
		decodedResult = json.loads(result)	

		pageIds = decodedResult["query"]["pages"].keys()
		self.text = None

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


