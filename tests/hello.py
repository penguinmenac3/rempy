import time

print("Hello World!")
print()
print("If you run this via:")
print("  rempy tests/hello.py@workstation:/home/$USER/Testing")
print("this is a remotely executed process.")

print("Waiting 20 seconds")
for i in range(20):
    print(i)
    time.sleep(1)
print()
print("Done.")
