import json


# def get_lang_content(language: str):
#     if language == 'en':
#         with open("./I18n/en.json", "r") as en_file:
#             en_data = json.load(en_file)
#         return en_data
#     elif language == 'he':
#         with open("./I18n/he.json", "r") as he_file:
#             he_file = json.load(he_file)
#         return he_file
#
#     elif language == 'fr':
#         with open("./I18n/fr.json", "r") as fr_file:
#             fr_file = json.load(fr_file)
#         return fr_file
#     else:
#         with open("./I18n/en.json", "r") as en_file:
#             en_data = json.load(en_file)
#         return en_data

def get_lang_content(language: str):

    if language == 'en':
        with open(r"./I18n/en.json", "r", encoding="utf-8") as en_file:
            en_data = json.load(en_file)
        return en_data
    elif language == 'he':
        with open(r"./I18n/he.json", "r", encoding="utf-8") as he_file:
            he_file = json.load(he_file)
        return he_file
    elif language == 'fr':
        with open(r"./I18n/fr.json", "r", encoding="utf-8") as fr_file:
            fr_file = json.load(fr_file)
        return fr_file
    else:
        with open(r"./I18n/en.json", "r", encoding="utf-8") as en_file:
            en_data = json.load(en_file)
        return en_data


