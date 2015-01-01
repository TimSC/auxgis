import web, app

class TestPage:
	def GET(self):
		db = web.ctx.db
		results = db.select("data", limit = 100)
		webinput = web.input()

		return app.RenderTemplate("helloworld.html", test=results, webinput=webinput)

