from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
import dfx_security
import pandas as pd
import sklearn
from sklearn.model_selection import train_test_split
import configparser
import logging, logging.config
from sklearn.metrics import confusion_matrix
import re
import os
import signal
import nltk
from loguru import logger
from flask import Flask , jsonify
import error_updation
from error_updation import *
from time import gmtime, strftime
import datetime
import os.path
import os
import json
import classifier_transactions
from loguru import logger
from classifier_transactions import update_classification_isnew
from error_updation import *


app = Flask(__name__)

config = configparser.ConfigParser()
config.read('config.ini')

log_location=config['CLASSIFIER']['LOGGER_LOC']
loginfo_filename=config['CLASSIFIER']['LOGINFO_FILENAME']
logdebug_filename=config['CLASSIFIER']['LOGDEBUG_FILENAME']
path_separator=config['CLASSIFIER']['PATH_SEP']
training_location=config['CLASSIFIER']['TRAINING_DATASET_LOCATION']
model_location=config['CLASSIFIER']['MODEL_SAVE_LOCATION']
vectorizer_model_pkl=config['CLASSIFIER']['VEC_MODEL_PKL_NAME']
classification_model_pkl=config['CLASSIFIER']['CLASS_PKL_NAME']
model_backup_loc=config['CLASSIFIER']['MODEL_BACKUP_LOCATION']
system_config_all=config['CLASSIFIER']['DISCOVERY_API_HOST']
training_status_complete_status=config['CLASSIFIER']['TRAINING_COMPLETE_STATUS']
training_port=int(config['CLASSIFIER']['TRAINING_PORT'])
training_doc_max=int(config['CLASSIFIER']['TRAINING_DOC_MAX'])
unclassified_group_file_loc=config['CLASSIFIER']['SIM_UNCLASSIFIED_GROUP']
unclassified_group_template_loc=config['CLASSIFIER']['SIM_TEMPLATE_GROUP']
classify_training_loc=config['CLASSIFIER']['TRAINING_DATASET_LOCATION']
max_training_doc=config['CLASSIFIER']['TRAINING_DOC_MAX']
host=config['CLASSIFIER']['CLASSIFIER_HOST']


import urllib.parse
move_groupto_training  = urllib.parse.urljoin(config['CLASSIFIER']['DISCOVERY_API_HOST'], config['CLASSIFIER']['MOVE_GROUPTO_TRAINING'])
get_subclass_template = urllib.parse.urljoin(config['CLASSIFIER']['DISCOVERY_API_HOST'],config['CLASSIFIER']['SELECT_SUBCLASS_TEMPLATE_BYID'])
get_unclassified_group = urllib.parse.urljoin(config['CLASSIFIER']['DISCOVERY_API_HOST'],config['CLASSIFIER']['SELECT_UNCLASS_BYGROUPID'])
update_unclass_training =  urllib.parse.urljoin(config['CLASSIFIER']['DISCOVERY_API_HOST'],config['CLASSIFIER']['UPDATE_UNCLASS_TRAINING'])
update_group_move_completed =  urllib.parse.urljoin(config['CLASSIFIER']['DISCOVERY_API_HOST'],config['CLASSIFIER']['UPDATE_GROUP_MOVE_COMPLETED'])
update_subclass_active =  urllib.parse.urljoin(config['CLASSIFIER']['DISCOVERY_API_HOST'],config['CLASSIFIER']['UPDATE_SUBCALSS_ACTIVE'])
get_inbound_byid =  urllib.parse.urljoin(config['CLASSIFIER']['DISCOVERY_API_HOST'],config['CLASSIFIER']['GET_INBOUND_BYID'])
update_inbound_api = urllib.parse.urljoin(config['CLASSIFIER']['DISCOVERY_API_HOST'],config['CLASSIFIER']['UPDATE_INBOUND'])
get_training_data_api = urllib.parse.urljoin(config['CLASSIFIER']['DISCOVERY_API_HOST'],config['CLASSIFIER']['GET_TRAINING_DATA_API'])
dfx_start_classifier_api = urllib.parse.urljoin(config['CLASSIFIER']['DISCOVERY_API_HOST'], config['CLASSIFIER']['TRAINING_COMPLETE_STATUS'])
select_class_byid = urllib.parse.urljoin(config['CLASSIFIER']['DISCOVERY_API_HOST'], config['CLASSIFIER']['SELECT_CLASS_BYID'])
update_class_template = urllib.parse.urljoin(config['CLASSIFIER']['DISCOVERY_API_HOST'], config['CLASSIFIER']['UPDATE_CLASS_TEMPLATE'])


