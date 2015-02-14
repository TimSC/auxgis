import sqlite3

if __name__=="__main__":
	conn = sqlite3.connect('auxgis.db')
	users = sqlite3.connect('users.db')	

	c = conn.cursor()

	# Spatial index
	try:
		c.execute('''CREATE VIRTUAL TABLE pos USING rtree(id, minLat, maxLat, minLon, maxLon);''')

	except Exception as err:
		print "Could not create table pos,", err

	#Meta data table
	try:
		c.execute('''CREATE TABLE data
				(id INTEGER PRIMARY KEY AUTOINCREMENT, 
				name text, 
				source text, 
				lat real, 
				lon real, 
				extended text,
				edits text);''')

	except Exception as err:
		print "Could not create table data,", err

	#User table
	usersc = users.cursor()

	try:
		usersc.execute('''CREATE TABLE users
				(id INTEGER PRIMARY KEY AUTOINCREMENT, 
				username text, 
				salt text, 
				email text,
				password_hash text
				);''')
	except Exception as err:
		print "Could not create table users,", err

	try:
		usersc.execute('''CREATE INDEX username_index ON users (username);''')
	except Exception as err:
		print "Could not create index username_index,", err

	#Recent changes table

	try:
		c.execute('''CREATE TABLE recentchanges
				(id INTEGER PRIMARY KEY AUTOINCREMENT, 
				username text, 
				modifyTime float, 
				recordId INTEGER,
				edits text
				);''')
	except Exception as err:
		print "Could not create table recentchanges,", err


	#User POIs

	try:
		c.execute('''CREATE TABLE pois
				(id INTEGER PRIMARY KEY AUTOINCREMENT, 
				username text, 
				recordId INTEGER,
				toVisit INTEGER,
				visitedDates TEXT
				);''')
	except Exception as err:
		print "Could not create table pois,", err

	conn.commit()
	users.commit()

