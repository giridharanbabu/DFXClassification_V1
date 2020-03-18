import pandas as pd
import requests as reql
import pickle
from flask import Flask
import doc_processing
from  unclassified_grouping import find_group
from document_similarity import *
from data_extractor import *
# from discovery_connector import call_classification
from loguru import logger
import re
import os
import nltk
import configparser
import classifier_transactions
from loguru import logger
import error_updation
from error_updation import *
import datetime
from datetime import timedelta
import os
import os.path
import shutil
from dbprocess import dbprocess
from build_models import unclassified_doc_update
from build_models import  classified_doc_update
from elasticsearch import Elasticsearch
from elasticsearch.connection import create_ssl_context
import ssl
from elastic_update import update_group_es


config = configparser.ConfigParser()
config.read('config.ini')
app = Flask(__name__)

#logger.add(loginfo_filename, format="{time:YYYY-MM-DD at HH:mm:ss} | {level} | {message}", backtrace=True,
#           level='DEBUG', rotation="1 week", compression="zip", enqueue=True)

path_separator = config['CLASSIFIER']['PATH_SEP']
temp_directory = config['CLASSIFIER']['TEMP_DIR_LOC']
classification_model_accuracy = config['CLASSIFIER']['CLASSIFICATION_FINAL_ACCURACY']
similiarity_accuracy = config['CLASSIFIER']['DOC_SIMILIARITY_ACCURACY']
root_dir = config['CLASSIFIER']['TRAINING_DATASET_LOCATION']
extraction_loc = config['CLASSIFIER']['CLASSIFIED_METADATA']
max_file_size = int(config['CLASSIFIER']['SOURCE_FILE_SIZE_MAXBYTE'])
min_file_size= int(config['CLASSIFIER']['SOURCE_FILE_SIZE_MINBYTE'])
model_location = config['CLASSIFIER']['MODEL_SAVE_LOCATION']
class_predicted_loc = config['CLASSIFIER']['CLASSIFIED_RESULT']
class_error_loc = config['CLASSIFIER']['CLASSIFIED_ERROR']
sim_template_loc = config['CLASSIFIER']['SIM_TEMPLATE_GROUP']

vector_model_pkl = config['CLASSIFIER']['VEC_MODEL_PKL_NAME']
class_model_pkl = config['CLASSIFIER']['CLASS_PKL_NAME']
is_model_enabled = False
log_level = config['CLASSIFIER']['LOG_LEVEL']
log_location = config['CLASSIFIER']['LOGGER_LOC']
log_name = os.path.normpath(os.path.join(log_location, "classifier_log.log"))
loginfo_filename = config['CLASSIFIER']['LOGINFO_FILENAME']
logdebug_filename = config['CLASSIFIER']['LOGDEBUG_FILENAME']
error_code=config['CLASSIFIER']['CLASSIFIER_ERROR_CODE']
write_file_system =  config['CLASSIFIER']['FILE_OUT']
ocr_store_full_text = int(config['CLASSIFIER']['OCR_STORE_FULL_TEXT'])

model_path = os.path.normpath(os.path.join(model_location, class_model_pkl))
vec_model_path = os.path.normpath(os.path.join(model_location, vector_model_pkl))
es_host = config['CLASSIFIER']['ES_HOST']
es_port = config['CLASSIFIER']['ES_PORT']
index = config['CLASSIFIER']['INDEX']


ssl_context = create_ssl_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE
es = Elasticsearch([{'host': es_host, 'port': es_port}],scheme="https",
                       # to ensure that it does not use the default value `True`
                       verify_certs=False,
                       ssl_context= ssl_context,
                       http_auth=("admin", "admin"))

dt = str(datetime.datetime.now()).replace(":","_")
newname = 'classifier_loginfor.log'+'.zip'+dt+'.zip'
newname_debug = 'classifier_logdebug.log'+'.zip' +dt+ '.zip'
if os.path.exists('classifier_loginfor.log' +'.zip'):
  os.rename('classifier_loginfor.log' +'.zip', newname)
  shutil.move(newname,log_location )