#sec_token = dfx_security.get_security_token()
headers = { 'Content-Type': "application/json", 'cache-control': "no-cache" ,'Authorization':  "sec_token" }
get_headers = {'Authorization':  "sec_token"}
training_record_count=0

sysdate = strftime("%Y_%m_%d_%H_%M_%S", gmtime())
dt = str(datetime.datetime.now()).replace(":","_")
newname = 'training_loginfo.log'+'.zip'+dt+'.zip'
newname_debug = 'training_debuglog.log'+'.zip' +dt+ '.zip'

group_status='Initiated'
group_in_training='InTraining'
group_in_training_failed = 'Failed'
group_complated_status='Completed'
model_path = os.path.normpath(os.path.join(model_location, classification_model_pkl))
vec_model_path = os.path.normpath(os.path.join(model_location, vectorizer_model_pkl))


if os.path.exists('training_loginfo.log'+'.zip'):
    os.rename('training_loginfo.log'+'.zip', newname)
if os.path.exists('training_debuglog.log'+'.zip'):
    os.rename('training_debuglog.log'+'.zip', newname_debug)
    #shutil.move(newname,r'C:\Users\giri\Desktop\DATASCIENTIST1\archieve_ini\config1'+Filename_config)

logger.add('traininginfo.log', format="{time} {message} | {level} | {message}", backtrace=True, level='INFO', rotation="1 day", enqueue=True, compression="zip")
logger.add('training_debuglog.log', format="{time} {message} | {level} | {message}", backtrace=True, level='DEBUG', rotation="1 day", enqueue=True, compression="zip")


def get_file_name(file_path):
    filename = ''
    if len(file_path) > 1:
         filename = os.path.splitext(os.path.basename(file_path))[0]
    return str(filename)


def get_file_ext(file_path):
    if len(file_path) > 1:
         ext  = os.path.splitext(os.path.basename(file_path))[1]
    return str(ext)


def address_to_pid(ip_address, ip_port):
    try:
        import psutil
        import os
        import signal
        from psutil import process_iter
        from signal import SIGTERM
        possible_pids = set()
        [x.pid for x in psutil.net_connections() if x.laddr == (
            str(ip_address), ip_port) and x.pid not in possible_pids\
                    and possible_pids.add(x.pid)]
        if len(possible_pids) < 1:
            return 'Nothing'
        return possible_pids.pop()
    except Exception as e:
        logger.error("error occurred in getting the pid {}", e)

from nltk.stem.snowball import SnowballStemmer
stemmer = SnowballStemmer("english")

def tokenize_stem(text):
    logger.info("\n\n tokenize_stem :")
    tokens = [word for sent in nltk.sent_tokenize(text) for word in nltk.word_tokenize(sent)]
    filtered_tokens = []
    # filter out any tokens not containing letters (e.g., numeric tokens, raw punctuation)
    for token in tokens:
        if re.search('[a-zA-Z]', token):
            filtered_tokens.append(token)
    stems = [stemmer.stem(t) for t in filtered_tokens]
    return stems


