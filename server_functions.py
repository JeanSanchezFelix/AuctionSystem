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

AUCTION_TICK_SECONDS = 0.2
ITEM_TICK_SECONDS = [0.2, 0.3, 0.3]
BID_TICK_SECONDS = 0.08
LOW_RAISE_TICK_SECONDS = 0.02

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

clients = []
client_names = {}
client_files = {}
client_active = {}
passed_current_item = {}

clients_lock = threading.Lock()
auction_lock = threading.Lock()
bid_event = threading.Event()
stop_event = threading.Event()

server_socket = None
accept_thread = None
auction_thread = None
client_threads = []
accepting_clients = True
auction_started = False
current_item_index = -1
current_price = 0
current_winner = None
current_winner_name = "None"
auction_active = False
auction_time_left = 0
current_tick_seconds = AUCTION_TICK_SECONDS


# =========================
# Utilities
# =========================
def safe_shutdown_close(sock):
    try:
        sock.shutdown(socket.SHUT_RDWR)
    except:
        pass

    try:
        sock.close()
    except:
        pass


def send_message(sock, message):
    try:
        sock.sendall((message + "\n").encode("utf-8"))
        return True
    except:
        return False


def broadcast(message):
    with clients_lock:
        current_clients = list(clients)

    for sock in current_clients:
        with clients_lock:
            if not client_active.get(sock, False):
                continue
        ok = send_message(sock, message)
        if not ok:
            remove_client(sock)

    log_message(message)


def remove_client(sock):
    file_obj = None
    with clients_lock:
        client_active[sock] = False
        if sock in clients:
            clients.remove(sock)
        if sock in client_files:
            file_obj = client_files.pop(sock)
        client_names.pop(sock, None)
        passed_current_item.pop(sock, None)

    if file_obj is not None:
        try:
            file_obj.close()
        except:
            pass

    safe_shutdown_close(sock)


def close_all_clients():
    with clients_lock:
        current_clients = list(clients)

    for sock in current_clients:
        remove_client(sock)


def get_current_item():
    if 0 <= current_item_index < len(items):
        return items[current_item_index]
    return None


def reset_pass_flags():
    with clients_lock:
        for sock in clients:
            passed_current_item[sock] = False


# =========================
# Command Processing
# =========================
def process_view(sock):
    with auction_lock:
        item = get_current_item()
        if item is None:
            send_message(sock, "NO_MORE_ITEMS")
            return

        if auction_active:
            send_message(
                sock,
                f"VIEW ITEM={item['name']} PRICE={current_price} LEADER={current_winner_name}",
            )
        else:
            send_message(sock, "VIEW NO_ACTIVE_AUCTION")


def process_pass(sock):
    with auction_lock:
        if not auction_active:
            send_message(sock, "ERROR NO_ACTIVE_AUCTION")
            return

    with clients_lock:
        if sock not in client_names:
            return
        passed_current_item[sock] = True
        name = client_names.get(sock, "UNKNOWN")

    send_message(sock, "OK PASS")
    broadcast(f"PASS NAME={name}")


def process_bid(sock, parts):
    global current_price, current_winner, current_winner_name
    global auction_time_left, current_tick_seconds

    if len(parts) != 2:
        send_message(sock, "ERROR BID_FORMAT")
        return

    try:
        amount = int(parts[1])
    except:
        send_message(sock, "ERROR BID_FORMAT")
        return

    with clients_lock:
        bidder_name = client_names.get(sock, "UNKNOWN")

    with auction_lock:
        if not auction_active:
            send_message(sock, "ERROR NO_ACTIVE_AUCTION")
            return

        if auction_time_left <= 0:
            send_message(sock, "ERROR NO_ACTIVE_AUCTION")
            return

        min_valid = current_price + MIN_INCREMENT
        if amount < min_valid:
            if amount > current_price:
                current_tick_seconds = LOW_RAISE_TICK_SECONDS
                bid_event.set()
            send_message(sock, f"ERROR BID_TOO_LOW MIN={min_valid}")
            return

        current_price = amount
        current_winner = sock
        current_winner_name = bidder_name
        auction_time_left = AUCTION_DURATION
        current_tick_seconds = BID_TICK_SECONDS

    with clients_lock:
        passed_current_item[sock] = False

    send_message(sock, "OK BID_ACCEPTED")
    broadcast(f"NEW_BID NAME={bidder_name} PRICE={amount}")
    bid_event.set()


def process_exit(sock):
    send_message(sock, "OK EXIT")
    remove_client(sock)


