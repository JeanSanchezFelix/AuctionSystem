import socket
import threading
import time

# =========================
# Configuration
# =========================
HOST = "127.0.0.1"
PORT = 5000

AUCTION_DURATION = 4
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

# Create the variables needed to keep the record of connected clients.
clients = []                # list of connected client sockets
client_names = {}       
client_files = {}           # the text-based file object associated with that socket
client_active = {}          # whether the client is still active,
passed_current_item = {}    # whether the client has declined the current auctioned item

# Create the synchronization objects needed by the server.
clients_lock = threading.Lock()
auction_lock = threading.Lock()
bid_event = threading.Event()
stop_event = threading.Event()

# Create the global variables needed for:
server_socket = None
accept_thread = None
auction_thread = None
client_threads = []
accepting_clients = False
auction_started = False
current_item_index = 0
current_price = 0
current_winner = None
current_winner_name = ""
auction_active = False
auction_end_time = 0


# =========================
# Utilities
# =========================
def safe_shutdown_close(sock):
    
    # Close the socket correctly.
    try:
        sock.shutdown(socket.SHUT_RDWR)
    except:
        pass
    
    try:
        sock.close()
    except:
        pass
    pass


def send_message(sock, message):

    # Send one complete line to a client socket.
    try:
        sock.sendall((message + "\n").encode("utf-8"))
        return True
    except:
        return False
    pass


def broadcast(message):
    # General steps:
    # 1. Make a copy of the connected client list while protected by clients_lock.
    # 2. Iterate over that copy.
    # 3. For each active client, call send_message(sock, message).
    # 4. If sending fails, remove that client.
    log_message(message)

    with clients_lock:
        active_clients = list(clients)

    for sock in active_clients:
        if not send_message(sock, message):
            remove_client(sock)
    pass
            
def remove_client(sock):
    # Remove one client from the server record.
    #
    # General steps:
    # 1. Enter the critical section protected by clients_lock.
    # 2. Mark the client as inactive.
    # 3. Remove the socket from the client list.
    # 4. Remove its name, file object, and PASS flag from dictionaries.
    # 5. After leaving the critical section, close the file object if it exists.
    # 6. Close the socket with safe_shutdown_close(sock).
    
    with clients_lock:
        client_active[sock] = False
        
        client_names.pop(sock, None)
        file_to_close = client_files.pop(sock, None)
        passed_current_item.pop(sock, None)
        
        if sock in clients:
            clients.remove(sock)
    
    if file_to_close is not None:
        try:
            file_to_close.close()
        except Exception:
            pass             
        
    safe_shutdown_close(sock)
    pass


def close_all_clients():
    # Close every connected client.
    #
    # Suggested logic:
    # 1. Make a copy of the client list.
    # 2. Iterate over the copy.
    # 3. Call remove_client(sock) for each one.
    with clients_lock:
        active_clients = list(clients)
    
    for sock in active_clients:
        remove_client(sock)
    pass


def get_current_item():
    # Return the current item from the item list.
    #
    # Suggested logic:
    # - If current_item_index is valid, return items[current_item_index]
    # - Otherwise return None
    
    if 0 <= current_item_index < len(items):
        return items[current_item_index]
    else:
        return None


def reset_pass_flags():
    # Reset the PASS flag of all connected clients.
    #
    # Suggested logic:
    # - Enter clients_lock
    # - For every client in the client list:
    #       passed_current_item[sock] = False
    with clients_lock:
        for socket in clients:
            passed_current_item[socket] = False
    pass


# =========================
# Command Processing
# =========================
def process_view(sock):
    # Answer the VIEW command.
    #
    # General logic:
    # 1. Enter auction_lock.
    # 2. Get the current item.
    # 3. If there are no more items, send NO_MORE_ITEMS.
    # 4. If the auction is active, send:
    #       item name, current price, and current leader
    # 5. Otherwise send VIEW NO_ACTIVE_AUCTION.
    
    with auction_lock:
        current_item = get_current_item()
        
        if current_item is None:
            send_message(sock, "[SERVER] NO_MORE_ITEMS")
        elif auction_active:
            send_message(sock, f"[SERVER] VIEW ITEM={current_item['name']} PRICE={current_price} LEADER={current_winner_name}")
        else:
            send_message(sock, "[SERVER] VIEW NO_ACTIVE_AUCTION")
    pass


