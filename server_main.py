from server_functions import start_server, open_log_file, close_log_file


def main():
    open_log_file("server.log")
    try:
        start_server()
    finally:
        close_log_file()


if __name__ == "__main__":
    main()