if os.path.exists('classifier_logdebug.log' +'.zip'):
  os.rename('classifier_logdebug.log' +'.zip', newname_debug)
  shutil.move(newname_debug,log_location )
logger.add('classifier_loginfor.log' , format="{time} {message} | {level} | {message}", backtrace=True, level='INFO', rotation="1 day", enqueue=True, compression="zip")
logger.add('classifier_logdebug.log' , format="{time} {message} | {level} | {message}", backtrace=True, level='DEBUG', rotation="1 day", enqueue=True, compression="zip")


def remove_stop_words(text):
    import spacy
    from spacy.lang.en import English
    from spacy.lang.en.stop_words import STOP_WORDS
    nlp = English()
    #  "nlp" Object is used to create documents with linguistic annotations.
    document = nlp(text)
    # Create list of word tokens
    token_list = []
    for token in document:
        token_list.append(token.text)

    # Create list of word tokens after removing stopwords
    filtered_sentence = []
    for word in token_list:
        lexeme = nlp.vocab[word]
        if lexeme.is_stop == False:
            filtered_sentence.append(word)
    return ' '.join(filtered_sentence)

templates = []
for name in os.listdir(root_dir):
    templates.append(name)
logger.info("\n\n templates  : {}", templates)


from sklearn import preprocessing
le = preprocessing.LabelEncoder()
le.fit(templates)
template_id = le.transform(le.classes_)
categorydf = pd.DataFrame({'template_id': template_id, 'templates': templates})
categorydf = categorydf.sort_values('template_id')
id_to_category = dict(categorydf[['template_id', 'templates']].values)
logger.info(" \n\n id_to_category : {}", id_to_category)


unclassified_dict = {}
prediction_json = {}


def tokenize_stem(text):
    from nltk.stem.snowball import SnowballStemmer
    stemmer = SnowballStemmer("english")
    logger.info("\n\n tokenize_stem : {}")
    tokens = [word for sent in nltk.sent_tokenize(text) for word in nltk.word_tokenize(sent)]
    filtered_tokens = []
    # filter out any tokens not containing letters (e.g., numeric tokens, raw punctuation)
    for token in tokens:
        if re.search('[a-zA-Z]', token):
            filtered_tokens.append(token)
    stems = [stemmer.stem(t) for t in filtered_tokens]
    return stems


def file_validation(file_name,file_size):
    is_valid = False
    logger.info(" file_validation : {}", file_name)
    print(" file_name :",file_name)
    print(" File Size :",file_size)
    if os.path.exists(file_name) and os.access(file_name,os.R_OK) and (min_file_size <= file_size ) and (max_file_size >= file_size) :
        is_valid = True
        logger.info(" file_validation : {}",file_validation)
    print("file_validation ->",is_valid)
    return is_valid


def get_file_name(file_path):
    filename = ''
    if len(file_path) > 1:
         filename = os.path.splitext(os.path.basename(file_path))[0]
    return str(filename)


def add_unclassified_docs(group_details,disc_inbound_id,org_filename,is_training,auth_key):
    unclassified_dict = {}
    try:
        if group_details['error_code'] == 0 and group_details['group_no'] is not None and int(group_details['group_no']) > 0 :
            prediction_json["group_no"] = group_details['group_no']
            prediction_json["unclassified_file_name"] = group_details['unclassified_file_name']
            unclassified_dict['DiscoveryInBoundId'] = disc_inbound_id
            unclassified_dict['ClassificationGroupId'] = int(group_details['group_no'])
            unclassified_dict['FileLocation'] =  group_details['file_name']
            logger.info("\n\n\n **************** class :group_details : {} ", group_details['file_name'])
            unclassified_dict['Name'] =  org_filename
            unclassified_dict['DisplayName'] =  org_filename
            unclassified_dict['IsTemplate'] = group_details['new_group']
            unclassified_dict['IsTrainingDocument'] = is_training
            #classifier_transactions.add_unclassified_doc_info(unclassified_dict,auth_key)
        else:
            prediction_json["error_msg"] = group_details['error_msg']
            prediction_json["error_code"] = group_details['error_code']
            #classifier_transactions.update_inbound_status(disc_inbound_id,auth_key)
    except Exception as error:
        print(error)
        #classifier_transactions.update_inbound_status(disc_inbound_id)
        #error_updation.exception_log(error, " Error occurred when adding unclassified details ", str(disc_inbound_id))


