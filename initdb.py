import sqlite3

if __name__=="__main__":
	conn = sqlite3.connect('auxgis.db')
	c = conn.cursor()

	c.execute('''DROP TABLE pos;''')
	c.execute('''DROP TABLE data;''')

	# Create tables
	c.execute('''CREATE VIRTUAL TABLE pos USING rtree(id, minLat, maxLat, minLon, maxLon);''')

	c.execute('''CREATE TABLE data
		         (id ROWID, name text, lat real, lon real, extended text);''')

