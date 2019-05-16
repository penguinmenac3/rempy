from time import sleep
import sys


print("Hello World!")
print(sys.argv[1:])

N = 10000
for i in range(N):
    print("\rWaiting for: {}    ".format(N-i), end="")
    sleep(0.01)
print()

import tensorflow as tf
print(tf.__version__)