def training_dataset():
    # Load the document from source path and converted into dataset
    try:
        logger.debug("\n\n training_dataset : {}", tokenize_stem)
        templates = []
        final_dataset = {}
        from os import listdir
        # read the templates
        for name in os.listdir(training_location):
            templates.append(name)
        # Load the data
        logger.info('\n Loading the dataset...\n')
        logger.info('\n templates : ',templates)
        from sklearn import datasets
        final_dataset = sklearn.datasets.load_files(training_location,
                                                       description=None, categories=templates, load_content=True,
                                                       encoding='ISO-8859-1', shuffle=False, random_state=42)
        print("\n type -> final_dataset :",type(final_dataset))
    except Exception as err:
        error_updation.exception_log(err, "error in final_dataset", str(''))
        #print("training_dataset", err)
    return final_dataset


def  move_group():
    import shutil
    from os import walk
    import os
    import requests as req
    from time import gmtime, strftime
    move_group_dict = {}
    count = 0
    logger.info(" move_group :{}")
     # try:
    move_group_dict['error_msg'] = ''
    move_group_dict['moved_group'] = []
    is_training_require = False
    #group_reqst = req.request(method='GET', url=move_groupto_training + group_status, headers=get_headers)
    #group_reqst_data = group_reqst.json()
    #print(" move_group group_reqst_data :{}",group_reqst_data)
    if group_reqst and group_reqst.status_code == 200 and group_reqst_data is not None and len(group_reqst_data) >= 1:
        for group in group_reqst_data:
            group_porcess_error = 0
            group_id = group['Id']
            get_training_data_url = get_training_data_api + str(group_id) + "&count=" + str(max_training_doc)
            group_unclassified_reqst = req.request(method='GET', url=get_training_data_url, headers=get_headers)
            unclassified_training_data = group_unclassified_reqst.json()
            subtemplate_id = group['SubClassificationTemplateId']
            logger.debug(" group_id : {}, subtemplate_id:{}", group_id, subtemplate_id)
            subclass_template_reqst = req.request(method='GET', url=get_subclass_template + str(subtemplate_id), headers=get_headers)
            subclass_templ_reqst_data = subclass_template_reqst.json()
            if group_unclassified_reqst and group_unclassified_reqst.status_code == 200 and  subclass_templ_reqst_data is not None  and subclass_template_reqst and subclass_template_reqst.status_code == 200 and  subclass_template_reqst.json() is not None and len(subclass_templ_reqst_data) >= 1:
                subclass_template_reqst_data = subclass_template_reqst.json()
                new_category_name = subclass_template_reqst_data['Name']
                new_dir_name = os.path.normpath(os.path.join(classify_training_loc, new_category_name))
                remove_train_dir = os.path.normpath(os.path.join(unclassified_group_template_loc,str(group_id)))
                if not os.path.exists(new_dir_name):
                    os.makedirs(new_dir_name, mode=0o777, exist_ok=True)
                import shutil
                group_files_count = 0
                for training_data in unclassified_training_data:
                    source_file_name = training_data['FileLocation']
                    inbound_id =  training_data['DiscoveryInBoundId']
                    id = training_data['Id']
                    import ntpath
                    destination = os.path.normpath(os.path.join(classify_training_loc,new_category_name,ntpath.basename(source_file_name)))
                    print(" \n source_file_name :",source_file_name)
                    print(" \n destination :", destination)
                    print(" \n new_dir_name :", new_dir_name)
                    if os.path.exists(source_file_name) and not os.path.exists(destination) and os.path.exists(new_dir_name):
                        shutil.move(source_file_name,new_dir_name)
                        if os.path.exists(destination):
                            training_data["IsTrainingDocument"] = 1
                            training_data["FileLocation"] = destination
                            training_data["Content"]= None
                            training_data["ContentDisplay"] = None
                            training_data["ModifiedBy"]="classifier"
                            sysdate = strftime("%Y-%m-%d %H:%M:%S", gmtime())
                            training_data["ModifiedDateTime"] = sysdate
                            training_data["ClassificationStatus"] = None
                            payload = json.dumps(training_data)
                            req.request("POST", url=update_unclass_training, data=payload, headers=headers)
                            group_files_count=group_files_count+ 1
                            print("\n Count : ",count)
                        else:
                            print()
                            #classifier_transactions.update_unclassifier_error_status(id,sec_token)
                            #exception_log('Document  in training',
                                          #'Destination path not exists ' + destination ,
                                          #inbound_id)
                    else:
                        print()
                        #classifier_transactions.update_unclassifier_error_status(id,sec_token)
                       # exception_log('OCR data is missing for training', 'Please check the source -'+source_file_name+'  , destination path - '+destination+' and  new directory -'+new_dir_name ,inbound_id )
                shutil.rmtree(remove_train_dir)
                if group_files_count > 0:
                    group['Status'] = group_in_training
                    count = count+1
                else:
                    group['Status'] = group_in_training_failed
                payload = json.dumps(group)
                group_status_update_rqst = req.request("POST", url=update_group_move_completed, data=payload,
                                                       headers=headers)
                if group_files_count > 0 and group_status_update_rqst and group_status_update_rqst.status_code == 200:
                    move_group_dict['moved_group'].append(str(group_id))
            else:
                exception_log('Failed in training',' failed to process group for training' + str(group_id))
    else:
        exception_log('Failed in training', ' failed to get group details for training' + move_groupto_training + group_status)
    # except Exception as error:
    #     exception_log('Failed in training', ' failed to get group details for training' +str(error))
    return count


