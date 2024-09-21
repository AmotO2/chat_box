import socket
import threading
import pickle
from PyQt5.QtWidgets import QMainWindow, QApplication, QPushButton, QTextEdit, QFileDialog, QVBoxLayout, QWidget, QComboBox, QInputDialog
import os
import sys
from PyQt5.QtMultimedia import QSound  # To play audio files

class ChatWindow(QMainWindow):
    def __init__(self, client):
        super().__init__()
        self.client = client

        # Set up the window
        self.setWindowTitle("Chat Application")
        self.setGeometry(100, 100, 600, 500)

        # Main Layout
        layout = QVBoxLayout()

        # Chat display
        self.chat_display = QTextEdit(self)
        self.chat_display.setReadOnly(True)
        layout.addWidget(self.chat_display)

        # Group selection dropdown
        self.group_dropdown = QComboBox(self)
        layout.addWidget(self.group_dropdown)

        # Message input
        self.message_input = QTextEdit(self)
        layout.addWidget(self.message_input)

        # Buttons
        self.send_btn = QPushButton('Send', self)
        self.send_btn.clicked.connect(self.send_message)
        layout.addWidget(self.send_btn)

        self.img_btn = QPushButton('Send Image', self)
        self.img_btn.clicked.connect(self.send_image)
        layout.addWidget(self.img_btn)

        self.audio_btn = QPushButton('Send Audio', self)
        self.audio_btn.clicked.connect(self.send_audio)
        layout.addWidget(self.audio_btn)

        # Group Buttons
        self.create_group_btn = QPushButton('Create Group', self)
        self.create_group_btn.clicked.connect(self.create_group)
        layout.addWidget(self.create_group_btn)

        self.join_group_btn = QPushButton('Join Group', self)
        self.join_group_btn.clicked.connect(self.join_group)
        layout.addWidget(self.join_group_btn)

        # Set central widget
        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def send_message(self):
        message = self.message_input.toPlainText()
        group = self.group_dropdown.currentText()
        if group:
            self.client.send_group_message(message, group)
        self.message_input.clear()

    def send_image(self):
        image_file, _ = QFileDialog.getOpenFileName(self, "Select Image")
        if image_file:
            group = self.group_dropdown.currentText()
            self.client.send_file(image_file, group)
            self.chat_display.append(f"Image sent: {image_file}")

    def send_audio(self):
        audio_file, _ = QFileDialog.getOpenFileName(self, "Select Audio", "", "Audio Files (*.mp3 *.wav)")
        if audio_file:
            group = self.group_dropdown.currentText()
            self.client.send_file(audio_file, group)
            self.chat_display.append(f"Audio file sent: {audio_file}")

    def create_group(self):
        group_name, ok = QInputDialog.getText(self, "Create Group", "Enter group name:")
        if ok and group_name:
            self.client.create_group(group_name)
            self.group_dropdown.addItem(group_name)

    def join_group(self):
        group_name, ok = QInputDialog.getText(self, "Join Group", "Enter group name:")
        if ok and group_name:
            self.client.join_group(group_name)
            self.group_dropdown.addItem(group_name)

    def display_message(self, message):
        self.chat_display.append(message)

    def play_audio(self, filename):
        # Play the audio file
        QSound.play(filename)


class ChatClient:
    def __init__(self, ip, port, update_ui_callback, username):
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_socket.connect((ip, port))
        self.update_ui_callback = update_ui_callback
        self.username = username

    def send_group_message(self, message, group):
        data = {
            "type": "group_message",
            "data": message,
            "group_name": group,
            "username": self.username
        }
        self.client_socket.send(pickle.dumps(data))

    def send_file(self, file_path, group):
        filename = os.path.basename(file_path)
        file_size = os.path.getsize(file_path)

        with open(file_path, 'rb') as f:
            file_data = f.read()

        # Send the file size first
        self.client_socket.send(pickle.dumps({
            "type": "file_transfer",
            "group_name": group,
            "filename": filename,
            "username": self.username  # Include username in file transfers
        }))
        self.client_socket.send(file_size.to_bytes(8, 'big'))  # Send file size
        self.client_socket.sendall(file_data)  # Send file data

    def create_group(self, group_name):
        data = {"type": "create_group", "group_name": group_name, "username": self.username}
        self.client_socket.send(pickle.dumps(data))

    def join_group(self, group_name):
        data = {"type": "join_group", "group_name": group_name, "username": self.username}
        self.client_socket.send(pickle.dumps(data))

    def receive_messages(self):
        while True:
            try:
                data = self.client_socket.recv(4096)
                if data:
                    message = pickle.loads(data)
                    if message["type"] == "group_message":
                        self.update_ui_callback(f"{message['group_name']}: {message['data']}")
                    elif message["type"] == "file_transfer":
                        # Handle file transfer
                        filename = message["filename"]
                        group_name = message["group_name"]

                        file_size = int.from_bytes(self.client_socket.recv(8), 'big')  # Receive file size
                        file_data = b''
                        while len(file_data) < file_size:
                            chunk = self.client_socket.recv(min(file_size - len(file_data), 4096))
                            if not chunk:
                                break
                            file_data += chunk

                        # Save the received file
                        with open(f"received_{filename}", 'wb') as f:
                            f.write(file_data)

                        if filename.endswith(('.mp3', '.wav')):
                            self.update_ui_callback(f"Audio received from {group_name}: {filename}")
                            self.update_ui_callback(f"To play the audio, click the 'Play Audio' button.")
                        else:
                            self.update_ui_callback(f"Image received from {group_name}: {filename}")

                elif message["type"] == "update_groups":
                    # Handle group updates
                    self.group_dropdown.clear()
                    self.group_dropdown.addItems(message["groups"])

            except Exception as e:
                print(f"Error receiving message: {e}")


def main():
    app = QApplication(sys.argv)

    # Ask for username
    username, ok = QInputDialog.getText(None, "Enter Username", "Please enter your username:")
    if not ok or not username:
        return  # If no username is provided, exit

    window = ChatWindow(None)
    client = ChatClient('127.0.0.1', 9999, window.display_message, username)
    window.client = client

    # Start the thread to receive messages
    threading.Thread(target=client.receive_messages, daemon=True).start()

    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
