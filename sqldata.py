import sqlite3
import re
def data_add(data):
	db = sqlite3.connect('Directory.db')
	cursor = db.cursor()
	try:
		cursor.executemany('INSERT INTO Listing VALUES (?,?,?,?)' , (data,))
		db.commit()
		print "It worked !"
	except:
		print "Not Working"
	db.close()

def add_data(data1):
	data1 = re.split(" " , data1)
	count = 0
	for i in xrange(len(data1)/4): 
		data = data1[count:count+4]
		print data
		data_add(data)
		count = count+4

def query_data(filename):
	db = sqlite3.connect('Directory.db')
	cursor = db.cursor()
	filename = (filename,)
	sql = 'SELECT * FROM Listing WHERE FILE_NAME = ?'
	cursor.execute(sql, filename)
	a = cursor.fetchall()
	l =[]
	for x in a:
		for i in x:
			l.append(str(i))
	l =  (' ').join(l).replace(',',' ')
	return l
	db.close()
		
def query_list():
	db = sqlite3.connect('Directory.db')
	cursor = db.cursor()
	sql = 'SELECT * FROM Listing'
	try:	
		l =[]
		cursor.execute(sql)
		a = cursor.fetchall()
		for x in a:
			for i in x:
				l.append(str(i))
		l = (' ').join(l).replace(',',' ')
		return l
	except:
		print "Error: unable to fecth data"
		return -1
	db.close()

def query_delete(host):
	db = sqlite3.connect('Directory.db')
	cursor = db.cursor()
	sql = 'DELETE FROM Listing WHERE HOST_NAME = ?'
	cursor.execute(sql,(host,))
	db.commit()
	db.close() 