def update_groupto_category():
    import shutil
    from os import walk
    import os
    import requests as req
    logger.info(" move_group :{}")
    update_training_group = {}
    try:
        group_reqst = req.request(method='GET', url=move_groupto_training + group_in_training, headers=get_headers)
        group_reqst_data = group_reqst.json()
        update_training_group['error_msg'] = ''
        update_training_group['moved_group'] = []
        print(" update_groupto_category GROUP :{}",group_reqst_data)
        if group_reqst and group_reqst.status_code == 200 and group_reqst.json() is not None:
            for group in group_reqst_data:
                group_id = group['Id']
                group_unclassified_reqst = req.request(method='GET', url=get_unclassified_group + str(group_id),headers=get_headers)
                unclass_reqst_data = group_unclassified_reqst.json()
                logger.debug(" \n \n unclass_reqst_data: {}", unclass_reqst_data)
                if group_unclassified_reqst and group_unclassified_reqst.status_code == 200 and unclass_reqst_data is not None:
                    for unclass_rec in unclass_reqst_data:
                        if int(unclass_rec['IsTrainingDocument']) == 1:
                            inbound_id = unclass_rec['DiscoveryInBoundId']
                            payload=None
                            #inbound_req = req.request("POST", url=update_inbound_api+str(inbound_id)+"&status=Open", data=payload, headers=headers)
                            unclass_rec["IsDeleted"] = 1
                            unclass_rec["ClassificationStatus"] = 'Training'
                            payload = json.dumps(unclass_rec)
                            unclass_rec_request = req.request("POST", url=update_unclass_training, data=payload, headers=headers)
                            logger.debug(" \n \n unclass_rec_request: {}", unclass_rec_request.status_code)
                subtemplate_id = group['SubClassificationTemplateId']
                logger.debug(" \n \n subtemplate_id: {}", subtemplate_id)
                subclass_template_reqst = req.request(method='GET', url=get_subclass_template + str(subtemplate_id), headers=get_headers)
                if subclass_template_reqst and subclass_template_reqst.status_code == 200 and subclass_template_reqst.json() is not None:
                    subclass_template_reqst_data = subclass_template_reqst.json()
                    subclass_template_reqst_data["IsActive"] = 1
                    subclass_template_reqst_data["IsNew"] = 0
                    class_id = subclass_template_reqst_data["ClassificationTemplateId"]
                    logger.debug(" \n \n subclass_template_reqst_data : class_id: {}", class_id)
                    payload_active = json.dumps(subclass_template_reqst_data)
                    update_subclass_rest = req.request("POST", url=update_subclass_active, data=payload_active, headers=headers)
                    logger.debug(" \n \n update_subclass_rest : class_id: {}", update_subclass_rest.status_code)
                    update_classification_isnew(class_id,sec_token,0,is_active=1)
                group["Status"] = group_complated_status
                payload = json.dumps(group)
                req.request("POST", url=update_group_move_completed, data=payload, headers=headers)
            update_training_group['move_msg'] = ' After Training Group status is updated successfully '
        else:
            update_training_group['error_msg'] = 'Please check the rest point fo: ' + move_groupto_training + group_status
    except Exception as error:
        print(" Error occurred in update completed status in group', error :", str(error))
    return update_training_group


