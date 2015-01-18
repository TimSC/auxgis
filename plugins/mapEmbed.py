import conf, os, sqlitedict, time, json, web
import flickrapi, urllib2
		
class Plugin(object):
	def __init__(self):
		pass

	def PrepareData(self, record):
		return {}

	def ProcessWebPost(self, db, webinput, record):
		return

	def PluginPage(self, action):
		return

	def GetHeaderInclude(self):
		return 'inc-record-map-header.html'

	def GetBodyInclude(self):
		return "inc-record-map.html"

	def GetRecordSummary(self, record, recMeta):
		pass


if __name__=="__main__":
	pass
