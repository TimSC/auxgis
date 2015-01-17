
class RawEditPlugin(object):
	def __init__(self):
		pass

	def PrepareData(self, record):
		return {}

	def ProcessWebPost(self, db, webinput, record):
		if webinput["action"] == "Update record":
			formData = {}		
			for key in webinput:
				if key[:6] != "field_": continue
				keyName = key[6:]
				formData[keyName] = webinput[key]
			
			record.Update(db, time.time(), web.ctx.session.username, formData)

