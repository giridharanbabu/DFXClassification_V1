# -*- coding: utf-8 -*-
"""
Created on Tue Jun  4 15:58:57 2019

@author: baskaran
"""

import os
import json
from time import gmtime, strftime
import urllib3
import requests as reql
import gensim.models as gsm
from os import listdir
from os.path import join
from gensim.models.doc2vec import TaggedDocument
import re
import nltk
from nltk.stem.porter import PorterStemmer
from nltk.corpus import stopwords
import configparser
import logging
import logging.config
from flask import Flask
from loguru import logger
from flask_restful import reqparse, abort, Api, Resource
from flask import json

app = Flask(__name__)
# api = Api(app)

# config = configparser.ConfigParser()
# config.read('loconfig.ini')
# logging.config.fileConfig('loconfig.ini')
# logger = logging.getLogger("sLogger")


config = configparser.ConfigParser()
config.read('config.ini')
logger.info("Config:", config)

get_file_info_request = config['CLASSIFIER']['GET_INBOUND_FILE_LIST']
get_template_request = config['CLASSIFIER']['GET_CLASSIFICATION_TEMPLATE']
tmpl_request_url = config['CLASSIFIER']['TEMPLATE_REQUEST']
class_save_url = config['CLASSIFIER']['CLASSIFICATION_SAVE']
new_unclass_templ_add = config['CLASSIFIER']['ADD_UNCALSSIFICATION_FILE']
get_unclassified_id_request = config['CLASSIFIER']['GET_UNCLASSIFIED_INFO_BY_INBID']
unclassified_templ_add = config['CLASSIFIER']['ADD_UNCLASSIFIED']
unclassified_templ_update = config['CLASSIFIER']['UPDATE_UNCLASSIFIED_TEMPLATE']
get_group_count_request = config['CLASSIFIER']['GET_CLASSIFIED_GROUP_COUNT']
add_group_templ = config['CLASSIFIER']['ADD_GROUP_TEMPLATE']

temp_directory = config['CLASSIFIER']['TEMP_DIR_LOC']
train_corpus = config['CLASSIFIER']['TRAIN_CORPUS_LOC']
gsm_model_file_location = config['CLASSIFIER']['GSM_MODEL_LOC']
gsm_model_name = config['CLASSIFIER']['GSM_MODEL_NAME']
classification_model_accuracy = config['CLASSIFIER']['CLASSIFICATION_FINAL_ACCURACY']
similiarity_accuracy = config['CLASSIFIER']['DOC_SIMILIARITY_ACCURACY']
file_ext_list = config['CLASSIFIER']['SUPPORTED_FILE_EXTENSIONS'].split(",")
img2text_dest_dir = config['CLASSIFIER']['IMG2TXT_IMG_SAVE_LOC']
root_dir = config['CLASSIFIER']['TRAINING_DATASET_LOCATION']
api_port_number = config['CLASSIFIER']['API_PORT_NUMBER']
headers = {'Content-Type': "application/json", 'cache-control': "no-cache"}
get_headers = {}


class doc_iterator(object):
    def __init__(self, doc_list, labels_list):
        self.labels_list = labels_list
        self.doc_list = doc_list

    def __iter__(self):
        for idx, doc in enumerate(self.doc_list):
            #print("\n ################# Doclist :         idx:", self.labels_list[idx], "  doc:", doc)
            logger.info("\n ################# Doclist :  idx:", self.labels_list[idx], "  doc:", doc)
            # yield TaggedDocument(words=doc.split(), tags=[self.labels_list[idx]])
            yield TaggedDocument(words=doc, tags=[self.labels_list[idx]])


def initial_clean(text):
    import re
    """
    Function to clean text of any punctuation and lower case the text
    """
    text = re.sub("((\S+)?(http(s)?)(\S+))|((\S+)?(www)(\S+))|((\S+)?(\@)(\S+)?)", " ", text)
    text = re.sub("[^a-zA-Z ]", "", text)
    text = text.lower()  # lower case the text
    text = nltk.word_tokenize(text)
    return text


stop_words = stopwords.words('english')


def remove_stop_words(text):
    """
    Function that removes all stopwords from text
    """
    return [word for word in text if word not in stop_words]


stemmer = PorterStemmer()


