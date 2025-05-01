import string
import random


def generate_nonce():
    return "".join(random.choices(string.ascii_letters + string.digits, k=16))
