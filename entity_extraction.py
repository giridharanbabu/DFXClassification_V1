import spacy
from flask import Flask
from flask import jsonify
from flask import request
import json
import re
from nltk.tokenize.treebank import TreebankWordDetokenizer as Detok
import configparser
from loguru import logger

import error_updation
from error_updation import *
import re

# config = configparser.ConfigParser()
# config.read('config.ini')
# logger.info("Config:", config)



def multiwordReplace(text, wordDic):
    """
    take a text and replace words that match a key in a dictionary with
    the associated value, return the changed text
    """
    rc = re.compile('|'.join(map(re.escape, wordDic)))

    def translate(match):
        return wordDic[match.group(0)]

    return rc.sub(translate, text)


def spacy_entity_extraction(content):
    try:
        from nltk import word_tokenize
        import spacy
        nlp = spacy.load('en_core_web_md')
        capitalized_text = []
        tokenized_words = word_tokenize(content)
        for text in tokenized_words:
            capitalize_first_char = text.capitalize()
            capitalized_text.append(capitalize_first_char)
        detokenizer = Detok()
        detokenized_text = detokenizer.detokenize(capitalized_text)
        #remove_cardinal = re.sub(r'[0-9]+', '', detokenized_text)
        nlp_document = nlp(detokenized_text)
        str_replace_dict = {}
        if len(nlp_document.ents) == 0:
            str2 = detokenized_text
        else:
            for entities in nlp_document.ents:
                extracted_entities = {entities.label_}
                if 'CARDINAL' not in extracted_entities:
                    extracted_text = {entities.text}
                    #print(extracted_text)
                   #print(extracted_text)
                    for key in extracted_text:
                        str_replace_dict[key] = "<span class='imp'>" + key + '</span>'
            str2 = multiwordReplace(detokenized_text, str_replace_dict)
        return str2
    except Exception as e:
        error_updation.exception_log(e, "Error in entities_extraction :", str('') )
        #logger.info(" Error in entities_extraction :", e)

#
# app = Flask(__name__)
# @app.route('/entity_extraction', methods=['POST'])


def entity_extraction():
    entities_extracted_in_json = []
    json_text = json.dumps(request.json)
    json_text = json.loads(json_text)
    text_document = json_text['path']
    with open(text_document, 'r', encoding='utf-8') as file_read:
        file_read = file_read.read()
        # print(file_read)
    extracted_entity = (spacy_entity_extraction(file_read))
    logger.debug("entities extracted are: {}", extracted_entity)

    return extracted_entity


# if __name__ == '__main__':
#     print(spacy_entity_extraction(r"C:\Users\admin\Desktop\dataset\driving_licence\Sample-Driving-licence117.txt"))
# #     # app.run(port=config['CLASSIFIER']['API_PORT_NUMBER'], threaded=True)