def stem_words(text):
    """
    Function to stem words, so plural and singular are treated the same
    """
    try:
        text = [stemmer.stem(word) for word in text]
        text = [word for word in text if len(word) > 1]  # make sure we have no 1 letter words
    except IndexError:  # the word "oed" broke this, so needed try except
        pass
    return text


def apply_all(text):
    """
    This function applies all the functions above into one
    """
    return stem_words(remove_stop_words(initial_clean(text)))


def train_doc_sim_model():
    doc_labels = [f for f in listdir(train_corpus) if f.endswith('.txt')]
    logger.info(doc_labels)
    data = []
    for doc in doc_labels:
        data.append(apply_all(open(join(train_corpus, doc), 'r').read()))

    # data = apply_all(data)
    doc_iteration = doc_iterator(data, doc_labels)

    # train doc2vec model
    # model = gsm.Doc2Vec(size=500, window=5, min_count=5, workers=8,alpha=0.025, min_alpha=0.025,epochs=100) # use fixed learning rate
    # model = gsm.Doc2Vec(vector_size=5 , window=5, min_count=2, workers=8,alpha=0.025, min_alpha=0.025,epochs=100) # use fixed learning rate

    # model = gsm.Doc2Vec(dm=0, vector_size=100, negative=5, hs=0, min_count=5, sample=0,  epochs=20, workers=4)
    # model = gsm.Doc2Vec(vector_size=100, window=5, min_count=5, workers=8,alpha=0.025, min_alpha=0.025,epochs=100) # use fixed learning rate
    model = gsm.Doc2Vec(dm=0, vector_size=100, window=5, min_count=5, workers=8, alpha=0.010, min_alpha=0.025,
                        epochs=100)  # use fixed learning rate
    # model = gsm.Doc2Vec(corpus_file=500, window=5, min_count=5, workers=8,alpha=0.025, min_alpha=0.025,epochs=100) # use fixed learning rate

    # model.save(gsm_model_file_location+"\\"+gsm_model_name)

    # print("model is saved")
    # model = gsm.Doc2Vec(vector_size=50, min_count=2, epochs=40) # use fixed learning rate
    model.build_vocab(doc_iteration)

    model.train(doc_iteration, total_examples=len(doc_labels), epochs=model.epochs)

    model.save(gsm_model_file_location + "\\" + gsm_model_name)

    # model.delete_temporary_training_data(keep_doctags_vectors=True, keep_inference=True)
    logger.info("model is saved")

    #print("model is saved")


def add_new_category_tmplte(unclassified_file, DiscoveryInBoundId, post_req_url, text_content):


    #print(" \n\n\n\ train_unclassified_model: 1", unclassified_file, "train_corpus :", train_corpus)
    logger.info(" \n\n\n\ train_unclassified_model: 1", unclassified_file, "train_corpus :", train_corpus)
    if len(post_req_url.strip()) > 0:
        import shutil
        shutil.move(unclassified_file, train_corpus)

        _, filename = os.path.split(unclassified_file)

        new_text_file = train_corpus + "\\" + filename
        #print("\n\n\n\n + new_text_file ", new_text_file)
        logger.info("new_text_file:", new_text_file)

        #print(" \n\n\n\ train_unclassified_model: 2 ", new_text_file)
        logger.info("train_unclassified_model: 2:", new_text_file)
        train_unclassified_model(new_text_file, text_content, DiscoveryInBoundId)
        '''
        new_content_name = "new_content_type_"+strftime("%Y-%m-%d %H:%M:%S", gmtime())    
        headers = { 'Content-Type': "application/json", 'cache-control': "no-cache"  }        
        json_cont = "{ \"DiscoveryInBoundId\":"+str(DiscoveryInBoundId)+", \"ClassificationGroupId\": null  ,  \"Name\":\""+new_content_name+"\", \"DisplayName\":\""+ new_content_name+"\" , \"Value\": null ,  \"Content\":"+json.dumps(text_content)+",  \"CreatedBy\":\"e-classification\", \"CreatedDateTime\":\""+strftime("%Y-%m-%d %H:%M:%S", gmtime())+"\" , \"ModifiedBy\": null,\r\n  \"ModifiedDateTime\": null  }"
        #print("#######################################\n payload :",json_cont)        
        saveReq = reql.request("POST",url = post_req_url, data =  json_cont.encode('utf-8') ,headers=headers)       
        logger.info(saveReq)
        '''