@app.route('/'+config['CLASSIFIER']['CLASSIFIER_URL_NAME'], methods=['POST'])
def classifier():
    from flask import jsonify,request
    dfx_data = request.get_json(force=True)
    logger.info(" classifier JSON: {}",type(dfx_data))
    # filename = data['file_name']
    # disc_inbound_id = data['inbound_id']
    # is_training_source = data['IsTrainingSource']
    # is_unclassified = data['is_unclassified']
    details = classification(dfx_data)
    logger.info("\n classifier :{}", details)
    return jsonify(details)


# def classification(dfx_data):
#     import gc
#     try:
#         prediction_json['error_code'] = 0
#         prediction_json["error_msg"] = ''
#         filename = dfx_data['file_name']
#         prediction_json['disc_inbound_id'] = dfx_data['inbound_id']
#         auth_key = dfx_data['Authorization']
#         is_training_source = 0
#         if dfx_data['FileLength'] is not None and type(dfx_data['FileLength']) is not int:
#             file_size = int(dfx_data['FileLength'])
#         else:
#             file_size = dfx_data['FileLength']
#         disc_inbound_id = dfx_data['inbound_id']
#         if dfx_data['IsTrainingSource'] is not None and type(dfx_data['IsTrainingSource']) is not int:
#             is_training_source = int(dfx_data['IsTrainingSource'])
#         is_unclassified = dfx_data['is_unclassified']
#         data_processing = {}
#         if file_validation(filename,file_size) and int(disc_inbound_id) > 0 :
#             if int(is_unclassified) == 1:
#                 data_processing['text_file_name'] = filename
#                 data_processing['error_code'] = 0
#             else:
#                 data_processing = doc_processing.filter_text_from_file(filename,disc_inbound_id,auth_key)
#                 logger.info("\n\n\n data_processing: {}", data_processing)
#             if int(data_processing['error_code']) is not 2 and data_processing['text_file_name'] is not None and data_processing['text_file_name'].strip() is not '' and int(data_processing['error_code']) == 0 and  len(data_processing['text_file_name'].strip()) > 1 :
#                 txt_filename = data_processing['text_file_name']
#                 text_extraction = ''
#                 logger.info(" \n Classification: txt_filename {}",txt_filename)
#                 with open(txt_filename, 'rb') as text_file:
#                     #text_extraction = text_file.read()
#                     text_raw = ''+(text_file.read()).decode()
#                     # logger.info(text_raw)
#                     text_extraction = remove_stop_words(text_raw)
#                     # logger.info(text_extraction)
#                 if os.path.exists(vec_model_path) and os.path.exists(model_path):
#                     global is_model_enabled
#                     is_model_enabled = True
#                 logger.info("\n\n  is_model_enabled : {}",is_model_enabled)
#                 if len(filename.strip()) > 1 and text_extraction is not None and len(text_extraction.strip()) > 0  and is_model_enabled :
#                     logger.info(" Prediction  Section : ******************** \n")
#                     features_list=vectorizer_model.transform([text_extraction])  # .toarray()
#                     prediction=classifier_model.predict(features_list)
#                     prediction_id = int(prediction)
#                     logger.debug("\n\n prediction : {}", prediction_id)
#                     proba_pred=classifier_model.predict_proba(features_list)
#                     new_doc_classifier=proba_pred[:, prediction_id]
#                     logger.info("\n\n new_doc_classifier: {}", new_doc_classifier, float(classification_model_accuracy), float(new_doc_classifier))
#                     if is_training_source == 0 and float(new_doc_classifier) >= float(classification_model_accuracy):
#                         class_dict = {}
#                         class_id = 0
#                         logger.info("Prediction : {}", prediction_id)
#                         logger.info("Prediction Probability :{}", proba_pred[:, prediction_id])
#                         prediction_json["file_name"] = filename
#                         prediction_json["predition_type"] = new_doc_classifier
#                         class_name = id_to_category.get(int(prediction_id))
#                         org_subclass_id = classifier_transactions.find_subclassification_id(class_name,auth_key)
#                         logger.info("\n\n class_name : {}", class_name)
#                         prediction_json['predicted_category'] = class_name
#                         class_dict["ClassificationTemplateId"] = classifier_transactions.find_classification_id(org_subclass_id,auth_key)
#                         class_dict["SubClassificationTemplateId"] = org_subclass_id
#                         class_dict["Type"] = class_name
#                         class_dict["DiscoveryInBoundId"] = int(disc_inbound_id)
#                         # predicted_dir_name = os.path.normpath(os.path.join(class_predicted_loc,class_name))
#                         # if not os.path.exists(predicted_dir_name):
#                         #     os.makedirs(predicted_dir_name, mode=0o777, exist_ok=False)
#                         # logger.info("predicted_file_name:{}",predicted_dir_name)
#                         class_id = classifier_transactions.save_classified_result(class_dict,txt_filename,auth_key)
#                         logger.info("\n\n **************** class_id : {}", class_id)
#                         if is_unclassified is not None and  int(is_unclassified) == 1:
#                             classifier_transactions.update_unclassified_status(dfx_data['unclass_id'],auth_key)
#                             if os.path.exists(txt_filename):
#                                 os.remove(txt_filename)
#                                 dir_name = os.path.split(txt_filename)[0]
#                                 temp_file_name =  os.path.split(txt_filename)[1]
#                                 template_loc = os.path.normpath(os.path.join(sim_template_loc ,os.path.split(dir_name)[1]))
#                                 print( "\n dir_name:",dir_name,"\n temp_file_name: ",temp_file_name,"\n template_loc" , template_loc )
#                                 if os.path.exists(template_loc) and os.path.isdir(template_loc) and len(
#                                     os.listdir(dir_name)) == 0:
#                                     # os.remove(os.path.normpath(os.path.join(template_loc, temp_file_name)))
#                                     os.system("rm -rf "+template_loc)
#                                     import shutil
#                                     shutil.rmtree(dir_name)
#                         import shutil
#                         if os.path.exists(txt_filename):
#                             os.remove(txt_filename)
#                     elif is_training_source == 1 and float(new_doc_classifier) >= float(classification_model_accuracy):
#                         if os.path.exists(txt_filename):
#                             os.remove(txt_filename)
#                         prediction_json["error_msg"] = " The document is marked for training "
#                         prediction_json['error_code'] = 1
#                         classifier_transactions.update_inbound_status(disc_inbound_id,auth_key)
#                         error_updation.custom_error_update_log(" Duplicate training document ", " Duplicate training document ",
#                                                                str(disc_inbound_id))
#                     elif int(is_unclassified) is not 1:
#                         group_details = find_group(txt_filename,auth_key)
#                         add_unclassified_docs(group_details, disc_inbound_id,get_file_name(filename), is_training_source,auth_key)
#                 elif len(filename.strip()) > 1 and text_extraction is not None and len(text_extraction.strip()) > 1 and not is_model_enabled:
#                     group_details = find_group(txt_filename,auth_key)
#                     add_unclassified_docs(group_details, disc_inbound_id, get_file_name(filename), is_training_source,auth_key)
#             else:
#                 prediction_json["error_msg"] = data_processing['error_msg']
#                 prediction_json['error_code'] = int(data_processing['error_code'])
#                 classifier_transactions.update_inbound_status(disc_inbound_id,auth_key)
#                 logger.info(" prediction_json: {}", prediction_json)
#                 error_updation.custom_error_update_log(data_processing['error_msg'],
#                                                         data_processing['error_msg'],
#                                                        str(disc_inbound_id))
#         else:
#             prediction_json["error_msg"] = " Kindly check the document's path/read permission/size "
#             prediction_json['error_code'] = 1
#             classifier_transactions.update_inbound_status(disc_inbound_id,auth_key)
#             error_updation.custom_error_update_log(" Kindly check the document's path/permission/size ", " Kindly check the document's path/permission/size ", str(disc_inbound_id))
#             logger.debug(prediction_json)
#             logger.info("\n\n prediction_json {}", prediction_json)
#     except Exception as exception:
#         classifier_transactions.update_inbound_status(disc_inbound_id,auth_key)
#         error_updation.exception_log(exception, prediction_json, str(disc_inbound_id))
#         # prediction_json['error_code'] = 1
#         logger.debug("\n\n exception: {}", exception)
#         prediction_json["error_msg"] = " Document Exception : "+str(exception)
#     return json.dumps(str(prediction_json))
#     # tagging the text files

