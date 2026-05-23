import socket
import threading
import time

# =========================
# Configuration
# =========================
HOST = "127.0.0.1"
PORT = 5000

AUCTION_DURATION = 20
MIN_INCREMENT = 50
EXPECTED_CLIENTS = 3

# =========================
# Log
# =========================
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


# =========================
# Global State
# =========================

items = [
    {"name": "Laptop", "base_price": 500},
    {"name": "Phone", "base_price": 300},
    {"name": "Tablet", "base_price": 400},
]

# TODO:
# Create the variables needed to keep the record of connected clients.
#
# One possible design is:
# clients = []
# client_names = {}
# client_files = {}
# client_active = {}
# passed_current_item = {}

# TODO:
# Create the synchronization objects needed by the server.
#
# Suggested syntax:
# clients_lock = threading.Lock()
# auction_lock = threading.Lock()
# bid_event = threading.Event()
# stop_event = threading.Event()

# TODO:
# Create the global variables needed for:
# - server_socket
# - accept_thread
# - auction_thread
# - client_threads
# - accepting_clients
# - auction_started
# - current_item_index
# - current_price
# - current_winner
# - current_winner_name
# - auction_active
# - auction_end_time


# =========================
# Utilities
# =========================
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


def send_message(sock, message):
    # TODO:
    # Send one complete line to a client socket.
    #
    # Suggested syntax:
    # try:
    #     sock.sendall((message + "\n").encode("utf-8"))
    #     return True
    # except:
    #     return False
    pass


def broadcast(message):
    # TODO:
    # Send the same message to all active clients.
    #
    # General steps:
    # 1. Make a copy of the connected client list while protected by clients_lock.
    # 2. Iterate over that copy.
    # 3. For each active client, call send_message(sock, message).
    # 4. If sending fails, remove that client.
    pass


def remove_client(sock):
    # TODO:
    # Remove one client from the server record.
    #
    # General steps:
    # 1. Enter the critical section protected by clients_lock.
    # 2. Mark the client as inactive.
    # 3. Remove the socket from the client list.
    # 4. Remove its name, file object, and PASS flag from dictionaries.
    # 5. After leaving the critical section, close the file object if it exists.
    # 6. Close the socket with safe_shutdown_close(sock).
    pass


def close_all_clients():
    # TODO:
    # Close every connected client.
    #
    # Suggested logic:
    # 1. Make a copy of the client list.
    # 2. Iterate over the copy.
    # 3. Call remove_client(sock) for each one.
    pass


def get_current_item():
    # TODO:
    # Return the current item from the item list.
    #
    # Suggested logic:
    # - If current_item_index is valid, return items[current_item_index]
    # - Otherwise return None
    pass


def reset_pass_flags():
    # TODO:
    # Reset the PASS flag of all connected clients.
    #
    # Suggested logic:
    # - Enter clients_lock
    # - For every client in the client list:
    #       passed_current_item[sock] = False
    pass


# =========================
# Command Processing
# =========================
def process_view(sock):
    # TODO:
    # Answer the VIEW command.
    #
    # General logic:
    # 1. Enter auction_lock.
    # 2. Get the current item.
    # 3. If there are no more items, send NO_MORE_ITEMS.
    # 4. If the auction is active, send:
    #       item name, current price, and current leader
    # 5. Otherwise send VIEW NO_ACTIVE_AUCTION.
    pass


def process_pass(sock):
    # TODO:
    # Process the PASS command.
    #
    # General logic:
    # 1. Enter clients_lock.
    # 2. Mark passed_current_item[sock] = True.
    # 3. Get the client name.
    # 4. Send OK PASS to that client.
    # 5. Broadcast that this client passed.
    pass


def process_bid(sock, parts):
    # TODO:
    # Remember:
    # if this function modifies global variables,
    # use the Python keyword global.
    #
    # General logic:
    # 1. Verify that the command has exactly two parts:
    #       BID <amount>
    # 2. Convert parts[1] to an integer.
    # 3. Get the bidder name from the client record.
    # 4. Enter auction_lock.
    # 5. Verify that an auction is active.
    # 6. Compute the minimum valid bid:
    #       min_valid = current_price + MIN_INCREMENT
    # 7. If amount is too low, reject it.
    # 8. If valid:
    #       update current_price
    #       update current_winner
    #       update current_winner_name
    #       restart auction_end_time using time.time() + AUCTION_DURATION
    # 9. Reset this client's PASS flag.
    # 10. Send OK BID_ACCEPTED.
    # 11. Broadcast NEW_BID.
    # 12. Notify the timer thread with bid_event.set().
    pass


