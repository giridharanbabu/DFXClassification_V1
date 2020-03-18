# -*- coding: utf-8 -*-
"""
Created on Thu Jul 11 10:37:14 2019

@author: baskaran
"""

import gensim
import numpy as np
from nltk.tokenize import word_tokenize
import os
import classifier_transactions
# path to the input corpus files
import configparser
import logging.config
import sys
import json
from loguru import logger
from string import digits 

import error_updation
from error_updation import *


config = configparser.ConfigParser()
config.read('config.ini')
#print("config:", config)
config = configparser.ConfigParser()
config.read('config.ini')
log_location = config['CLASSIFIER']['LOGGER_LOC']
loginfo_filename = config['CLASSIFIER']['LOGINFO_FILENAME']
logdebug_filename = config['CLASSIFIER']['LOGDEBUG_FILENAME']


group_identifier = config['CLASSIFIER']['GROUP_IDENTIFIER']
sim_group_loc = config['CLASSIFIER']['SIM_UNCLASSIFIED_GROUP']
unclassified_doc_loc = config['CLASSIFIER']['SIM_UNCLASSIFIED_DOC_LOC']
sim_template = config['CLASSIFIER']['SIM_TEMPLATE_GROUP']
sim_accuracy =  config['CLASSIFIER']['DOC_SIMILIARITY_ACCURACY']



def new_data_query(test_data, dictionary, tf_idf_model, sims):
    query_doc = [w.lower() for w in word_tokenize(test_data)]
    query_doc_bow = dictionary.doc2bow(query_doc)
    query_doc_tf_idf = tf_idf_model[query_doc_bow]
    sim_result = sims[query_doc_tf_idf]
    return sim_result


def similarity(input_file,auth_key):
    error_msg = ''
    sim_details = {}
    sim_details['error_msg'] = ''
    sim_details['error_code'] = 0
    sim_details['new_group'] = 0
    sim_details['group_no'] = 0
    group_no = 0
    try:
        sim_details['error_code'] = 0
        if os.path.exists(input_file):
            from datetime import datetime as dt
            sysdate = dt.now()

            training_dataset = []
            train_data = ''
            doc_labels = [os.path.join(path, name) for path, subdirs, files in os.walk(sim_template) for name in files if
                          name.endswith('.txt')]
            train_txt_file = "sim_training_data.txt"
            logger.debug(" \n\n\n doc_labels : {}", doc_labels)
            remove_digits = str.maketrans('', '', digits) 
            for file in doc_labels:
                with open(file, 'r', errors='ignore', encoding='utf-8') as f:
                    training_dataset.append(((os.path.basename(os.path.dirname(file)) + '~~__~~' + (f.read()).translate(remove_digits)).replace("\n", ' ')) + "\n")
                    
                    
            logger.debug(" \n\n training_dataset: {}",training_dataset)
            #print(" \n\n SIM Input file", input_file)
            with open(input_file, "r", errors='ignore',encoding='utf-8') as f:
                new_data = f.read().replace("\n", ' ').translate(remove_digits)
                print("-----new_data",new_data)
            logger.debug("Number of train docs : {}".format(len(training_dataset)))
            if (len(training_dataset) > 0) :
                train_docs = [[w.lower() for w in word_tokenize(line)] for line in training_dataset]
                train_dictionary = gensim.corpora.Dictionary(train_docs)
                train_corpus = [train_dictionary.doc2bow(gen_doc) for gen_doc in train_docs]
                logger.info("Creating TF-IDF model")
                tf_idf = gensim.models.TfidfModel(train_corpus)
                logger.info(tf_idf)
                sim_model_loc = config['CLASSIFIER']['SIM_MODEL_LOC']
                sims = gensim.similarities.Similarity(sim_model_loc, tf_idf[train_corpus], num_features=999999999)
                logger.info("sims: {}", sims)
                result = new_data_query(test_data=new_data, dictionary=train_dictionary, tf_idf_model=tf_idf, sims=sims)
                logger.debug("\n\n\n result: {}", result)
                indices = np.asarray(result).argsort()[-5:][::-1]
                #indices = np.asarray(result).argsort()[-len(training_dataset):][::-1]
                # logger.debug(indices, [result[_] for _ in indices])
                res = [result[_] for _ in indices]
                logger.debug("\n\n res : {}", res[0])
                sim_details['accuracy_rate']= res[0]
                # op.write((training_dataset[indices[0]].split(group_identifier))[0] + "\n")
                group_list = training_dataset[indices[0]].split(group_identifier)
                #print("$$$$$ Group List",group_list)
                logger.debug("\n\n\n Group Number : {}", group_no)
                #print("#####",res[0])
                if len(group_list) > 0 and float(res[0]) >= float(sim_accuracy):
                    group_no= group_list[0]
                    sim_details['group_no'] = group_no
                    logger.debug("\n\n\n Existing Group Number : {}", group_no)
                else:
                    group_details = classifier_transactions.add_group(auth_key)
                    group_no = int(group_details['group_no'])
                    logger.debug("\n\n\n New Group Number : {}", group_no)
                    sim_details['group_no'] = group_no
                    if group_no is not None and  group_no is not '' and group_no > 0:
                        sim_details['new_group'] = 1
                    else:
                        sim_details['error_msg'] = group_details['error_msg']
                        sim_details['error_code'] = group_details['error_code']
                    logger.debug("\n\n\n New Group Number : {}", group_no)
            else:
                sim_details['error_msg']=" similarity : Error in similarity() : Resource is not available in mentioned location" + input_file
                sim_details['error_code'] = 4
                sim_details['group_no'] = group_no
    except Exception as err:
        sim_details['error_code'] = 4
        print(" Exception  occured in similarity :" + str(err))
        sim_details['error_msg'] = "Exception  occurred in similarity : Please check the input resource :"+input_file+" ,"+ str(err)
        error_updation.exception_log(err, sim_details, str(input_file))
    #logger.debug("\n\n\n sim_details: {}", sim_details)
    return sim_details

#'''
#if __name__ == '__main__':
     #print("\n MAIN:")
     #start_time = time()
     #print(similarity('C:\Users\sqladmin\Desktop\1~~__~~2_SDREW_bs.txt','5OQup5dfl74oPRGtwlvHn1SW5xU6MxobIkCN2fJhjnAIaCwXwuhf__1YOVObkc2rD76CC1Qfxj2tm7YYLHovxXek9tMy3ekX5AE8cfbHEDrHKBGte8oHS8aX7aBTCyNyxSfe4O02q6Rkt49iNYuo_wj4Mxd4VlKqTcpxjNy1TiwG4iU5ZXugPaeIeQ0eYg1XvbsvbqYLaQpO1zDJCtzmrIhwZe0pw5140GujMhlPf-uixZq6cYqqWPUW6GMzdoxpuwxJerMPVdYwhgPX6tW0Q4gb77D_OWLNqhg_JPHhZn8'))
     #print("Time taken : {}".format(time() - start_time))
#'''