def process_pass(sock):
    # Process the PASS command.
    #
    # General logic:
    # 1. Enter clients_lock.
    # 2. Mark passed_current_item[sock] = True.
    # 3. Get the client name.
    # 4. Send OK PASS to that client.
    # 5. Broadcast that this client passed.
    
    with clients_lock:
        passed_current_item[sock] = True
        name = client_names.get(sock)

    send_message(sock, "[SERVER] OK PASS")
    broadcast(f"[SERVER] CLIENT_PASSED NAME={name}")
    pass


def process_bid(sock, parts):
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
    
    global current_price
    global current_winner
    global current_winner_name
    global auction_end_time
    
    if len(parts) != 2:
        send_message(sock, "[SERVER] ERROR INVALID_COMMAND")
        return

    parts = [part.strip() for part in parts if part.strip()]

    try:
        amount = int(parts[1])
        sender_name = client_names.get(sock)
        with auction_lock:
            
            # Verify that an auction is active.
            if auction_active:
                min_valid = current_price + MIN_INCREMENT
                if amount < min_valid:
                    send_message(sock, "[SERVER] ERROR BID_TOO_LOW")
                    return
                else:
                    current_price = amount
                    current_winner = sock
                    current_winner_name = sender_name
                    auction_end_time = time.time() + AUCTION_DURATION

                    # Reset this client's PASS flag.
                    with clients_lock:
                        passed_current_item[sock] = False

                    send_message(sock, "[SERVER] OK BID_ACCEPTED")
                    broadcast(f"[SERVER] NEW_BID NAME={sender_name} PRICE={amount}")
                    bid_event.set()
            
    except ValueError:
        send_message(sock, "[SERVER] ERROR INVALID_BID_AMOUNT")
        return

    pass


def process_exit(sock):
    # Process EXIT.
    #
    # General logic:
    # 1. Send OK EXIT.
    # 2. Remove the client with remove_client(sock).
    with clients_lock:
        passed_current_item[sock] = True
        name = client_names.get(sock)
    send_message(sock, "[SERVER] OK EXIT")
    remove_client(sock)
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

        # Read the first line from file_obj as the client name.
        #
        # Suggested syntax:
        name = file_obj.readline()

        if not name:
            remove_client(sock)
            return

        name = name.strip()

        if name == "":
            remove_client(sock)
            return

        # Save the client information in the server record.
        
        with clients_lock:
            client_names[sock] = name
            client_files[sock] = file_obj
            client_active[sock] = True
            passed_current_item[sock] = False
        

        send_message(sock, f"[SERVER] HELLO NAME={name}")
        log_message(f"[SERVER] CLIENT_REGISTERED NAME={name} ADDR={addr}")

        while not stop_event.is_set():
            # TODO:
            # Read one command line from file_obj.
            #
            # Suggested syntax:
            line = file_obj.readline()

            if not line:
                break

            message = line.strip()

            if message == "":
                continue

            # Split the command into words.
            parts = message.split()
            command = parts[0].upper()

            # Process the command:
            if command == "VIEW":
                process_view(sock)
            elif command == "BID":
                process_bid(sock, parts)
            elif command == "PASS":
                process_pass(sock)
            elif command == "EXIT":
                process_exit(sock)
                return
            else:
                send_message(sock, "[SERVER] ERROR INVALID_COMMAND")

    except:
        pass

    remove_client(sock)