def eliminating_classified():
    return {
    "size": 5000,
    "query": {
        "bool": {
            "filter": {
                "wildcard": {
                    "content": "*"
                }
            },

            "must_not": [
                {"exists": {"field": "classified"}},
                {"exists": {"field": "group_no"}}
            ]
        }
    }
}





def classification(auth_key):
    import gc
    #try:
    data_processing = {}
    #disc_inbound_id = dfx_data['inbound_id']
    filter_classified = es.search(index=index, body=eliminating_classified())
    raw_data = filter_classified['hits']['hits']
    for data in raw_data:
        es_id = data['_id']#urllib.parse.quote(data['_id'], safe='')
        print(es_id)
        inbound_id=data['_source']['resourceName']
        content = data['_source']['content']
        uri= data['_source']['uri']
        data_processing = doc_processing.filter_text_from_file(inbound_id,content,'auth_key')
        logger.info("\n\n\n data_processing: {}", data_processing)
        txt_filename = data_processing['text_file_name']
        text_extraction = ''
        logger.info(" \n Classification: txt_filename {}",txt_filename)

        if os.path.exists(vec_model_path) and os.path.exists(model_path):
            global is_model_enabled
            is_model_enabled = True
            logger.info("\n\n  is_model_enabled : {}",is_model_enabled)
            with open(txt_filename, 'rb+') as text_file:
                # text_extraction = text_file.read()
                text_raw = '' + (text_file.read()).decode()
                # logger.info(text_raw)
                text_extraction = remove_stop_words(text_raw)
                # logger.info(text_extraction)
            if text_extraction is not None and len(text_extraction.strip()) > 0  and is_model_enabled :
                logger.info(" Prediction  Section : ******************** \n")
                features_list=vectorizer_model.transform([text_extraction])  # .toarray()
                prediction=classifier_model.predict(features_list)
                prediction_id = int(prediction)
                logger.debug("\n\n prediction : {}", prediction_id)
                proba_pred=classifier_model.predict_proba(features_list)
                new_doc_classifier=proba_pred[:, prediction_id]
                logger.info("\n\n new_doc_classifier: {}", new_doc_classifier, float(classification_model_accuracy), float(new_doc_classifier))
                if float(new_doc_classifier) >= float(classification_model_accuracy):
                    class_dict = {}
                    class_id = 0
                    logger.info("Prediction : {}", prediction_id)
                    logger.info("Prediction Probability :{}", proba_pred[:, prediction_id])
                    prediction_json["file_name"] = inbound_id
                    prediction_json["predition_type"] = new_doc_classifier
                    class_name = id_to_category.get(int(prediction_id))
                    #org_subclass_id = classifier_transactions.find_subclassification_id(class_name,auth_key)
                    logger.info("\n\n class_name : {}", class_name)
                    prediction_json['predicted_category'] = class_name
                    classified_doc_update(class_name,prediction_json["predition_type"][0],content,uri)

                    # class_dict["ClassificationTemplateId"] = classifier_transactions.find_classification_id(org_subclass_id,auth_key)
                    # class_dict["SubClassificationTemplateId"] = org_subclass_id
                    # class_dict["Type"] = class_name
                    # class_dict["DiscoveryInBoundId"] = int(inbound_id)

                    #--class_id = classifier_transactions.save_classified_result(class_dict,txt_filename,auth_key)
                    #--logger.info("\n\n **************** class_id : {}", class_id)
