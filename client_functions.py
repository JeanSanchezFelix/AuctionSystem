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
    # TODO:
    # Close the socket correctly.
    #
    # Suggested syntax:
    # try:
    #     sock.shutdown(socket.SHUT_RDWR)
    # except:
    #     pass
    #
    # try:
    #     sock.close()
    # except:
    #     pass
    pass


def receive_messages(sock):
    try:
        # This creates a text wrapper around the socket,
        # so messages can be read one line at a time.
        file_obj = sock.makefile("r", encoding="utf-8")

        while not stop_event.is_set():
            # TODO:
            # Read one full line from the server.
            #
            # Suggested syntax:
            # line = file_obj.readline()
            line = None

            # If the socket is closed, readline() returns an empty string.
            if not line:
                break

            # Remove spaces and newline characters.
            message = line.strip()

            if message == "":
                continue

            # Show the message in console and save it in the log.
            log_message(message)

            # TODO:
            # If the server sends SERVER_SHUTDOWN,
            # stop the client by setting stop_event.
            pass

        file_obj.close()

    except:
        pass

    stop_event.set()


def send_commands(sock):
    try:
        while not stop_event.is_set():
            # Read one line written by the user in the console.
            line = sys.stdin.readline()

            if not line:
                break

            command = line.strip()

            if command == "":
                continue

            # TODO:
            # Send the command as a full line to the server.
            #
            # Suggested syntax:
            # sock.sendall((command + "\n").encode("utf-8"))
            pass

            # TODO:
            # If the user typed EXIT, stop this loop.
            pass

    except:
        pass


def start_client():
    # TODO:
    # Create the client socket.
    #
    # Suggested syntax:
    # sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock = None

    # TODO:
    # Connect the socket to the server.
    #
    # Suggested syntax:
    # sock.connect((HOST, PORT))

    # TODO:
    # Create one thread for receive_messages(sock)
    # and one thread for send_commands(sock).
    #
    # Suggested syntax:
    # recv_thread = threading.Thread(target=receive_messages, args=(sock,))
    # send_thread = threading.Thread(target=send_commands, args=(sock,))
    recv_thread = None
    send_thread = None

    # TODO:
    # Start both threads.
    #
    # Suggested syntax:
    # recv_thread.start()
    # send_thread.start()

    # TODO:
    # Wait for the sending thread to finish first.
    #
    # Suggested syntax:
    # send_thread.join()

    # TODO:
    # Wait for the receiving thread.
    # A timeout can be used to avoid waiting forever.
    #
    # Suggested syntax:
    # recv_thread.join(timeout=10)

    # When both threads are done, close the socket.
    stop_event.set()
    # TODO:
    # Call safe_shutdown_close(sock)

    # TODO:
    # Optional final wait for the receiving thread.
    #
    # Suggested syntax:
    # recv_thread.join(timeout=2)