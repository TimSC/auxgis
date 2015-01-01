#Recipe for apache: http://webpy.org/cookbook/mod_wsgi-apache

import web, os
import sqlite3

urls = (
	'/.*', 'hello',
	)

class hello:
	def GET(self):
		cur = web.ctx.db.cursor()
		cur.execute("SELECT name FROM data;")
		tmp = []
		count = 0

		while True:
		  
			row = cur.fetchone()
			
			if row == None:
				break
				
			tmp.append(row[0])
			count += 1
			if count > 100:
				break


		return "Hello, world." + (",".join(tmp[:100])) + "..."

def my_loadhook():
	curdir = os.path.dirname(__file__)
	conn = sqlite3.connect(os.path.join(curdir, 'auxgis.db'))
	web.ctx.db = conn

app = web.application(urls, globals())

curdir = os.path.dirname(__file__)

app.add_processor(web.loadhook(my_loadhook))

session = web.session.Session(app, web.session.DiskStore(os.path.join(curdir,'sessions')),)


application = app.wsgifunc()

