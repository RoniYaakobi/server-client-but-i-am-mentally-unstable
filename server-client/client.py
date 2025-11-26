__author__ = 'Yossi'
# 2.6  client server October 2021


from tcp_by_size import send_with_size, recv_by_size
import socket, sys, traceback

class Client:
    def __init__(self, serv_addr = "127.0.0.1"):
        self.serv_addr = serv_addr

        code_to_request = dict()

        no_op = lambda *x: ""

        code_to_request["1"] = ("TIME", no_op)
        code_to_request["2"] = ("RAND", no_op) 
        code_to_request["3"] = ("WHOU", no_op)
        code_to_request["4"] = ("EXEC", self.get_exec_args)
        code_to_request["5"] = ("DIRC", self.get_path) 
        code_to_request["6"] = ("EXIT", no_op)

        self.code_to_request = code_to_request

        reply_to_format = dict()

        reply_to_format["TIMR"] = lambda fields : "The Server time is: " + fields[0]
        reply_to_format["RNDR"] = lambda fields : "Server draw the number: " + fields[0] 
        reply_to_format["WHOR"] = lambda fields : "Server name is: " + fields[0]
        reply_to_format["ERRR"] = lambda fields : "Server return an error: " + fields[0] + " " + fields[1]
        reply_to_format["EXER"] = lambda fields : "Stdout was " + fields[0] if fields != "" else "Empty"
        reply_to_format["DIRR"] = lambda fields : "Directory: " + fields[0]
        reply_to_format["EXTR"] = lambda fields : "Server acknowledged the exit message"


        self.reply_to_format = reply_to_format


    def get_exec_args(self):
        args = []
        arg = input("Path of the executable: ")
        
        while arg != "":
            args.append(arg)
            arg = input("Any additional arguments? Enter an empty line if not. ")
        
        if len(args) < 1:
            print("You must have at least the executable path!")
            return ""

        return "~"+"~".join(args)
    def get_path(self):
        path = input("Path to view: ")
        if path != "":
            return f'~"{path}"'

        return ""


    def menu(self):
        """
        show client menu
        return: string with selection
        """
        print("""Choose the operation you want to make:
              1. Ask server for time
              2. Ask server for random number
              3. Ask server for name
              4. Ask server to run an executable
              5. View a directory in the server's file system
              6. Ask server to disconnect""")
        return input('Input Code > ' )


    def protocol_build_request(self, from_user):
        """
        build the request according to user selection and protocol
        return: string - msg code
        """
        code, func = self.code_to_request[from_user]

        return f"{code}{func()}"


    def protocol_parse_reply(self, reply):
        """
        parse the server reply and prepare it to user
        return: answer from server string
        """

        to_show = 'Invalid reply from server'
        try:
            reply = reply.decode()
            fields = []
            if '~' in reply:
                fields = reply.split('~')
            code = reply[:4]
            format = self.reply_to_format[code]
            to_show = format(fields[1:])
        except:
            print('Server replay bad format')
        return to_show


    def handle_reply(self, reply):
        """
        get the tcp upcoming message and show reply information
        return: void
        """
        to_show = self.protocol_parse_reply(reply)
        if to_show != '':
            print('\n==========================================================')
            print (f'  SERVER Reply: {to_show}   |')
            print(  '==========================================================')


    def main(self):
        """
        main client - handle socket and main loop
        """
        connected = False

        sock= socket.socket()

        port = 42006
        try:
            sock.connect((self.serv_addr,port))
            print (f'Connect succeeded {self.serv_addr}:{port}')
            connected = True
        except:
            print(f'Error while trying to connect.  Check ip or port -- {self.serv_addr}:{port}')

        while connected:
            from_user = self.menu()
            to_send = self.protocol_build_request(from_user)
            if to_send =='':
                print("Selection error try again")
                continue
            try :
                send_with_size(sock, to_send.encode())
                byte_data = recv_by_size(sock)
                if byte_data == b'':
                    print ('Seems server disconnected abnormal')
                    break
                self.handle_reply(byte_data)

                if from_user == "6":
                    print('Will exit ...')
                    connected = False
                    break
            except socket.error as err:
                print(f'Got socket error: {err}')
                break
            except Exception as err:
                print(f'General error: {err}')
                print(traceback.format_exc())
                break
        print ('Bye')
        sock.close()


if __name__ == '__main__':
    client = Client(sys.argv[1]) if len(sys.argv) > 1 else Client()
    client.main()