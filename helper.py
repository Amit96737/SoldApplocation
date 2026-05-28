from datetime import timedelta, datetime

import jwt

from constants import ACCESS_TOKEN_EXPIRE_MINUTES, SECRET_KEY, ALGORITHM


def create_access_token(email_address: str):
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    data = {"sub": email_address}
    to_encode = data.copy()
    expire = datetime.utcnow() + access_token_expires
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def replace_first(text, old_substring, new_substring):
    # Find the first occurrence of the old substring
    index = text.find(old_substring)
    if index == -1:
        return text  # Return the original text if the substring is not found

    # Replace the first occurrence
    return text[:index] + new_substring + text[index + len(old_substring):]


def calculate_average(numbers):
    if not numbers:
        return 0  # Return 0 if the list is empty to avoid division by zero.

    total = sum(numbers)
    average = total / len(numbers)
    return round(average, 1)


def getOnlineStatus(last_seen: datetime):
    return last_seen + timedelta(minutes=5) > datetime.utcnow()
