'''
Structure of http packet 
"Method hostname address
end_of_file file_packet_no seq_no 
message_body 
'''
import socket
import cPickle as pickle
import threading
import os
import re
import random
import sqlite3
from sqldata import *
import time
import select

MTU = 128
hostname = "Directory"
address = ''

# ------------------------------Per Client Thread--------------------------------------

def client_thread(c, addr,data):
	print "Inside the thread for a new connection from a client "
	print ""
	state = 0

# -------------------------------SYNACK -----------------------------------------------
	
	seq_no = random.randint(0,7)
	ack_no = (int(data[1])+1)%8
	msg = "SYNACK " + str(seq_no) +" " +str(ack_no)
	c.sendto(msg,addr)
	print "SYNACK sent !"
	print ""

# ------------------------------SYNACKACK ---------------------------------------------	
	
	data, addr = c.recvfrom(MTU)
	data = re.split(" " , data)
	while (data[0] != "SYNACKACK"):
		state = 0 
	state =1
	print "Received SYNACKACK ! TCP Handshake done ! Connection established !"
	seq_no = int(data[2])%8
	ack_no =(int(data[1])+1)%8

# --------------------------------------------------------------------------------------
# ------------------------------EXCHANGE MSG--------------------------------------------
	
	http_packet, addr = c.recvfrom(MTU)	
	packet = re.split("\r\n\r\n", http_packet)
	packet_header = packet[0]
	packet_header = packet_header.replace("\r\n"," ")
	packet_header = re.split(" ", packet_header)
	if len(packet)>1:
		DATA = packet[1]

# -----------------------------INFORM & UPDATE------------------------------------------
	print packet_header[0]
	if packet_header[0] == "I&A":
		print "DATABASE IS BEING UPDATED"
		
		while packet_header[3]!='0':
			# Send ACK
			seq_no = int(packet_header[5])%8
			ack_no = (int(packet_header[4])+1)%8
			header = "ACK" + " " + str(seq_no) +" "+ str(ack_no)+"\r\n"
			c.sendto(header,addr)
			#Receive NEXT PACKET
			http_packet,addr = c.recvfrom(MTU)
			packet = re.split("\r\n\r\n" , http_packet)
			packet_header = packet[0]
			packet_header = packet_header.replace("\r\n"," ")
			packet_header = re.split(" ",packet_header)
			if len(packet[1]) > 0 and int(packet_header[4])==ack_no:
				DATA = DATA + packet[1]	
			print packet_header
			seq_no = int(packet_header[5])%8
			ack_no = (int(packet_header[4]) + 1)%8
		
		DATA = DATA.replace("\r\n", " ")
	#	DATA = re.split(" ", DATA)
		print "Lock acquired - Thou Shalt Not Pass!"
		lock.acquire()
		add_data(DATA)
		lock.release()
		print "Releasing lock on database - Free you are!"
		#call & Update database

# --------------------------------------------------------------------------------------
# ---------------------------------QUERY-------------------------------------------------
	
	elif packet_header[0] =="QUERY":
		filename = packet_header[3]
		print "Lock acquired - Do. Or do not. There is no try"
		lock.acquire()
		row = query_data(filename)
		lock.release()
		print "Releasing lock - May the force be with you !"		
		if len(row) > 0:
			msg = "200" + " " +"OK" + "\r\n" + row 
			c.sendto(msg,addr)
		
		elif filename == "LIST":
			#read list from database into DATA
			DATA = query_list()
		#	print "Read_data " + DATA
			byte_len = len(DATA)
			count = 0
			end_flag = 1		
			timeout = 0.1
			alpha = 0.125
			while count<(byte_len): 	
				success = 0
				while(success!=1):
							# CREATE AND SEND MSG
					
					header = "I&A "+hostname+" "+address+"\r\n"+str(end_flag)+" "+str(seq_no)+" "+str(ack_no)+"\r\n\r\n" 
					send_size = min((128-len(header)),len(DATA) - count)
					http_msg = header + DATA[count:count+send_size]
					c.sendto(http_msg,addr)

							#  TIMER_START
					
					start_timer = time.time()
					iter_timer = timeout 
					
							# KEEP LISTENING UNTIL TIMEOUT
						
					while (time.time() - start_timer)< timeout and iter_timer >0:
						ready = select.select([c],[],[],iter_timer)
				
						if ready[0]:
							sampleRTT = time.time() - start_timer
							timeout = (1-alpha)*timeout + alpha*sampleRTT
							data ,addr= c.recvfrom(MTU)
							data = data.replace("\r\n" , " ")
							data = re.split(" ", data)
				
								# DUPLICATE/MANGLED ACK 
							
							if data[0] != "ACK" or (int(data[2])) !=((seq_no+1))%8: 
								timelost = time.time()- start_timer
								if timelost > timeout:
									print "Retransmission due to DUPACK:"
									break
								else: 
									iter_timer = timeout - timelost
							else:
								# NOT DUPLICATE - GENUINE ACK

								success = 1
								count+=send_size
								seq_no = int(data[2])%8
								ack_no = (int(data[1])+1)%8
								break
						else:
							print "Retransmitting due to Time out:"	
			
			# send a msg with End_flag =0 
			
			header = "I&A "+hostname+" "+address+"\r\n"+"0"+" "+str(seq_no)+" "+str(ack_no)+"\r\n\r\n"
			c.sendto(header,addr)
			print "Closing Socket opened for Query"
			c.close()	
		else: 
			msg = "400" + " " + "Error" 
			c.sendto(msg,addr)
			c.close()

# ---------------------------------------------------------------------------------------
# --------------------------------MAIN LOOP----------------------------------------------

if __name__ =='__main__':
	conn = sqlite3.connect('Directory.db')
	sql = '''CREATE TABLE IF NOT EXISTS Listing (
	HOST_NAME text,
        FILE_NAME text,
	FILE_SIZE text,
	ADDRESS text,
	UNIQUE(HOST_NAME, FILE_NAME) )'''	 
	lock = threading.Lock()
	c = conn.cursor()
	c.execute(sql)
	s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR , 1)
	
	s.bind(('',5000))  
	print "Server is UP & Running" 
	
	while True:
					# connection request from client
		data, addr = s.recvfrom(MTU)
		data = re.split(" " ,data)
		if data[0] == 'SYN': 
			print "SYN packet received , starting TCP handshake" 
			c = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) 
					# bind a socket at one of the available ports
			c.bind(('',0)) 
			client = threading.Thread(target = client_thread,args=(c,addr,data)) 
			client.start()

		elif data[0]== "EXIT":
			Hostname = data[1]
			query_delete(Hostname)
			Address = data[2]
			print Hostname + " with address : " +Address + " is exiting"
	s.close()


