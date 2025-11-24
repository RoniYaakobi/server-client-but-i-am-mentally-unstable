__author__ = 'Yossi'

# 2.6  client server October 2021
import socket, random, traceback
import time, threading, os, datetime

class Server:
	_instance = None

	def __new__(cls, *args, **kwargs):
		if cls._instance is None:
			cls._instance = super().__new__(cls)
		return cls._instance

	def __init__(self):
		self.all_to_die = False
		self.threads = []

	def logtcp(self, dir, tid, byte_data):
		"""
		log direction, tid and all TCP byte array data
		return: void
		"""
		if dir == 'sent':
			print(f'{tid} S LOG:Sent     >>> {byte_data}')
		else:
			print(f'{tid} S LOG:Recieved <<< {byte_data}')

	def send_data(self, sock, tid, bdata):
		"""
		send to client byte array data
		will add 8 bytes message length as first field
		e.g. from 'abcd' will send  b'00000004~abcd'
		return: void
		"""
		bytearray_data = str(len(bdata)).zfill(8).encode() + b'~' + bdata
		sock.send(bytearray_data)
		self.logtcp('sent',tid, bytearray_data)
		print("")


	def check_length(self, message):
		"""
		check message length
		return: string - error message
		"""
		size = len(message)
		if size < 13:  # 13 is min message size
			return b'ERRR~003~Bad Format message too short'
		if int(message[:8].decode()) !=  size -9:
			return b'ERRR~003~Bad Format, incorrect message length'
		return b''


	def get_time(self):
		"""return local time """
		return datetime.datetime.now().strftime('%H:%M:%S:%f')


	def get_random(self):
		"""return random 1-10 """
		return str(random.randint(1, 10))

	def get_server_name(self):
		"""return server name from os environment """
		return os.environ['COMPUTERNAME']

	def protocol_build_reply(self, request):
		"""
		Application Business Logic
		function despatcher ! for each code will get to some function that handle specific request
		Handle client request and prepare the reply info
		string:return: reply
		"""
		request_code = request[:4].decode()
		request = request.decode("utf8")
		if request_code == 'TIME':
			reply = 'TIMR' +'~' + self.get_time()
		elif request_code == 'RAND':
			reply ='RNDR' + '~' + self.get_random()
		elif request_code == 'WHOU':
			reply ='WHOR' + '~' + self.get_server_name()
		elif request_code == 'EXIT':
			reply= 'EXTR'
		else:
			reply = 'ERRR~002~code not supported'
			fields = ''
		return reply.encode()

	def handle_request(self, request):
		"""
		Hadle client request
		tuple :return: return message to send to client and bool if to close the client socket
		"""
		try:
			request_code = request[:4]
			to_send = self.protocol_build_reply(request)
			if request_code == b'EXIT':
				return to_send, True
		except Exception as err:
			print(traceback.format_exc())
			to_send =  b'ERRR~001~General error'
		return to_send, False

	def handle_client(self, sock, tid , addr):
		"""
		Main client thread loop (in the server),
		:param sock: client socket
		:param tid: thread number
		:param addr: client ip + reply port
		:return: void
		"""
		finish = False
		print(f'New Client number {tid} from {addr}')
		while not finish:
			if self.all_to_die:
				print('will close due to main server issue')
				break
			try:
				byte_data = sock.recv(1000)  # todo improve it to recv by message size
				if byte_data == b'':
					print ('Seems client disconnected')
					break
				self.logtcp('recv',tid, byte_data)
				err_size = self.check_length(byte_data)
				if err_size != b'':
					to_send = err_size
				else:
					byte_data = byte_data[9:]   # remove length field
					to_send , finish = self.handle_request(byte_data)
				if to_send != '':
					self.send_data(sock, tid , to_send)
				if finish:
					time.sleep(1)
					break
			except socket.error as err:
				print(f'Socket Error exit client loop: err:  {err}')
				break
			except Exception as  err:
				print(f'General Error %s exit client loop: {err}')
				print(traceback.format_exc())
				break

		print(f'Client {tid} Exit')
		sock.close()

	def main(self):
		"""
		main server loop
		1. accept tcp connection
		2. create thread for each connected new client
		3. wait for all threads
		4. every X clients limit will exit
		"""
		srv_sock = socket.socket()
		input("0")
		srv_sock.bind(('0.0.0.0', 42006))
		input("1")
		srv_sock.listen(20)
		input("2")
		#next line release the port
		srv_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

		i = 1
		while True:
			print('\nMain thread: before accepting ...')
			cli_sock , addr = srv_sock.accept()
			print('\n3')
			t = threading.Thread(target = self.handle_client, args=(cli_sock, str(i), addr))
			t.start()
			i+=1
			self.threads.append(t)
			if i > 4:     # for tests change it to 4
				print('\nMain thread: going down for maintenance')
				break

		self.all_to_die = True
		print('Main thread: waiting to all clints to die')
		for t in self.threads:
			t.join()
		srv_sock.close()
		print( 'Bye ..')


if __name__ == '__main__':
	server = Server()
	server.main()
