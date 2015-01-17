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
	try:
		c.execute('''DROP TABLE recentchanges;''')
	except:
		pass

	conn.commit()

