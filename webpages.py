import web, app

class TestPage:
	def GET(self):
		db = web.ctx.db
		webinput = web.input()
		lat = float(webinput["lat"])
		lon = float(webinput["lon"])

		latHWidth = 0.05
		lonHWidth = 0.1

		vrs = {'minLat':lat-latHWidth, 'maxLat':lat+latHWidth, 'minLon':lon-lonHWidth, 'maxLon': lon+lonHWidth}
		cond = "minLat>=$minLat AND maxLat<=$maxLat AND minLon>=$minLon AND maxLon<=$maxLon"
		#cond = "1=1"
		results = db.select("pos", where=cond, vars=vrs, limit = 1000)
		out = []

		for record in results:
			rowId = record["id"]
			
			vars2 = {"id": rowId}
			dataResults = db.select("data", where="id=$id", vars= vars2, limit = 100)
			dataResults = list(dataResults)
			assert len(dataResults) > 0

			out.append(dataResults[0])
			a = dataResults[0]

		return app.RenderTemplate("helloworld.html", test=out, webinput=webinput)

