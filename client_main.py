import sys
import time
from client_functions import start_client, open_log_file, close_log_file


def main():
    log_name = f"client_{int(time.time() * 1000)}.log"

    if len(sys.argv) > 1:
        log_name = sys.argv[1]

    open_log_file(log_name)
    try:
        start_client()
    finally:
        close_log_file()


if __name__ == "__main__":
    main()