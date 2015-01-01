#Recipe for apache: http://webpy.org/cookbook/mod_wsgi-apache

import web, os, sys
sys.path.append(os.path.dirname(__file__))
import webpages

urls = (
	'/.*', 'webpages.TestPage',
	)

def InitDatabaseConn():
	curdir = os.path.dirname(__file__)
	web.ctx.db = web.database(dbn='sqlite', db=os.path.join(curdir, 'auxgis.db'))

app = web.application(urls, globals())
curdir = os.path.dirname(__file__)
app.add_processor(web.loadhook(InitDatabaseConn))
session = web.session.Session(app, web.session.DiskStore(os.path.join(curdir,'sessions')),)

application = app.wsgifunc()

