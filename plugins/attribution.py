
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
		return

	def GetBodyInclude(self):
		return "inc-record-attribution.html"

	def GetRecordSummary(self, record, recMeta):
		pass

