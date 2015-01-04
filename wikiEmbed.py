import urllib2, json
import mwparserfromhell

class MediawikiArticle(object):
	def __init__(self, articleName):

		url = "https://en.wikipedia.org/w/api.php?format=json&action=query&titles={0}&prop=revisions&rvprop=content".format(urllib2.quote(articleName))
		#print url
		ha = urllib2.urlopen(url)
		result = ha.read()
		#print result
		decodedResult = json.loads(result)	

		pageIds = decodedResult["query"]["pages"].keys()
		self.text = None

		if pageIds > 0:
			pageData = decodedResult["query"]["pages"][pageIds[0]]
			self.wikicode = pageData["revisions"][0]["*"]
			wp = mwparserfromhell.parse(self.wikicode)
			self.text = wp.strip_code()

if __name__ == "__main__":

	wiki = MediawikiArticle("Stoughton Barracks")
	print wiki.text


