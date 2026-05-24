import os
import server_functions
from server_functions import start_server, open_log_file, close_log_file


def main():
    server_functions.AUCTION_DURATION = int(os.environ.get("AUCTION_DURATION", 20))
    server_functions.EXPECTED_CLIENTS = int(os.environ.get("EXPECTED_CLIENTS", 3))

    open_log_file("server.log")
    try:
        start_server()
    finally:
        close_log_file()


if __name__ == "__main__":
    main()