import urllib2, json, sqlitedict, time, os, web
import mwparserfromhell, webpages
from xml.sax.saxutils import escape, unescape

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

		url = u"https://en.wikipedia.org/w/api.php?format=json&action=query&titles={0}&prop=revisions&rvprop=content&continue=".format(urllib2.quote(articleName.encode('utf8')))
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
		firstPageId = int(pageIds[0])

		if firstPageId < 0:
			raise RuntimeError("Wiki page not found")
		else:
			pageData = decodedResult["query"]["pages"][str(firstPageId)]
			self.wikicode = pageData["revisions"][0]["*"]
			wp = mwparserfromhell.parse(self.wikicode)
			self.text = wp.strip_code()

class MediawikiSearch(object):
	def __init__(self, lat, lon, radius):

		url = [u"https://en.wikipedia.org/w/api.php?format=json&action=query&list=geosearch&gsradius={2}&gscoord={0}|{1}&continue&gslimit=5000".format(lat,lon,radius)]
		url.append(u"&continue")

		#print u"".join(url)
		ha = urllib2.urlopen(u"".join(url))
		jsonDat = ha.read()
		#print result
		decodedResult = json.loads(jsonDat)	
		#print decodedResult

		if "error" in decodedResult:
			raise RuntimeError(decodedResult["error"]["info"])

		self.results = []
		geoResults = decodedResult["query"]["geosearch"]
		for result in geoResults:
			self.results.append(result)
		

class Plugin(object):
	def __init__(self):
		pass

	def PrepareData(self, record):
		#Process wikipedia link into embeded text
		wikipediaArticle = record.current["wikipedia"]
		wikis = []

		if wikipediaArticle is not None and len(wikipediaArticle) > 0:
			try:
				article = MediawikiArticle(wikipediaArticle)
			except RuntimeError:
				#Page not found
				return {"wikis": wikis}

			wikiEntry = {}
			textExtract = SplitTextByParagraph(article.text, 1000)
			wikiEntry["text"] = escape(textExtract).replace("\n", "<br/>")
			wikiEntry["url"] = u"https://en.wikipedia.org/wiki/{0}".format(urllib2.quote(wikipediaArticle.encode('utf8')))
			wikiEntry["credit"] = "Wikipedia"
			wikiEntry["article"] = wikipediaArticle

			wikis.append(wikiEntry)

		return {"wikis": wikis}

	def ProcessWebPost(self, db, webinput, record):
		if webinput["action"] == "associate" and webinput["plugin"] == "wikiEmbed":

			formData={'wikipedia': webinput["article"]}
			record.Update(db, time.time(), web.ctx.session.username, formData)

		if webinput["action"] == "link" and webinput["plugin"] == "wikiEmbed":
			opts = {}
			for opt in webinput:
				optSplit = opt.split("-", 2)
				if optSplit[0] != "opt": continue
				rowId = int(optSplit[1])
				if rowId not in opts: opts[rowId] = []

				opts[rowId].append((optSplit[2], webinput[opt]))

			for rowId in opts:
				recentChangeTracker = webpages.RecentChangeTracker(db)
				record = webpages.Record(db, rowId, recentChangeTracker)
				newTitle = None
				changed = False

				for wikiTitle, action in opts[rowId]:
					if action == "unset" and wikiTitle == record.current["wikipedia"]:
						newTitle = None
						changed = True
					if action == "set" and wikiTitle != record.current["wikipedia"]:
						newTitle = wikiTitle
						changed = True
				
				if changed:
					record.Update(db, time.time(), web.ctx.session.username, {"wikipedia": newTitle})

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

			searchResult = MediawikiSearch(lat, lon, webinput["radius"])
			result = []
			for r in searchResult.results:
				r["url"] = u"https://en.wikipedia.org/wiki/{0}".format(urllib2.quote(r["title"].encode('utf8')))
				result.append(r)

			out = {}
			out["lat"] = lat
			out["lon"] = lon
			out["result"] = result

			return ("searchwikipedia.html", out)

		if action == "link":
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
			
			#Get nearby wikipedia articles
			searchResult = MediawikiSearch(lat, lon, webinput["radius"])
			result = []
			for r in searchResult.results:
				r["url"] = u"https://en.wikipedia.org/wiki/{0}".format(urllib2.quote(r["title"].encode('utf8')))
				result.append(r)

			#List nearby local records
			for r in result:
				nearbyRecords, nearbyMeta = webpages.GetRecordsNear(db, r["lat"], r["lon"], maxRecs = 10)
				for nearRec in nearbyRecords:
					if r["title"] == nearRec.current["wikipedia"]:
						nearRec.selected = 1
					else:
						if nearRec.current["wikipedia"] == None or nearRec.current["wikipedia"] == "":
							nearRec.selected = 0
						else:
							nearRec.selected = -1

					#a = nearRec.current["wikipedia"]
					#b = r["title"]
					#assert 0

				r["nearby"] = nearbyRecords
				r["meta"] = nearbyMeta

			out = {}
			out["lat"] = lat
			out["lon"] = lon
			out["result"] = result

			return ("linkwikipedia.html", out)

	def GetHeaderInclude(self):
		return

	def GetBodyInclude(self):
		return "inc-record-wikipedia.html"

	def GetRecordSummary(self, record, recMeta):
		if len(record.current["wikipedia"]) > 0:
			recMeta["pluginData"].append("wiki!")

if __name__ == "__main__":
	if 0:
		wiki = MediawikiArticle("Stoughton Barracks")
		print wiki.text
	if 1:
		#wiki = MediawikiSearch(53., -1.2, 10000)
		wiki = MediawikiSearch(51.07922714916926, 1.143951416015625, 10000)

		for result in wiki.results:
			print result