def pickle_save(model, path, filename):
    try :
        import pickle
        model_name = os.path.normpath(os.path.join(path ,filename))
        with open(model_name, 'wb') as f:
            pickle.dump(model, f)
            logger.debug("\n\n Pickled dumped : {}", path)
        if os.path.exists(model_name) :
            return model_name
        else:
            raise WindowsError(" Model build process is failed")
    except Exception as error :
        error_updation.exception_log(error, "Model build process is failed", str(filename))
        #print(" Model build process is failed",str(error))


def cross_validation(features,labels ,cv_no=5):
    from sklearn.model_selection import cross_val_score
    from sklearn.linear_model import LogisticRegression
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.naive_bayes import MultinomialNB
    models = [
        LogisticRegression(random_state=0,n_jobs= -1,solver='saga'),
        RandomForestClassifier(n_estimators=200, max_depth=3, random_state=0),
        MultinomialNB()
    ]
    cross_validation_df = pd.DataFrame(index=range(cv_no * len(models)))
    entries = []
    for model in models:
        model_name = model.__class__.__name__
        accuracies = cross_val_score(model, features, labels, scoring='accuracy', cv=cv_no)
        for fold_idx, accuracy in enumerate(accuracies):
            entries.append((model_name, fold_idx, accuracy))
    cross_validation_df = pd.DataFrame(entries, columns=['model_name', 'fold_idx', 'accuracy'])
    cv_acc_mean = cross_validation_df.groupby('model_name').accuracy.mean()
    logger.debug("\n\n Accuracy mean: {}",cv_acc_mean)
    print(' cv_acc_mean :',cv_acc_mean)
    return cv_acc_mean


def update_classification_isnew(class_id,auth_key,is_new=0,is_active=0):
    try:
        import requests as req
        headers['Authorization'] = auth_key
        get_headers['Authorization'] = auth_key
        class_rqst = req.request(method='GET', url=select_class_byid + str(class_id),headers=get_headers)
        class_rqst_data = class_rqst.json()
        logger.debug("\n\n update_classification_isnew : class_rqst_data : {}, select_class_byid class_id :{} ", class_rqst_data , select_class_byid + str(class_id))
        if class_rqst and class_rqst.status_code == 200 and class_rqst_data is not None:
            class_rqst_data["IsNew"] = is_new
            class_rqst_data["IsActive"]=is_active
            payload = json.dumps(class_rqst_data)
            logger.debug("\n\n update_classification_isnew : {}", payload)
            update_class_reqst = req.request("POST", url=update_class_template, data=payload, headers=headers)
            logger.debug("\n\n update_classification_isnew:, {},update_class_reqst:{}", update_class_reqst.status_code, update_class_reqst.text)
            return update_class_reqst.text
    except Exception as error:
        logger.debug("\n\n exception: {}", str(error))



@app.route('/'+config['CLASSIFIER']['TRAINING_URL'] )
def call_training():
    return jsonify(build_model())


