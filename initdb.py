import sqlite3

if __name__=="__main__":
	conn = sqlite3.connect('auxgis.db')

	# Create table
	c.execute('''CREATE TABLE stocks
		         (date text, trans text, symbol text, qty real, price real)''')

