import socket
import threading
import pickle


class ChatServer:
    def __init__(self, ip, port):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((ip, port))
        self.server_socket.listen(10)
        print(f"Server listening on {ip}:{port}")
        self.clients = []  # List of connected clients
        self.groups = {}  # Dictionary to manage groups

    def broadcast_groups(self):
        group_list = list(self.groups.keys())
        for client in self.clients:
            try:
                client.send(pickle.dumps({"type": "update_groups", "groups": group_list}))
            except Exception as e:
                print(f"Error broadcasting group list: {e}")

    def handle_client(self, client_socket):
        while True:
            try:
                data = client_socket.recv(4096)
                if not data:
                    break  # Break the loop if no data is received
                message = pickle.loads(data)
                if message["type"] == "group_message":
                    group = message["group_name"]
                    self.broadcast_group_message(message["data"], group, client_socket)
                elif message["type"] == "create_group":
                    group_name = message["group_name"]
                    self.groups[group_name] = []  # Create new group
                    self.broadcast_groups()  # Notify all clients about new group
                elif message["type"] == "join_group":
                    group_name = message["group_name"]
                    if group_name in self.groups:
                        self.groups[group_name].append(client_socket)
                    self.broadcast_groups()  # Notify clients
                elif message["type"] == "file_transfer":
                    self.receive_file(client_socket, message["group_name"], message["filename"])
            except Exception as e:
                print(f"Error handling client: {e}")
                break

    # Clean up the client connection
        self.clients.remove(client_socket)
        client_socket.close()


    def receive_file(self, client_socket, group_name, filename):
        """Receive a file from the client and broadcast it."""
        file_size = int.from_bytes(client_socket.recv(8), 'big')  # Receive file size
        file_data = b''
        while len(file_data) < file_size:
            chunk = client_socket.recv(min(file_size - len(file_data), 4096))
            if not chunk:
                break
            file_data += chunk

        file_path = f"received_{filename}"
        with open(file_path, 'wb') as f:
            f.write(file_data)

        # Broadcast the file to the group
        self.broadcast_group_message(file_data, group_name, is_file=True, filename=filename)

    def broadcast_group_message(self, message, group_name):
        if group_name in self.groups:
            for client in self.groups[group_name]:
                try:
                    client.send(pickle.dumps({"type": "group_message", "data": message, "group_name": group_name}))
                except Exception as e:
                    print(f"Error sending message: {e}")

    def start(self):
        print("Server started...")
        while True:
            client_socket, _ = self.server_socket.accept()
            print("Client connected")
            self.clients.append(client_socket)
            threading.Thread(target=self.handle_client, args=(client_socket,)).start()

if __name__ == "__main__":
    server = ChatServer('127.0.0.1', 9999)
    server.start()