def process_exit(sock):
    # TODO:
    # Process EXIT.
    #
    # General logic:
    # 1. Send OK EXIT.
    # 2. Remove the client with remove_client(sock).
    pass


# =========================
# Threads
# =========================
def handle_client(sock, addr):
    try:
        # This wrapper allows reading complete lines from the socket.
        file_obj = sock.makefile("r", encoding="utf-8")

        # Ask the client for its name.
        send_message(sock, "[SERVER] ENTER_NAME")

        # TODO:
        # Read the first line from file_obj as the client name.
        #
        # Suggested syntax:
        # name = file_obj.readline()
        name = None

        if not name:
            remove_client(sock)
            return

        name = name.strip()

        if name == "":
            remove_client(sock)
            return

        # TODO:
        # Save the client information in the server record.
        #
        # General logic:
        # - enter clients_lock
        # - store the client name
        # - store file_obj
        # - mark the client as active
        # - initialize its PASS flag as False

        send_message(sock, f"[SERVER] HELLO NAME={name}")
        log_message(f"[SERVER] CLIENT_REGISTERED NAME={name} ADDR={addr}")

        while not stop_event.is_set():
            # TODO:
            # Read one command line from file_obj.
            #
            # Suggested syntax:
            # line = file_obj.readline()
            line = None

            if not line:
                break

            message = line.strip()

            if message == "":
                continue

            # Split the command into words.
            parts = message.split()
            command = parts[0].upper()

            # TODO:
            # Process the command:
            # if command == "VIEW": process_view(sock)
            # elif command == "BID": process_bid(sock, parts)
            # elif command == "PASS": process_pass(sock)
            # elif command == "EXIT": process_exit(sock) and return
            # else: send ERROR INVALID_COMMAND

    except:
        pass

    remove_client(sock)


def accept_clients_loop():
    # TODO:
    # If this function modifies global variables,
    # remember to declare them with global.
    #
    # General logic:
    # 1. Print that the server is listening.
    # 2. While the server is accepting clients:
    #       accept a new connection
    #       accept() returns:
    #           sock  -> client socket
    #           addr  -> client address
    # 3. If the auction has already started, reject the client.
    # 4. Otherwise, add the client socket to the client list.
    # 5. Create one thread for handle_client(sock, addr).
    # 6. Start the thread and save it in client_threads.
    # 7. When the number of connected clients reaches EXPECTED_CLIENTS,
    #    stop accepting more clients.
    #
    # Suggested socket syntax:
    # sock, addr = server_socket.accept()
    pass


def auction_loop():
    # TODO:
    # If this function modifies global variables,
    # remember to declare them with global.
    #
    # General logic:
    # 1. Mark that the auction phase has started.
    # 2. Iterate through all items in the item list.
    # 3. For each item:
    #       - set current_price to the base price
    #       - clear the winner
    #       - mark auction_active = True
    #       - compute auction_end_time = time.time() + AUCTION_DURATION
    #       - reset PASS flags
    #       - clear bid_event
    #       - broadcast AUCTION_START
    #
    # 4. While the auction is active:
    #       - compute remaining = int(auction_end_time - time.time())
    #       - if remaining <= 0, finish this auction
    #       - optionally send TIME_LEFT
    #       - wait for new bids with:
    #             bid_event.wait(timeout=0.5)
    #       - if the event was set, clear it with bid_event.clear()
    #
    # 5. When the timer finishes:
    #       - mark auction_active = False
    #       - if there is a winner, send AUCTION_END with winner and price
    #       - otherwise send AUCTION_END with WINNER=None
    #
    # 6. After all items:
    #       - broadcast SERVER_SHUTDOWN
    #       - set stop_event
    pass


# =========================
# Start / Shutdown
# =========================
def start_server():
    # TODO:
    # If this function modifies global variables,
    # remember to declare them with global.
    #
    # General logic:
    # 1. Create the server socket.
    #    Suggested syntax:
    #    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    #
    # 2. Allow fast reuse of the port.
    #    Suggested syntax:
    #    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    #
    # 3. Bind the socket to the server address.
    #    Suggested syntax:
    #    server_socket.bind((HOST, PORT))
    #
    # 4. Start listening for connections.
    #    Suggested syntax:
    #    server_socket.listen()
    #
    # 5. Create and start the thread that accepts clients.
    #
    # 6. Wait until all expected clients are connected.
    #
    # 7. Create and start the auction thread.
    #
    # 8. Wait for the auction thread to finish.
    #
    # 9. Close the server socket.
    #
    # 10. Wait for the accept thread.
    #
    # 11. Close all client sockets.
    #
    # 12. Wait for all client threads.
    #
    # 13. Print SERVER_CLOSED.
    pass