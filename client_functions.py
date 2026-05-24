import socket
import threading
import sys

HOST = "127.0.0.1"
PORT = 5000

stop_event = threading.Event()

LOG_FILE = None


def open_log_file(filename):
    global LOG_FILE
    LOG_FILE = open(filename, "w", encoding="utf-8")


def close_log_file():
    global LOG_FILE
    if LOG_FILE is not None:
        LOG_FILE.close()
        LOG_FILE = None


def log_message(message):
    print(message, flush=True)
    if LOG_FILE is not None:
        LOG_FILE.write(message + "\n")
        LOG_FILE.flush()


def safe_shutdown_close(sock):
    try:
        sock.shutdown(socket.SHUT_RDWR)
    except:
        pass

    try:
        sock.close()
    except:
        pass


def receive_messages(sock):
    try:
        file_obj = sock.makefile("r", encoding="utf-8")

        while not stop_event.is_set():
            line = file_obj.readline()

            if not line:
                break

            message = line.strip()

            if message == "":
                continue

            log_message(message)

            if message == "SERVER_SHUTDOWN":
                stop_event.set()
                break

        file_obj.close()

    except:
        pass

    stop_event.set()


def send_commands(sock):
    try:
        while not stop_event.is_set():
            line = sys.stdin.readline()

            if not line:
                break

            command = line.strip()

            if command == "":
                continue

            sock.sendall((command + "\n").encode("utf-8"))

            if command.upper() == "EXIT":
                stop_event.set()
                break

    except:
        pass


def start_client():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    sock.connect((HOST, PORT))

    recv_thread = threading.Thread(target=receive_messages, args=(sock,), daemon=True)
    send_thread = threading.Thread(target=send_commands, args=(sock,), daemon=True)

    recv_thread.start()
    send_thread.start()

    send_thread.join()
    recv_thread.join()

    stop_event.set()
    safe_shutdown_close(sock)

    recv_thread.join(timeout=2)
