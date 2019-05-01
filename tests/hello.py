from time import sleep
import sys


print("Hello World!")
print(sys.argv[1:])

N = 100
for i in range(N):
    print("\rWaiting for: {}    ".format(N-i), end="")
    sleep(1)
print()

import tensorflow as tf
print(tf.__version__)
