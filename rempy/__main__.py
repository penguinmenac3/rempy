import sys
from rempy import server, client

def print_help():
    print("Run a script/module remotely")
    print("rempy server.com script.py  # to run a python script remotely")
    print("rempy server.com -m foo.bar  # to run a python module remotely")
    print("")
    print("Run a server")
    print("rempy config.json    # To run a server")
    print("")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print_help()
    elif sys.argv[1].endswith(".json"):
        server.main(sys.argv[1:])
    else:
        client.main(sys.argv[1:])
