import random
import string


def generate_affiliate_code(length=6):
    chars = string.ascii_letters + string.digits
    return ''.join(random.choices(chars.upper(), k=length))

