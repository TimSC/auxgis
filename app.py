#Recipe for apache: http://webpy.org/cookbook/mod_wsgi-apache

import web, os
import sqlite3

urls = (
	'/.*', 'hello',
	)

class hello:
	def GET(self):
		db = web.ctx.db
		results = db.select("data", limit = 100)
		names = [tmp["name"] for tmp in results]

		return "Hello, world." + (",<br/>".join(names)) + "..."

def my_loadhook():
	curdir = os.path.dirname(__file__)
	conn = web.database(dbn='sqlite', db=os.path.join(curdir, 'auxgis.db'))
	web.ctx.db = conn

app = web.application(urls, globals())
curdir = os.path.dirname(__file__)
app.add_processor(web.loadhook(my_loadhook))
session = web.session.Session(app, web.session.DiskStore(os.path.join(curdir,'sessions')),)

application = app.wsgifunc()