def update_unclassified_groupid(inbound_id_list, group_id,auth_key):
    import requests as req
    headers['Authorization'] = auth_key
    for inbid in inbound_id_list:
        #print("\n\n\n\n inbid :", inbid)
        logging.info("inbid :", inbid)
        resp = req.request(method='GET', url=get_unclassified_id_request + str(inbid))
        # discovery_inbound_id = 242
        unclassified_json_str = json.loads(resp.text)
        update_unclassified_cont = ""
        #print("\n\n\group_id : ", group_id, " n\n unclassified_json_str :", unclassified_json_str)
        logger.info("group_id : ", group_id, "unclassified_json_str :", unclassified_json_str)
        if resp and resp.status_code == 200 and unclassified_json_str is not None:
            # unclassified_json_str = json.dumps(unclassified_json_str)
            #print(" \n\n\n\n : group_json_str :", unclassified_json_str)
            logger.info("group_json_str :", unclassified_json_str )
            update_unclassified_cont = "{  \"DiscoveryInBoundId\":\"" + str(inbid) + "\""
            update_unclassified_cont += " , \"Id\":\"" + str(unclassified_json_str.get("Id")) + "\" "
            if (group_id is not None):
                update_unclassified_cont += " ,  \"ClassificationGroupId\":\"" + str(group_id) + "\" "
            else:
                update_unclassified_cont += " ,\"ClassificationGroupId\": null "

            if (unclassified_json_str.get("ClassificationStatus") is not None):
                update_unclassified_cont += " ,\"ClassificationStatus\": \"" + unclassified_json_str.get(
                    "ClassificationStatus") + "\""
            else:
                update_unclassified_cont += " ,\"ClassificationStatus\": null "

            if (unclassified_json_str.get("Name") is not None):
                update_unclassified_cont += " ,\"Name\": \"" + unclassified_json_str.get("Name") + "\""
            else:
                update_unclassified_cont += " ,\"Name\": null "

            if (unclassified_json_str.get("DisplayName") is not None):
                update_unclassified_cont += " ,\"DisplayName\": \"" + unclassified_json_str.get("DisplayName") + "\""
            else:
                update_unclassified_cont += " ,\"DisplayName\": null "
            if (unclassified_json_str.get("Value") is not None):
                update_unclassified_cont += " ,\"Value\": \"" + unclassified_json_str.get("Value") + "\""
            else:
                update_unclassified_cont += " ,\"Value\": null "
            if (unclassified_json_str.get("Content") is not None):
                update_unclassified_cont += " ,\"Content\": " + json.dumps(unclassified_json_str.get("Content")) + ""
            else:
                update_unclassified_cont += " ,\"Content\": null "
            if (unclassified_json_str.get("IsDeleted") is not None):
                update_unclassified_cont += " ,\"IsDeleted\": " + str(int(unclassified_json_str.get("IsDeleted")))
            else:
                update_unclassified_cont += " ,\"IsDeleted\": null "
            if (unclassified_json_str.get("CreatedBy") is not None):
                update_unclassified_cont += " ,\"CreatedBy\": \"" + unclassified_json_str.get("CreatedBy") + "\""
            else:
                update_unclassified_cont += " ,\"CreatedBy\": null "
            if (unclassified_json_str.get("FileLocation") is not None):
                update_unclassified_cont += " ,\"FileLocation\": \"" + unclassified_json_str.get(
                    "FileLocation").replace("\\", "\\\\") + "\""
            else:
                update_unclassified_cont += " ,\"FileLocation\": null "
            if (unclassified_json_str.get("FileName") is not None):
                update_unclassified_cont += " ,\"FileName\": \"" + unclassified_json_str.get("FileName") + "\""
            else:
                update_unclassified_cont += " ,\"FileName\": null "
            if (unclassified_json_str.get("CreatedBy") is not None):
                update_unclassified_cont += " ,\"CreatedBy\": \"" + unclassified_json_str.get("CreatedBy") + "\""
            else:
                update_unclassified_cont += " ,\"CreatedBy\": null "

            if (unclassified_json_str.get("CreatedDateTime") is not None):
                update_unclassified_cont += " ,\"CreatedDateTime\": \"" + unclassified_json_str.get(
                    "CreatedDateTime") + "\""
            else:
                update_unclassified_cont += " ,\"CreatedDateTime\": null "

            update_unclassified_cont += ", \"ModifiedBy\": \"e-classification\",\r\n  \"ModifiedDateTime\":\"" + strftime(
                "%Y-%m-%d %H:%M:%S", gmtime()) + "\"  }"

            #print("\n\n\n ###################Unclassified ID:", unclassified_json_str.get("Id"))
            logger.info("###################Unclassified ID :", unclassified_json_str.get("Id") )
            # update_unclassified_cont =  "{\"Id\":\""+str(unclass_id)+"\", \"DiscoveryInBoundId\":\""+str(inbid)+"\", \"ClassificationGroupId\":\""+str(group_id)+"\"  ,\"ClassificationStatus\": \""+unclass_classification_status+"\" ,  \"Name\":\""+unclass_name+"\", \"DisplayName\":\""+ unclass_display_name+"\" , \"Value\":\""+unclass_value+"\" ,\"Content\":"+json.dumps(unclass_content)+", \"IsDeleted\": \""+unclass_isdeleted+"\" , \"CreatedBy\":\""+unclass_createdby+"\", \"CreatedDateTime\":\""+unclass_createddatetime+"\" , \"ModifiedBy\": \"e-classification\",\r\n  \"ModifiedDateTime\":\""+strftime("%Y-%m-%d %H:%M:%S", gmtime())+"\"  }"
            #print("#######################################\n UPDATE Unclassified :", update_unclassified_cont)
            logger.info("#######################################\n UPDATE Unclassified :", update_unclassified_cont)
            update_saveReq = reql.request("POST", url=unclassified_templ_update, data=update_unclassified_cont,
                                          headers=headers)
            #print(" update_unclassified_groupid :", update_saveReq.text)
            logging.info(" update_unclassified_groupid :", update_saveReq.text)


