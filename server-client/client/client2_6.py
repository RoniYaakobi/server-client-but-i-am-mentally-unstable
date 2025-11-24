__author__ = 'Yossi'
# 2.6  client server October 2021

import socket, sys,traceback

class Client:
    def __init__(self, serv_addr = "127.0.0.1"):
        self.serv_addr = serv_addr

    def logtcp(self, dir, byte_data):
        """
        log direction and all TCP byte array data
        return: void
        """
        if dir == 'sent':
            print(f'C LOG:Sent     >>>{byte_data}')
        else:
            print(f'C LOG:Recieved <<<{byte_data}')


    def send_data(self, sock, bdata):
        """
        send to client byte array data
        will add 8 bytes message length as first field
        e.g. from 'abcd' will send  b'00000004~abcd'
        return: void
        """
        bytearray_data = str(len(bdata)).zfill(8).encode() + b'~' + bdata
        sock.send(bytearray_data)
        self.logtcp('sent', bytearray_data)


    def menu(self):
        """
        show client menu
        return: string with selection
        """
        print('\n  1. ask for time')
        print('\n  2. ask for random')
        print('\n  3. ask for name')
        print('\n  4. notify exit')
        print('\n  (5. some invalid data for testing)')
        return input('Input 1 - 4 > ' )


    def protocol_build_request(self, from_user):
        """
        build the request according to user selection and protocol
        return: string - msg code
        """
        if from_user == '1':
            return 'TIME'
        elif from_user == '2':
            return 'RAND'
        elif from_user == '3':
            return 'WHOU'
        elif from_user == '4':
            return 'EXIT'
        elif from_user == '5':
            return input("enter free text data to send> ")
        else:
            return ''


    def protocol_parse_reply(self, reply):
        """
        parse the server reply and prepare it to user
        return: answer from server string
        """

        to_show = 'Invalid reply from server'
        try:
            reply = reply.decode()
            if '~' in reply:
                fields = reply.split('~')
            code = reply[:4]
            if code == 'TIMR':
                to_show = 'The Server time is: ' + fields[1]
            elif code == 'RNDR':
                to_show = 'Server draw the number: ' +  fields[1]
            elif code == 'WHOR':
                to_show = 'Server name is: ' +  fields[1]
            elif code == 'ERRR':
                to_show = 'Server return an error: ' + fields[1] + ' ' + fields[2]
            elif code == 'EXTR':
                to_show = 'Server acknowledged the exit message';
        except:
            print ('Server replay bad format')
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
                self.send_data(sock,to_send.encode())
                byte_data = sock.recv(1000)   # todo improve it to recv by message size
                if byte_data == b'':
                    print ('Seems server disconnected abnormal')
                    break
                self.logtcp('recv',byte_data)
                byte_data = byte_data[9:]  # remove length field
                self.handle_reply(byte_data)

                if from_user == '4':
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