# =========================
# Threads
# =========================
def handle_client(sock, addr):
    try:
        file_obj = sock.makefile("r", encoding="utf-8")

        send_message(sock, "[SERVER] ENTER_NAME")
        name = file_obj.readline()

        if not name:
            remove_client(sock)
            return

        name = name.strip()

        if name == "":
            remove_client(sock)
            return

        with clients_lock:
            client_names[sock] = name
            client_files[sock] = file_obj
            client_active[sock] = True
            passed_current_item[sock] = False

        send_message(sock, f"[SERVER] HELLO NAME={name}")
        log_message(f"[SERVER] CLIENT_REGISTERED NAME={name} ADDR={addr}")

        while not stop_event.is_set():
            line = file_obj.readline()

            if not line:
                break

            message = line.strip()

            if message == "":
                continue

            parts = message.split()
            command = parts[0].upper()

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
                send_message(sock, "ERROR INVALID_COMMAND")

    except:
        pass

    remove_client(sock)


def accept_clients_loop():
    global accepting_clients

    log_message(f"[SERVER] LISTENING {HOST}:{PORT}")

    while accepting_clients and not stop_event.is_set():
        try:
            sock, addr = server_socket.accept()
        except:
            break

        if auction_started:
            send_message(sock, "ERROR AUCTION_ALREADY_STARTED")
            safe_shutdown_close(sock)
            continue

        with clients_lock:
            clients.append(sock)

        t = threading.Thread(target=handle_client, args=(sock, addr), daemon=True)
        t.start()
        client_threads.append(t)

        with clients_lock:
            if len(clients) >= EXPECTED_CLIENTS:
                accepting_clients = False


def auction_loop():
    global auction_started, current_item_index, current_price
    global current_winner, current_winner_name, auction_active
    global auction_time_left, current_tick_seconds

    auction_started = True

    for i, item in enumerate(items):
        with auction_lock:
            current_item_index = i
            current_price = item["base_price"]
            current_winner = None
            current_winner_name = "None"
            auction_active = True
            auction_time_left = AUCTION_DURATION
            if 0 <= i < len(ITEM_TICK_SECONDS):
                current_tick_seconds = ITEM_TICK_SECONDS[i]
            else:
                current_tick_seconds = AUCTION_TICK_SECONDS

        reset_pass_flags()
        bid_event.clear()
        broadcast(f"AUCTION_START ITEM={item['name']} BASE={item['base_price']}")

        while not stop_event.is_set():
            with auction_lock:
                remaining = auction_time_left
                active = auction_active

            if not active or remaining <= 0:
                break

            broadcast(f"TIME_LEFT ITEM={item['name']} SECONDS={remaining}")

            with auction_lock:
                timeout = current_tick_seconds

            bid_event.wait(timeout=timeout)
            if bid_event.is_set():
                bid_event.clear()
                with auction_lock:
                    if current_tick_seconds == LOW_RAISE_TICK_SECONDS and auction_time_left > 0:
                        auction_time_left -= 1
                continue

            with auction_lock:
                if auction_active and auction_time_left > 0:
                    auction_time_left -= 1

        with auction_lock:
            auction_active = False
            auction_time_left = 0
            winner_name = current_winner_name
            final_price = current_price

        if winner_name != "None":
            broadcast(
                f"AUCTION_END ITEM={item['name']} WINNER={winner_name} PRICE={final_price}"
            )
        else:
            broadcast(f"AUCTION_END ITEM={item['name']} WINNER=None PRICE={final_price}")

    broadcast("SERVER_SHUTDOWN")
    stop_event.set()


# =========================
# Start / Shutdown
# =========================
def start_server():
    global server_socket, accept_thread, auction_thread

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    bind_deadline = time.monotonic() + 5
    while True:
        try:
            server_socket.bind((HOST, PORT))
            break
        except OSError:
            if time.monotonic() >= bind_deadline:
                raise
            time.sleep(0.1)

    server_socket.listen()

    accept_thread = threading.Thread(target=accept_clients_loop, daemon=True)
    accept_thread.start()

    while not stop_event.is_set():
        with clients_lock:
            connected_ok = len(clients) >= EXPECTED_CLIENTS
            registered_ok = len(client_names) >= EXPECTED_CLIENTS
            if connected_ok and registered_ok:
                break
        time.sleep(0.1)

    auction_thread = threading.Thread(target=auction_loop, daemon=True)
    auction_thread.start()

    auction_thread.join()

    safe_shutdown_close(server_socket)

    if accept_thread is not None:
        accept_thread.join(timeout=2)

    close_all_clients()

    for t in client_threads:
        t.join(timeout=2)

    log_message("SERVER_CLOSED")