def insert_unclassified_doc_info(inbound_id, group_id, content, doc_path, doc_location,auth_key):
    headers['Authorization'] = auth_key
    new_content_name = "new_content_type_" + strftime("%Y-%m-%d %H:%M:%S", gmtime())
    unclass_insert_json_cont = "{ \"DiscoveryInBoundId\":" + str(
        inbound_id) + ", \"ClassificationStatus\": null,  \"Name\":\"" + new_content_name + "\", \"DisplayName\":\"" + new_content_name + "\" , \"Value\": null ,  \"Content\":" + json.dumps(
        content) + ",  \"CreatedBy\":\"e-classification\", \"CreatedDateTime\":\"" + strftime("%Y-%m-%d %H:%M:%S",
                                                                                              gmtime()) + "\" , \"ModifiedBy\": null,\r\n  \"ModifiedDateTime\": null "
    if (doc_location is not None):
        unclass_insert_json_cont += " ,\"FileLocation\": \"" + doc_location.replace("\\", "\\\\") + "\""
    else:
        unclass_insert_json_cont += " ,\"FileLocation\": null "
    if (doc_path is not None):
        unclass_insert_json_cont += " ,\"FileName\": \"" + doc_path + "\""
    else:
        unclass_insert_json_cont += " ,\"FileName\": null "
    if (group_id is not None):
        unclass_insert_json_cont += " ,  \"ClassificationGroupId\":\"" + str(group_id) + "\"  }"
    else:
        unclass_insert_json_cont += " ,\"ClassificationGroupId\": null  }"

    #print("#######################################\n train_unclassified_model 3 :", unclass_insert_json_cont)
    logger.info("#######################################\n train_unclassified_model 3 :", unclass_insert_json_cont )
    new_unclass_add_resp = reql.request("POST", url=unclassified_templ_add, data=unclass_insert_json_cont,
                                        headers=headers)
    #print("\n\n insert_unclassified_doc_info , ID :", new_unclass_add_resp.text)
    logger.info("\n\n insert_unclassified_doc_info , ID :", new_unclass_add_resp.text )
    return (new_unclass_add_resp.text)


