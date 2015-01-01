import sqlite3

if __name__=="__main__":
	conn = sqlite3.connect('auxgis.db')
	c = conn.cursor()

	try:
		c.execute('''DROP TABLE pos;''')
	except:
		pass
	try:
		c.execute('''DROP TABLE data;''')
	except:
		pass

	# Create tables
	c.execute('''CREATE VIRTUAL TABLE pos USING rtree(id, minLat, maxLat, minLon, maxLon);''')

	c.execute('''CREATE TABLE data
		         (id ROWID, name text, source text, lat real, lon real, extended text);''')

	conn.commit()

