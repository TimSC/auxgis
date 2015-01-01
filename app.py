#Recipe for apache: http://webpy.org/cookbook/mod_wsgi-apache

import web, os

urls = (
	'/.*', 'hello',
	)

class hello:
	def GET(self):
			return "Hello, world."

app = web.application(urls, globals())

curdir = os.path.dirname(__file__)
session = web.session.Session(app, web.session.DiskStore(os.path.join(curdir,'sessions')),)

application = app.wsgifunc()