def add_new_group(auth_key):
    import requests as req
    headers['Authorization'] = auth_key
    get_headers['Authorization'] = auth_key
    resp = req.request(method='GET', url=get_group_count_request,headers=get_headers)
    if (resp and resp.status_code == 200) and (resp.json() is not None and int(resp.json()) >= 0):
        group_name = "Group_" + str(int(resp.json()) + 1)
        new_group_cont = "{ \"Name\":\"" + group_name + "\", \"CreatedBy\":\"e-classification\" , \"CreatedDateTime\":\"" + strftime(
            "%Y-%m-%d %H:%M:%S", gmtime()) + "\", \"ModifiedBy\": null, \"ModifiedDateTime\": null  }"
        #print("#######################################\n train_unclassified_model4:  new_group_cont :", new_group_cont)
        logger.info("#######################################\n train_unclassified_model4:  new_group_cont :", new_group_cont)
        group_resp = reql.request("POST", url=add_group_templ, data=new_group_cont, headers=headers)
        return (group_resp.text)


#@app.route('/unclassification', methods=['POST'])
def unclassified_process():
    from flask import request, jsonify
    #print("\n\n\n request :", request)
    logger.info("request :", request)
    response = request.json

    #print("\n\n\n RESPONSE :", response)
    logger.info("RESPONSE :", response)
    doc_name = response['file_name']
    inbound_id = int(response['inbound_id'])
    train_unclassified_model(doc_name, inbound_id)

    return jsonify(response)


# @app.route('/train_unclassified_model', methods = ['POST'])