#                         if is_unclassified is not None and  int(is_unclassified) == 1:
#                             classifier_transactions.update_unclassified_status(dfx_data['unclass_id'],auth_key)
                else:
                    group_details = find_group(txt_filename, auth_key)

                    unclassified_doc_update(uri, str(group_details['accuracy_rate']),content,str(group_details['group_no']),str(group_details['group_file_path']),str(group_details['doc_name']))
                    elastic_update = update_group_es(es_id, str(group_details['group_no']))



        else:
            group_details = find_group(txt_filename,auth_key)
            print(group_details)
            unclassified_doc_update(uri, str(group_details['accuracy_rate']), content, str(group_details['group_no']),str(group_details['group_file_path']),str(group_details['doc_name']))
            elastic_update = update_group_es(es_id, str(group_details['group_no']))

            #print(unclassified_doc_update(uri,))
                #add_unclassified_docs(group_details, inbound_id, get_file_name(txt_filename), "0",auth_key)

           
        
    # except Exception as exception:
    #     #classifier_transactions.update_inbound_status(disc_inbound_id,auth_key)
    #     #error_updation.exception_log(exception, prediction_json, str(disc_inbound_id))
    #     # prediction_json['error_code'] = 1
    #     logger.debug("\n\n exception: {}", exception)
        #prediction_json["error_msg"] = " Document Exception : "+str(exception)
    return json.dumps(str(prediction_json))


