#Recipe for apache: http://webpy.org/cookbook/mod_wsgi-apache
#Jinja2 templating using solution 2 from: http://webpy.org/cookbook/template_jinja

#sudo apt-get install apache2 libapache2-mod-wsgi python-dev python-jinja2
#sudo easy_install web.py
#sudo easy_install mwparserfromhell
#sudo easy_install flickrapi

import web, os, sys, datetime
sys.path.append(os.path.dirname(__file__))
import webpages, userpages, conf, plugins
from jinja2 import Environment,FileSystemLoader

urls = (
	'/', 'webpages.SearchNear',
	'/nearby', 'webpages.Nearby',
	'/nearbygpx', 'webpages.NearbyGpx',
	'/record', 'webpages.RecordPage',
	'/login', 'userpages.LogIn',
	'/logout', 'userpages.LogOut',
	'/register', 'userpages.Register',
	'/searchnear', 'webpages.SearchNear',
	'/plugin', 'webpages.PluginPage',
	'/recentchanges', 'webpages.RecentChanges',
	'/longnames', 'webpages.LongNames',
	)

def Jinja2DateTime(value):
	dt = datetime.datetime.fromtimestamp(value)
	return dt.strftime("%Y-%m-%d %H:%M:%S")

def RenderTemplate(template_name, **context):
	extensions = context.pop('extensions', [])
	globals = context.pop('globals', {})

	jinja_env = Environment(
			loader=FileSystemLoader(os.path.join(os.path.dirname(__file__), 'templates')),
			extensions=extensions,
			)
	jinja_env.globals.update(globals)
	jinja_env.filters['datetime'] = Jinja2DateTime

	#jinja_env.update_template_context(context)
	return jinja_env.get_template(template_name).render(context)

def InitDatabaseConn():
	curdir = os.path.dirname(__file__)
	web.ctx.db = web.database(dbn='sqlite', db=os.path.join(curdir, 'auxgis.db'))
	web.ctx.users = web.database(dbn='sqlite', db=os.path.join(curdir, 'users.db'))
	web.ctx.session = session

web.config.debug = conf.debug
app = web.application(urls, globals())
curdir = os.path.dirname(__file__)
app.add_processor(web.loadhook(InitDatabaseConn))

session = web.session.Session(app, web.session.DiskStore(os.path.join(curdir,'sessions')),)

application = app.wsgifunc()