def train_unclassified_model(new_doc_name, DiscoveryInBoundId):
    # train the model
    train_doc_sim_model()
    # model2vec=gsm.Doc2Vec.load(gsm_model_file_location+"\\"+gsm_model_name)
    # print("model is loaded")

    # loading the model
    model2vec = gsm.Doc2Vec.load(gsm_model_file_location + "\\" + gsm_model_name)
    #print("\n\n\n\n train_unclassified_model  \n\n new_doc_name :  ", new_doc_name)
    logger.info("\n\n\n\n train_unclassified_model  \n\n new_doc_name :  ", new_doc_name )
    new_doc_content = apply_all(open(join(train_corpus + "\\" + new_doc_name), 'r').read())  # .split()

    # new_test=["driving"]
    sim_doc_list = []
    inbound_id_list = []
    unclassified_doc_id = []

    with open(train_corpus + "\\" + new_doc_name) as textfile:
        text_content = textfile.read()

    # new_content_name = "new_content_type_" + strftime("%Y-%m-%d %H:%M:%S", gmtime())

    try:
        inferred_docvec = model2vec.infer_vector(new_doc_content)

        sim_doc_list = model2vec.docvecs.most_similar([inferred_docvec])

        #print(" sim_doc_list:", sim_doc_list)
        logger.info(" sim_doc_list:", sim_doc_list )
    except Exception as e:
        #print("\n\n\n\ SIM Exception ", e)
        logger.info("\n\n\n\ SIM Exception ", e)

    if len(sim_doc_list) == 0:
        new_unclass_doc_id = insert_unclassified_doc_info(DiscoveryInBoundId, None, text_content, new_doc_name,
                                                          train_corpus)
        #print("\n\n\n len(sim_doc_list) = 0 ", new_unclass_doc_id)
        logger.info("\n\n\n len(sim_doc_list) = 0 ", new_unclass_doc_id)
    else:
        import requests as req
        group_id = None
        doc_count = 0
        inbound_id_list = []
        for doc_temp, sim_accuracy in sim_doc_list:
            if (float(sim_accuracy) >= float(similiarity_accuracy)):
                inbound_id_temp = doc_temp.split("_")[0]
                inbound_id_list.append(inbound_id_temp)

        for doc, accuracy in sim_doc_list:
            if (float(accuracy) >= float(similiarity_accuracy)):
                doc_count += 1
                inbound_id = doc.split("_")[0]
                # inbound_id_list.append(inbound_id)
                # template_id = 2
                # url = "http://192.168.0.13:8080/privateapi/classificationtemplate/getById?id=2"
                resp = req.request(method='GET', url=get_unclassified_id_request + str(inbound_id))
                # discovery_inbound_id = 242
                group_json_str = json.loads(resp.text)
                if resp and resp.status_code == 200 and group_json_str is not None:
                    #print(" \n\n\n\n : group_json_str :", group_json_str)
                    logger.info(" \n\n\n\n : group_json_str :", group_json_str)
                    templ_id = group_json_str.get("ClassificationGroupId")
                    new_unclass_doc_id = group_json_str.get("Id")
                    unclassified_doc_id.append(new_unclass_doc_id)

                    if templ_id is not None and templ_id > 0:
                        group_id = templ_id
                        break
        #print("\n\n\n\n GROUP ID:", group_id, " \n Document Count", doc_count, " \n\n\n inbound_id_list :",
        #     len(inbound_id_list))
        logger.info("\n\n\n\n GROUP ID:", group_id, " \n Document Count", doc_count, " \n\n\n inbound_id_list :",
              len(inbound_id_list))

        if (len(inbound_id_list) == 0 and (
                group_id == None or group_id == '' or int(group_id) == 0) and doc_count == 0):
            new_unclass_doc_id = insert_unclassified_doc_info(DiscoveryInBoundId, group_id, text_content, new_doc_name,
                                                              train_corpus)
            #print("\n\n\n\n inbound_id_list : 0 ,group_id :0 ,doc_count = 0 ==============>  saveReq :",
            #     new_unclass_doc_id)
            logger.info("\n\n\n\n inbound_id_list : 0 ,group_id :0 ,doc_count = 0 ==============>  saveReq :",
                  new_unclass_doc_id)
        elif len(inbound_id_list) >= 1 and (group_id is not None and group_id >= 1) and doc_count >= 1:
            new_unclass_doc_id = insert_unclassified_doc_info(DiscoveryInBoundId, group_id, text_content, new_doc_name,
                                                              train_corpus)  # inbound_id_list.append(DiscoveryInBoundId)
            #print("\n\n saveReq: new_unclass_doc_id ", new_unclass_doc_id, "group_id:", group_id, "inbound_id_list:",
            #     inbound_id_list)
            logger.info("\n\n saveReq: new_unclass_doc_id ", new_unclass_doc_id, "group_id:", group_id, "inbound_id_list:",
                  inbound_id_list)
            update_unclassified_groupid(inbound_id_list, group_id)
        elif (len(inbound_id_list) >= 1) and (
                group_id == None or int(group_id) == 0 or group_id.strip == '') and doc_count >= 1:
            import requests as req
            new_unclass_doc_id = insert_unclassified_doc_info(DiscoveryInBoundId, group_id, text_content, new_doc_name,
                                                              train_corpus)
            #print("\n\n\n\n inbound_id_list : 1 ,group_id : = 0 ,doc_count :1+ : ==============  saveReq :",
            #     new_unclass_doc_id)
            logger.info("\n\n\n\n inbound_id_list : 1 ,group_id : = 0 ,doc_count :1+ : ==============  saveReq :",
                  new_unclass_doc_id)
            # inbound_id_list.append(DiscoveryInBoundId)
            new_group_id = add_new_group()
            if (int(new_group_id) > 0):
                #print("\n\n\n\n New group id", new_group_id)
                logger.info("\n\n\n\n New group id", new_group_id)
                #print("\n\n\n\n unclassified_doc_id :", unclassified_doc_id, " unclassified_doc_id Length:",
                #     len(unclassified_doc_id))
                logger.info("\n\n\n\n unclassified_doc_id :", unclassified_doc_id, " unclassified_doc_id Length:",
                      len(unclassified_doc_id))
                update_unclassified_groupid(inbound_id_list, new_group_id)
        elif (len(inbound_id_list) == 0) and (
                group_id == None or int(group_id) == 0 or group_id == '') and doc_count >= 1:
            new_unclass_doc_id = insert_unclassified_doc_info(DiscoveryInBoundId, group_id, text_content, new_doc_name,
                                                              train_corpus)
            inbound_id_list.append(DiscoveryInBoundId)
            new_group_id = add_new_group()
            if (int(new_group_id) > 0):
                #print("\n\n\n\n New group id", new_group_id)
                logger.info(("\n\n\n\n New group id", new_group_id))
                update_unclassified_groupid(inbound_id_list, new_group_id)
            else:
                #print("\n\n\nFailed to add new group")
                logger.info("\n\n\nFailed to add new group")


if __name__ == "__main__":
    train_unclassified_model("C:/Users/admin/Documents/148_Sample-Aadhaar1120.txt", "148")

    #app.run(port=api_port_number, debug=True)
