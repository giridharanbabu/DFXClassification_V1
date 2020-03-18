from random import choice
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
from error_updation import *
from training_updates import get_training_data
from training_updates import get_model_name
from training_updates import insert_training_details
from training_updates import update_group_status
from nltk.stem.snowball import SnowballStemmer
stemmer = SnowballStemmer("english")

config = configparser.ConfigParser()
config.read('config.ini')

model_location=config['CLASSIFIER']['MODEL_SAVE_LOCATION']
vectorizer_model_pkl=config['CLASSIFIER']['VEC_MODEL_PKL_NAME']
classification_model_pkl=config['CLASSIFIER']['CLASS_PKL_NAME']
model_backup_loc=config['CLASSIFIER']['MODEL_BACKUP_LOCATION']

model_path = os.path.normpath(os.path.join(model_location, classification_model_pkl))
vec_model_path = os.path.normpath(os.path.join(model_location, vectorizer_model_pkl))

sysdate = strftime("%Y_%m_%d_%H_%M_%S", gmtime())

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


def write_files(files, path, group_doc_path_by_id):
    import os
    import shutil
    try:
        os.makedirs(path)
        for file in files:
            src_path = os.path.join(group_doc_path_by_id, file)
            dst_path = os.path.join(path, file)
            #print(src_path)
            shutil.copy(src_path, dst_path)
    except OSError:
        if not os.path.isdir(path):
            raise

training_location =r"C:\Users\gdnau\Giri\dfx\training\dataset"
group_path = r'C:\Users\gdnau\Giri\dfx\unclassified_doc\doc_group'
def  move_group(model_id):
    import shutil
    from os import walk
    import os
    import requests as req
    from time import gmtime, strftime
    move_group_dict = {}
    count = 0
    group_id = get_training_data(model_id)
    #print(group_id)
    group_files_count = 0
    import random
    for root, subdirs, files in os.walk(group_path):
        for doc_group in subdirs:
            for id in group_id:
                if str(id[0]) == doc_group:
                    filenames = random.sample(os.listdir(os.path.join(group_path, str(id[0]))), 20)
                    model_name = get_model_name(id[1])
                    #print(model_name)
                    path = os.path.join(training_location, str(model_name))
                    group_doc_path_by_id = os.path.join(group_path,str(id[0]))
                    write_files(filenames, path, group_doc_path_by_id)
                    group_files_count = group_files_count + 1
                    #print("\n Count : ", group_files_count)
                else:
                    pass

    return group_files_count

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

def build_model(model_id, status):
    try :
        import time
        from datetime import datetime
        start_time = datetime.now()
        print(start_time)
        import json
        training_dict = {}
        logger.info("\n\n >>>>>>>>>>>>>>>>>>>> Move Group to Training In Progress <<<<<<<<<<<<<<<<<<<<<< ")
        group_count = move_group(model_id)
        if  group_count > 0:
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
                    end_time = datetime.now()
                    print('Duration: {}'.format(end_time - start_time))
                    insert_training_details(start_time, end_time, training_location, model_path, vec_model_path, "0.98")
                    update_group_status(model_id)
                    #update_trained_group()
                    # pid_opened = address_to_pid(host, int(training_port))
                    # logger.info(pid_opened)
                    # os.kill(pid_opened, signal.SIGTERM)
                    training_dict['training_resp']=" Model build process is successfully completed "
                else:
                   training_dict['training_resp']=" Failed to  Build Model "
                   logger.info(training_dict)
            else:
                training_dict['training_resp'] = "dataset length is zero , unable to build the new model "
               #exception_log(' Training is stopped ', '  dataset length is zero , unable to build the new model ')
        else:
            training_dict['training_resp'] = " There is no new dataset available  for training "

            #exception_log(' Training is stopped ', ' There is no new dataset available  for training ')

    except Exception as error:
        #error_updation.exception_log(error, "Failed to  complete  the process in model building :", str(''))
        #pid_opened = address_to_pid(host,int(training_port))
        logger.info(error)
        #os.kill(pid_opened, signal.SIGTERM)

    return json.dumps(training_dict)


#print(build_model(6))
#print(move_group(6))