def build_model():
    try :
        import json
        training_dict = {}
        logger.info("\n\n >>>>>>>>>>>>>>>>>>>> Move Group to Training In Progress <<<<<<<<<<<<<<<<<<<<<< ")
        if move_group() > 0 :
            import shutil
            import gzip
            import subprocess
            bkup_file_name = 'bkup_'+sysdate
            logger.info("\n\n training_dataset - > Model Building ")
            training_data = training_dataset()
            logger.info('\n Feature Extraction...\n')
            logger.info(" DATASET LENGTH : {}", len(training_data.data))
            if len(training_data.data) >= 1:
                if os.path.exists(model_path):
                    os.rename(model_path, os.path.normpath(
                        os.path.join(model_backup_loc, bkup_file_name + "_" + classification_model_pkl)))
                if os.path.exists(vec_model_path):
                    os.rename(vec_model_path,
                              os.path.normpath(os.path.join(model_backup_loc, bkup_file_name + "_" + vectorizer_model_pkl)))
                #tfidf_vec_model = TfidfVectorizer(tokenizer=tokenize_stem,stop_words='english')
                tfidf_vec_model = TfidfVectorizer(sublinear_tf=True, min_df=5, norm='l2', encoding='latin-1', ngram_range=(1, 2), tokenizer=tokenize_stem,  stop_words='english')
                features = tfidf_vec_model.fit_transform(training_data.data,y=None).toarray()
                labels = training_data.target
                logger.debug("features : {}", features.shape)
                cv_df = cross_validation(features=features, labels=labels, cv_no=5)
                print(' cv_df ', cv_df)
                print('  cv_df type :', type(cv_df))
                #print("features :",features.shape)
                X_train, X_test, y_train, y_test = train_test_split(features, labels, test_size=0.33, random_state=0)
                model = LogisticRegression(random_state=0,n_jobs=-1,solver='saga')
                model.fit(X_train, y_train)
                logger.debug(" \n\n pickle_saved :{}", classification_model_pkl)
                y_pred_proba = model.predict_proba(X_test)
                y_pred = model.predict(X_test)
                logger.debug(" \n\n y_pred :{} ",y_pred)
                conf_mat = confusion_matrix(y_test, y_pred)
                pickle_save(tfidf_vec_model , model_location, vectorizer_model_pkl)
                pickle_save(model, model_location, classification_model_pkl)
                logger.debug("\n\n conf_mat: {}", conf_mat)
                logger.info(" Model location: model_path ->", model_path, "vec_model_path:", vec_model_path)
                training_dict['training_resp'] = ''
                if os.path.exists(vec_model_path) and os.path.exists(model_path):
                    update_groupto_category()
                    pid_opened = address_to_pid(host, int(training_port))
                    logger.info(pid_opened)
                    os.kill(pid_opened, signal.SIGTERM)
                    # import requests as req
                    # group_unclassified_reqst = req.request(method="GET", url=dfx_start_classifier_api, headers=get_headers)
                    # if group_unclassified_reqst and group_unclassified_reqst.status_code == 200 :
                    training_dict['training_resp']=" Model build process is successfully completed "
                else:
                   training_dict['training_resp']=" Failed to  Build Model "
                   logger.info(training_dict)
            else:
               exception_log(' Training is stopped ', '  dataset length is zero , unable to build the new model ')
       else:
           exception_log(' Training is stopped ', ' There is no new dataset available  for training ' )
    except Exception as error:
        #error_updation.exception_log(error, "Failed to  complete  the process in model building :", str(''))
        pid_opened = address_to_pid(host,int(training_port))
        logger.info(pid_opened)
        #os.kill(pid_opened, signal.SIGTERM)
    return json.dumps(training_dict)


if __name__ == "__main__":
    #training_dataset()
    print(build_model())
    #app.run(host=config['CLASSIFIER']['CLASSIFIER_HOST'], port=config['CLASSIFIER']['TRAINING_PORT'], debug=False)