def accept_clients_loop():
    # TODO:
    # If this function modifies global variables,
    # remember to declare them with global.
    global accepting_clients
    global server_socket
    global client_threads
    global auction_started
    #
    # General logic:
    # 1. Print that the server is listening.
    log_message(f"[SERVER] LISTENING ON {HOST}:{PORT}")
    # 2. While the server is accepting clients:
    #       accept a new connection
    #       accept() returns:
    #           sock  -> client socket
    #           addr  -> client address
    while accepting_clients and not stop_event.is_set():
        try:
            sock, addr = server_socket.accept()
            log_message(f"[SERVER] NEW_CONNECTION FROM {addr}")
        except Exception as e:
            log_message(f"[SERVER] ACCEPT_ERROR: {e}")
            continue
    # 3. If the auction has already started, reject the client.
        if auction_started:
            log_message(f"[SERVER] REJECTED CONNECTION FROM {addr} (AUCTION_STARTED)")
            safe_shutdown_close(sock)
            continue
    # 4. Otherwise, add the client socket to the client list.
        else:
            with clients_lock:
                clients.append(sock)

    # 5. Create one thread for handle_client(sock, addr).
            client_thread = threading.Thread(target=handle_client, args=(sock, addr))
    # 6. Start the thread and save it in client_threads.
            client_thread.start()
            client_threads.append(client_thread)
    # 7. When the number of connected clients reaches EXPECTED_CLIENTS,
    #    stop accepting more clients.
            if len(clients) >= EXPECTED_CLIENTS:
                log_message(f"[SERVER] EXPECTED NUMBER OF CLIENTS CONNECTED ({EXPECTED_CLIENTS}). STOPPING ACCEPTING NEW CLIENTS.")
                accepting_clients = False
                break
    


def auction_loop():
    
    global auction_started
    global current_item_index
    global current_price
    global current_winner
    global current_winner_name
    global auction_active
    global auction_end_time

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
    
    auction_started = True
    for index, item in enumerate(items):
        current_item_index = index
        current_price = item["base_price"]
        current_winner = None
        current_winner_name = ""
        auction_active = True
        auction_end_time = time.time() + AUCTION_DURATION
        
        reset_pass_flags()
        bid_event.clear()
        
        broadcast(f"[SERVER] AUCTION_START ITEM={item['name']} BASE_PRICE={item['base_price']}")
        last_remaining = None
        
        while auction_active:
            remaining = int(auction_end_time - time.time())
            if remaining <= 0:
                auction_active = False
                break
            
            # Send TIME_LEFT updates when the number changes.
            if remaining != last_remaining:
                broadcast(f"[SERVER] TIME_LEFT ITEM={item['name']} SECONDS={remaining}")
                last_remaining = remaining
            
            bid_event.wait(timeout=0.5)
            if bid_event.is_set():
                bid_event.clear()
    
        if current_winner is not None:
            broadcast(
                f"[SERVER] AUCTION_END ITEM={item['name']} WINNER={current_winner_name} PRICE={current_price}"
            )
        else:
            broadcast(
                f"[SERVER] AUCTION_END ITEM={item['name']} WINNER=None PRICE=0"
            )
        
    broadcast("[SERVER] SERVER_SHUTDOWN")
    stop_event.set()    


# =========================
# Start / Shutdown
# =========================
def start_server():
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
    #    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSE
    # If this function modifies global variables,
    # remember to declare them with global.
    global server_socket
    global accept_thread
    global auction_thread
    global client_threads
    global accepting_clients
    #
    # General logic:
    # 1. Create the server socket.
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    #
    # 2. Allow fast reuse of the port.
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    #
    # 3. Bind the socket to the server address.
    server_socket.bind((HOST, PORT))
    #
    # 4. Start listening for connections.
    server_socket.listen()
    server_socket.settimeout(0.5)
    #
    # 5. Create and start the thread that accepts clients.
    client_threads = []
    accepting_clients = True
    accept_thread = threading.Thread(target=accept_clients_loop)
    #
    # 6. Wait until all expected clients are connected.
    accept_thread.start()

    while not stop_event.is_set():
        with clients_lock:
            if len(clients) >= EXPECTED_CLIENTS:
                break
        time.sleep(0.05)

    # Stop accepting once we have the expected client count.
    accepting_clients = False

    # 7. Create and start the auction thread.
    auction_thread = threading.Thread(target=auction_loop)
    auction_thread.start()
    #
    # 8. Wait for the auction thread to finish.
    auction_thread.join()
    #
    # 9. Close the server socket.
    safe_shutdown_close(server_socket)
    #
    # 10. Wait for the accept thread.
    accept_thread.join()
    #
    # 11. Close all client sockets.
    close_all_clients()
    #
    # 12. Wait for all client threads.
    for thread in client_threads:
        thread.join(timeout=2)
    #
    # 13. Print SERVER_CLOSED.
    log_message("[SERVER] SERVER_CLOSED")