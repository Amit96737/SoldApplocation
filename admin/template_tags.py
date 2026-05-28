import json, ast
from datetime import datetime


def item_image_format(value: str):
    return json.loads(value)[0]


def list_to_str(value):
    return ", ".join(json.loads(value))


def subscription_status(value):
    if value > datetime.utcnow():
        return True
    return False


def str_list_to_list(string_list):
    return ast.literal_eval(string_list)

