import socket
import cPickle as pickle 
import os
import math
import threading 
import random
import re
import time
import select

hostname = "host1" # client's name
address = "192.168.0.18" # client's own address
listenPort = 21
listenAddr = '192.168.0.18'
MTU  = 128
server = ('192.168.0.18' , 5000)
timeout = 0.1

# ---------------------------------------------------------------------------------------------------------------------------------
# -----------------------------------------------------Inform and Update-----------------------------------------------------------

		#-----------------User's list of files--------------------

def get_IU_msg():
	filename = raw_input("Enter the file name to be updated or type 'q' if you are done updating:")
	msg = ""
	while filename != 'q' :
		if os.path.isfile(filename):
			size = os.path.getsize(filename)
			msg = msg + hostname +" " + filename + " " + str(size) + " " + address + "\r\n"
			filename = raw_input("Enter the file name to be updated or type 'q' if you are done updating:")
		else:
			print "You do not have the '{0}' file, please enter another filename".format(filename)
			filename = raw_input("Enter the file name to be uploaded or type 'q' if you are done updating:")
	return msg	

def inform_update():

	DATA = get_IU_msg()

		# --------------------SYN---------------------
	
	seq_no = random.randint(0,7)
	c = socket.socket(socket.AF_INET , socket.SOCK_DGRAM)
	c.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR,1)
	c.bind((address,0)) 
	msg= "SYN " + str(seq_no) + " " + '0'
	c.sendto(msg,server)
	print "SENDING SYN ! "

		# ----------------SYNACKACK-------------------
	
	data, thread_addr = c.recvfrom(MTU)
	data = re.split(" ",data)
	if data[0] == "SYNACK": 
		ack_no = (int(data[1])+1)%8 
		seq_no = int(data[2])%8	
		msg = "SYNACKACK " + str(seq_no) + " " + str(ack_no) 
		c.sendto(msg,thread_addr)
		print "SENDING SYNACKACK !! "
		# ------------------DATA----------------------
		
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
			c.sendto(http_msg,thread_addr)
						
							#  TIMER_START
			start_timer = time.time()
			iter_timer = timeout 
			print "Entering inner loop"
						
						# KEEP LISTENING UNTIL TIMEOUT
			while (time.time() - start_timer)< timeout and iter_timer >0:
				ready = select.select([c],[],[],iter_timer)
				if ready[0]:
					sampleRTT = time.time() - start_timer
					timeout = (1-alpha)*timeout + alpha*sampleRTT
					data,addr = c.recvfrom(MTU) 
					data = data.replace("\r\n" , " ")
					data = re.split(" ", data)
					print data	

						# DUPLICATE/MANGLED ACK 
					if data[0] != "ACK" or (int(data[2])) !=((seq_no+1))%8: 
						print "MANGELED / OUT OF ORDRE PACKET"
						timelost = time.time()- start_timer
						if timelost > timeout:
							print "Retransmission due to DUPACK:"
							break
						else: 
							iter_timer = timeout - timelost
					else:
					# NOT DUPLICATE - GENUINE ACK
						print "Packet transmitted successfully ! The force is strong with you !!"
						success = 1
						count+=send_size
						seq_no = int(data[2])%8
						ack_no = (int(data[1])+1)%8
						break
				else:
					print "Retransmission due to Time out:"
		
		# send a msg with End_flag =0 
	
	header = "I&A "+hostname+" "+address+"\r\n"+"0"+" "+str(seq_no)+" "+str(ack_no)+"\r\n\r\n"
	c.sendto(header,thread_addr)
	print "Database Updated ! Closing SOCKET ! Danke Scheon !"
	c.close()

# -----------------------------------------------------------------------------------------------------------------
# -----------------------------------------------Query Content-----------------------------------------------------

