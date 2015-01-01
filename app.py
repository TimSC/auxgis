#Recipe for apache: http://webpy.org/cookbook/mod_wsgi-apache

import web

urls = (
	'/.*', 'hello',
	)

class hello:
	def GET(self):
			return "Hello, world."

application = web.application(urls, globals()).wsgifunc()

