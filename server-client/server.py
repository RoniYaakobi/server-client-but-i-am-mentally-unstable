__author__ = 'Yossi'

# 2.6  client server October 2021
from tcp_by_size import send_with_size, recv_by_size, DELIMETER
from ftp_protocol import send_file
import socket, random, traceback
import time, threading, os, datetime, subprocess

class Server:
	_instance = None

	def __new__(cls, *args, **kwargs):
		if cls._instance is None:
			cls._instance = super().__new__(cls)
		return cls._instance

	def __init__(self):
		self.all_to_die = False
		self.threads = []

		code_to_reply = dict()

		self.no_op = lambda *x: ""

		code_to_reply["TIME"] = ("TIMR", self.get_time)
		code_to_reply["RAND"] = ("RNDR", self.get_random) 
		code_to_reply["WHOU"] = ("WHOR", self.get_server_name) 
		code_to_reply["EXEC"] = ("EXER", self.run_executable)
		code_to_reply["DIRC"] = ("DIRR", self.get_dir)
		code_to_reply["DELP"] = ("DELR", self.del_path)
		code_to_reply["COPY"] = ("CPYR", self.copy)
		code_to_reply["DWLD"] = ("DWNR", self.send_to_client)
		code_to_reply["EXIT"] = ("EXTR", self.no_op)

		self.code_to_reply = code_to_reply

	def check_length(self, sock, message):
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


	def get_time(self, sock, *args):
		"""return local time """
		return DELIMETER + datetime.datetime.now().strftime('%H:%M:%S:%f')


	def get_random(self, sock, *args):
		"""return random 1-10 """
		return DELIMETER + str(random.randint(1, 10))

	def get_server_name(self, sock, *args):
		"""return server name from os environment """
		return DELIMETER + os.environ['COMPUTERNAME']
	
	def run_executable(self, sock, exe, *args):
		if args == ():
			output = subprocess.run(executable=exe, capture_output=True, text=True, args = tuple())
		else:
			output = subprocess.run(executable=exe, capture_output=True, text=True, args=args)
		stdout = output.stdout

		return DELIMETER + (stdout if stdout != None else "")
	
	def get_dir(self, sock, path):
		result = subprocess.run(f'dir "{path}"', capture_output=True, text=True, shell=True)

		return DELIMETER + result.stdout
	
	def del_path(self, sock, path):
		if os.path.isfile(path):
			result = subprocess.run(f'del "{path}"', capture_output=True, text=True, shell=True)
		elif os.path.isdir(path):
			result = subprocess.run(f'rmdir /s /q "{path}"', capture_output=True, text=True, shell=True)
		else:
			raise FileNotFoundError

		return DELIMETER + result.stdout
	
	def copy(self, sock, source_path, destination_path):
		if os.path.isfile(source_path):
			result = subprocess.run(f'copy "{source_path}" "{destination_path}"', capture_output=True, text=True, shell=True)
		elif os.path.isdir(source_path):
			result = subprocess.run(f'robocopy "{source_path}" "{destination_path}" /E', capture_output=True, text=True, shell=True)
		else:
			raise FileNotFoundError

		return DELIMETER + result.stdout
	
	def send_to_client(self, sock, path):
		return DELIMETER + send_file(sock, path)

	def protocol_build_reply(self, sock, request):
		"""
		Application Business Logic
		function despatcher ! for each code will get to some function that handle specific request
		Handle client request and prepare the reply info
		string:return: reply
		"""

		request_code = request[:4].decode()

		code, func = self.code_to_reply.get(request_code, ("ERRR~002~code not supported", self.no_op))

		request = request.decode("utf8")

		args = request[5:].split(DELIMETER) # ignore opcode and start reading the arguments

		reply = f"{code}{func(sock, *args)}"
		
		return reply.encode()

	def handle_request(self, sock, request):
		"""
		Hadle client request
		tuple :return: return message to send to client and bool if to close the client socket
		"""
		try:
			request_code = request[:4]
			to_send = self.protocol_build_reply(sock, request)
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
				byte_data = recv_by_size(sock)
				
				if byte_data == '':
					send_with_size(sock, b'ERRR~003~Bad Format, incorrect message length or data')
					break
				
				to_send , finish = self.handle_request(sock, byte_data)
				if to_send != '':
					send_with_size(sock, to_send)
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
		srv_sock.bind(('0.0.0.0', 42006))
		srv_sock.listen(20)

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