if __name__ == '__main__':
    if os.path.exists(vec_model_path) and os.path.exists(model_path):
        logger.info("{} \n\n\n")
        from pyfiglet import Figlet
        f = Figlet(font='slant')
        logger.info("{}", f.renderText('DFX CLASSIFIER ') + "v 0.1")
        with open(model_path, 'rb') as model_file:
            classifier_model = pickle.load(model_file)
        with open(vec_model_path, 'rb') as vec_model:
            vectorizer_model = pickle.load(vec_model)
        is_model_enabled = True
    logger.info(" \n\n classification :-> is_model_enabled : {}", int(is_model_enabled))
    #classifier_api = os.path.normpath(os.path.join(config['CLASSIFIER']['CLASSIFIER_HOST'], config['CLASSIFIER']['CLASSIFIER_URL_NAME']))
    # print(classification(r'\\192.168.0.14\Users\giri\Desktop\Credit_Card_Agreements_2018_Q3\1st Financial Bank USA\MasterCard or Visa Credit Card Agreement.pdf',9))
    # payload = {}
    # payload['file_name'] = r'C:\Users\baskaran\Desktop\Milton.pdf'
    # payload['unclass_id'] = 0
    # payload['inbound_id'] = 354
    # payload['IsTrainingSource'] = 0
    # payload['is_unclassified'] = 0
    # payload['FileLength'] = 24546
    # payload['Authorization'] = 'bearer PJZ45ervujGYDWxe0lxRzDPG0fORLHfbaSYHEgDnpUBKF-ueDNlKIWZoNpHUWzNLHVeR5pjcVyRuQpAOn4Ae759UQxT5sH1eshjjR13REREOdr7TfuOXCQhUTFhNUqf8iJChuJjZbXdNYqEnqFX6osHv5YBJbyer5IoiquNOkejk-TQplGJd0gL1_AoT19k_TDpqijaCsZtoHrYRt2ORNaWebl0cdd9pi7jWdYLX6vHnA3c1nxjEQsVjHAxkGIDPGKKYVQPaoXtsDcw6Uk0ypN4siyzdcPj2hWOX7TUWNsI'
    # print(classification(payload))
    # {"file_name": "\\\\WIN-EN47KDFIU2V\\CRMFiles\\fsfdfsdfK.docx", "unclass_id": 0, "inbound_id": 265,
    #  "IsTrainingSource": 0, "is_unclassified": 0,
    #  "Authorization": "bearer 6aAHmqDL4XmXLXAX6lbqhQSTVGR15n8pSaMFIcHn9V0GRhGHHnX4NOf6oSZRHdL9hkjR3U21O6RD8fzRafZIuQpvayXq_hq3qkYrCprUxgbNSj-b9_atmSVzmQlMCqkARfmmxabZqMCP6qKaWM5HyncQvps5SDi9yExt4jGE5qZaRT3DicWlPq1LEdaHKrfAUDX5yNL-PYJyiTmHFiAw-8wUgk0GxvoAGRnhPMTrZo3ZE2nMlDT5SDaJDc40YIMZ9EvgzziV0nj_kWYn5eMezKgcWCbgjfxNpTUEXpZo8lA",
    #  "FileLength": null}
    # {"file_name": "\\\\WIN-EN47KDFIU2V\\CRMFiles\\9PYMPC_tic.pdf", "unclass_id": 0, "inbound_id": 207,
    #  "IsTrainingSource": 0, "is_unclassified": 0,
    #  "Authorization": "bearer PJZ45ervujGYDWxe0lxRzDPG0fORLHfbaSYHEgDnpUBKF-ueDNlKIWZoNpHUWzNLHVeR5pjcVyRuQpAOn4Ae759UQxT5sH1eshjjR13REREOdr7TfuOXCQhUTFhNUqf8iJChuJjZbXdNYqEnqFX6osHv5YBJbyer5IoiquNOkejk-TQplGJd0gL1_AoT19k_TDpqijaCsZtoHrYRt2ORNaWebl0cdd9pi7jWdYLX6vHnA3c1nxjEQsVjHAxkGIDPGKKYVQPaoXtsDcw6Uk0ypN4siyzdcPj2hWOX7TUWNsI"}
    # {"file_name": "\\\\192.168.0.14\\dfx\\crm_tmp\\2~~d87a4763-8b07-ea11-b806-00155d00090f~~8M1XMA_tic.pdf",
    #  "unclass_id": 0, "inbound_id": 1, "IsTrainingSource": 0, "is_unclassified": 0,
    #  "Authorization": "bearer 9jYF-wEagkECw_DX75Y80W69TT3m6YQGqQNST4XHhaxb3uiUYTlAYxJnrddmLVB3YXl4p-zPK_KecjmVX3LAZEd0gvbpcILM4ItbYyCwe8dB3Huj8qScXsFpH_ccUAOZydigKLxKR_Px4OICZKGsbxQYQOEhHdDGuDMPxybNDksFNp1L7PrBSWAzs18AmfUDE7RDiHCRDmdkBihJHLPU_AdqAwfJy5Oj2dahFGZVhfcoIb7u-7dr0ok-u5dymJlziEc40M3A9hTYHS4bj9wkAfCuJX7iDx550RW20hh2dZI"}
    #app.run(host=config['CLASSIFIER']['CLASSIFIER_HOST'], port=config['CLASSIFIER']['API_PORT_NUMBER'], debug=False, threaded = True)
    classification("auth_key")

