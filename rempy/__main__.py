import sys
from rempy import server, client

def print_help():
    print("Run a script/module remotely")
    print("rempy server.com script.py  # to run a python script remotely")
    print("rempy server.com -m foo.bar  # to run a python module remotely")
    print("")
    print("Run a server")
    print("rempy  # To run a server")
    print("")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        server.main()
    elif sys.argv[1] == "config-server":
        server.config()
    elif sys.argv[1] == "config-client":
        client.config()
    else:
        client.main(sys.argv[1:])
