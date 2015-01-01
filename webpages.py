import web

class TestPage:
	def GET(self):
		db = web.ctx.db
		results = db.select("data", limit = 100)
		names = [tmp["name"] for tmp in results]

		return "<br/>".join(names)
