import sys
import doc_processing
import document_similarity
from classification import *
from flask import request, jsonify
import configparser
import logging.config
from flask import Flask
import sys
import logging.config
import os
from flask import Flask
import requests as req
from loguru import logger

config = configparser.ConfigParser()
config.read('config.ini')
#print("config:", config)
log_location = config['CLASSIFIER']['LOGGER_LOC']
log_name = os.path.normpath(os.path.join(log_location,"classifier_log.log"))
loginfo_filename = config['CLASSIFIER']['LOGINFO_FILENAME']
logdebug_filename = config['CLASSIFIER']['LOGDEBUG_FILENAME']

logger.add(loginfo_filename, format="{time:YYYY-MM-DD at HH:mm:ss} | {level} | {message}", backtrace=True ,  level='INFO' , rotation="00:00", compression="zip",enqueue=True ,diagnose=True  )
logger.add(logdebug_filename, format="{time:YYYY-MM-DD at HH:mm:ss} | {level} | {message}", backtrace=True ,  level='DEBUG' , rotation="00:00", compression="zip",enqueue=True ,diagnose=True  )


logger.info("Classifier:", config['CLASSIFIER'])
port = config['CLASSIFIER']['TRAINING_PORT']
host = config['CLASSIFIER']['CLASSIFICATION_API_HOST']
doc_similarity_api = config['CLASSIFIER']['DOC_SIMILARITY_API']


app = Flask(__name__)

from nltk.stem.snowball import SnowballStemmer

stemmer = SnowballStemmer("english")

'''
def tokenize_stem(text):
    import nltk
    import re
    print("\n\n tokenize_stem :")
    tokens = [word for sent in nltk.sent_tokenize(text) for word in nltk.word_tokenize(sent)]
    filtered_tokens = []
    # filter out any tokens not containing letters (e.g., numeric tokens, raw punctuation)
    for token in tokens:
        if re.search('[a-zA-Z]', token):
            filtered_tokens.append(token)
    stems = [stemmer.stem(t) for t in filtered_tokens]
    return stems
'''

@app.route('/classifier', methods=['POST'])
def classifier():
    data = request.get_json(force=True)
   # logger.info(" classifier JSON:",data)
    filename = data['file_name']
    disc_inbound_id = data['inbound_id']
    details = classification(filename, disc_inbound_id)
    #logger.info("\n classifier :", details)
    return jsonify(details)


if __name__ == '__main__':
     app.run(host='0.0.0.0' , port=3535)
     #app.run(host='0.0.0.0' , port=3535, debug=True)
     #app.run(host=host, port=port, debug=True)