def content_query():
	
	print "Quering server "

	# --------------------SYN---------------------
	
	seq_no = random.randint(0,7)
	c = socket.socket(socket.AF_INET , socket.SOCK_DGRAM)
	c.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR,1)
	c.bind((address,0)) 
	msg= "SYN " + str(seq_no) + " " + '0'
	c.sendto(msg,server)

	# ----------------SYNACKACK-------------------
	
	data, thread_addr = c.recvfrom(MTU)
	data = re.split(" ",data)
	if data[0] == "SYNACK": 
		ack_no = (int(data[1])+1)%8 
		seq_no = int(data[2])%8	
		msg = "SYNACKACK " + str(seq_no) + " " + str(ack_no+1) 
		c.sendto(msg,thread_addr)

	# -----------------DATA-----------------------

		method = "QUERY"
		print("Enter the filename to be queried ")
		filename = raw_input("Type LIST if you want the whole list : ")	
		http_msg = method + " " + hostname + " " + address + "\r\n" + filename + "\r\n" 
		c.sendto(http_msg, thread_addr)
		
		if filename == 'LIST': 

			http_packet, addr = c.recvfrom(MTU)
	#		print "Received packet ; " + http_packet	
			packet = re.split("\r\n\r\n", http_packet)
			packet_header = packet[0]
			packet_header = packet_header.replace("\r\n"," ")
			packet_header = re.split(" ", packet_header)
			if len(packet[1]) >0 :# and int(packet_header[4])==ack_no:
				DATA = packet[1]

				while packet_header[3]!="0":
					seq_no = int(packet_header[5])%8
					ack_no = (int(packet_header[4])+1)%8
					header = "ACK" + " " + str(seq_no) +" "+ str(ack_no)+"\r\n"
					c.sendto(header,addr)
				
					http_packet,addr = c.recvfrom(MTU)
					packet = re.split("\r\n\r\n" , http_packet)
					packet_header = packet[0]
					packet_header = packet_header.replace("\r\n"," ")
					packet_header = re.split(" ", packet_header)
					if len(packet[1])>0 and int(packet_header[4])==ack_no:
						DATA = DATA + packet[1]	
					seq_no = int(packet_header[5])%8
					ack_no = (int(packet_header[4]) + 1)%8 
			
				DATA = DATA.replace("\r\n", " ")
				DATA = re.split(" ", DATA)
				count = 0
				print "This is the list of all entries in the table"  			
				for i in xrange(len(DATA)/4):	
					print  DATA[count:count+4]
					count+=4
				c.close()		
		
		else:
						# Single file Requested 
			data = c.recv(MTU)
			data1 = data.replace("\r\n", " ")
			data = re.split(" ", data1)
		
			if data[0] =='200':
				print "File exists"
				data = data[2:]
				print "File size : " + data[2]
				count = 0
				for i in xrange(len(data)/4):
					print data[count:count+4]
				c.close()
			elif data[0] =='400':
				print "File does not exist"
				c.close()
	
	
	# -------------------GET FILE FROM PEER---------

	user_i = raw_input("Do you want to download any file? if YES enter the filename, if NO enter q: ")
	if user_i != "q":
		peer_addr = raw_input("Enter the ip address of peer: ")
		peer_port = int(raw_input("Enter the port no. of peer: "))
		c = socket.socket()
		c.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR,1)
	#	peer_addr = re.split(",", peer_addr)
	#	peer_addr = tuple(peer_addr)
		c.connect((peer_addr,peer_port))
		header = "GET" + " " + filename 
		c.send(header)
		data = c.recv(2048)
		data1 = data.replace("\r\n" , " ")
		packet_data = data1.split(" ")
		if packet_data[0] =="200":
			size = int(packet_data[3])
			f= open("copy_" + filename , 'wb')
			data = c.recv(2048)
			total = len(data)
			f.write(data)
			while total < size:
				data = c.recv(2048)
				total += len(data)
				f.write(data)
		print "File "+ "copy_"+filename+ " Copied to current directory"
		c.close()

# ---------------------------------------------------------------------------------------------------------------------
# -----------------------------------------------------EXIT------------------------------------------------------------
def exit_msg():
	method = "EXIT " + hostname + " " + address
	c = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
	c.bind((address,0))
	c.sendto(method,server)
	c.close()
	exit(0)
# ---------------------------------------------------------------------------------------------------------------------
# ------------------------------------------------P2P Server Block-----------------------------------------------------

def sender(peer_client,filename):
	header = "200" + " " + "OK" + "\r\n"
	msg = header + filename + " " + str(os.path.getsize(filename))
	peer_client.send(msg)
	with open (filename , 'rb') as f:
		data = f.read(2048)
		peer_client.send(data)
		while data != "":
			data = f.read(2048)
			peer_client.send(data)
		peer_client.close()

			# -------------Connection Thread--------------

def p2p_server(peer_client):
	msg = peer_client.recv(2048)
	msg1 = msg.replace("\r\n" , " " )
	packet_data = msg1.split(" ")			
	filename = packet_data[1]	
	if packet_data[0] == 'GET':
		if os.path.isfile(filename):
			sender(peer_client,filename)
		else:
			header = "404" + " " + "File not found" + "\r\n"
			peer_client.send(header)
	elif os.path.isfile(filename):
		header = "405" + " " + "Method not allowed" + "\r\n"
		peer_client.send(header)
	else:
		header = "400" + " " + "Bad Request" + "\r\n"
		peer_client.send(header)

def server_thread():
	peer_i = 1
	if peer_i ==1: 
			# starts the peer_server thread that listens at listernPort and listernAddr
	#	print "Listening ... " 
		listener = socket.socket()
		listener.setsockopt(socket.SOL_SOCKET , socket.SO_REUSEADDR,1)
		listener.bind((listenAddr,listenPort))
		listener.listen(5)
		while True:
			peer_client , address = listener.accept()
			process_t = threading.Thread(target = p2p_server,args=(peer_client,))
			process_t.start()
		listener.close()

# ---------------------------------------------------------------------------------------------------------------------
# --------------------------------------------------MAIN FUCNTION------------------------------------------------------

if __name__ == '__main__':
	
		# -------------Spin off P2P server thread---------------
	server_t = threading.Thread(target = server_thread, args = ())
	server_t.daemon=True
	server_t.start()
	print"Enter 1 for Inform and update"
	print"Enter 2 for Query"
	print"Enter 3 for Exit"
	while(1):
		user_input = raw_input("Enter your response : ")
		if user_input =='1':
			inform_update()
		elif user_input =='2':
			content_query()
		elif user_input =='3':
			exit_msg()
		else:
			print "Ever tried. Ever failed. No matter. Try again. Fail again. Fail better." 
			
					

