"""
Created on Tue Jun  4 15:58:57 2019

@author: baskaran
"""
import os
import json
import configparser
import logging.config
from flask import json
import logging
import classifier_transactions
import document_similarity
from loguru import logger

import error_updation
from error_updation import *
config = configparser.ConfigParser()
config.read('config.ini')
log_location = config['CLASSIFIER']['LOGGER_LOC']
#loginfo_filename = config['CLASSIFIER']['LOGINFO_FILENAME']
#logdebug_filename = config['CLASSIFIER']['LOGDEBUG_FILENAME']

# logger.add(loginfo_filename, format="{time:YYYY-MM-DD at HH:mm:ss} | {level} | {message}", backtrace=True ,  level='INFO' , rotation="00:00", compression="zip",enqueue=True ,diagnose=True  )
# logger.add(logdebug_filename, format="{time:YYYY-MM-DD at HH:mm:ss} | {level} | {message}", backtrace=True ,  level='DEBUG' , rotation="00:00", compression="zip",enqueue=True ,diagnose=True  )


path_separator = config['CLASSIFIER']['PATH_SEP']
group_identifier = config['CLASSIFIER']['GROUP_IDENTIFIER']
sim_group_loc = config['CLASSIFIER']['SIM_UNCLASSIFIED_GROUP']
unclassified_doc_loc = config['CLASSIFIER']['SIM_UNCLASSIFIED_DOC_LOC']
sim_template = config['CLASSIFIER']['SIM_TEMPLATE_GROUP']
sim_group_loc = config['CLASSIFIER']['SIM_UNCLASSIFIED_GROUP']
sim_accuracy = config['CLASSIFIER']['DOC_SIMILIARITY_ACCURACY']
group_details = {}


def get_file_name(file_path):
    filename = ''
    if len(file_path) > 1:
         filename = os.path.splitext(os.path.basename(file_path))[0]
    return str(filename)

def get_file_ext(file_path):
    if len(file_path) > 1:
         ext  = os.path.splitext(os.path.basename(file_path))[1]
    return str(ext)

'''
def file_rename(file_name, doc_group_no):

    new_group_filename = ''
    try:

        logger.debug(" file_rename : file_name {}, doc_group_no :{}",file_name, ,doc_group_no)

        new_group_filename = os.path.normpath(os.path.join(sim_group_loc, str(doc_group_no),
                                                           str(doc_group_no) + group_identifier + get_file_name(
                                                               file_name) + get_file_ext(file_name)))
        if os.path.exists(file_name) and not os.path.exists(new_group_filename) and int(doc_group_no) > 0:
            os.rename(file_name, new_group_filename)
        else:
            return " Error in file_rename : Resource is not available on mentioned location "+ file_name+", new group file name: ",new_group_filename
    except Exception as error:
        group_details['error_code'] = 3
        group_details['error_msg'] += " Find_group : Issue with file rename "+ str(error)
    return new_group_filename

'''
def file_rename(old_name, new_name):
    try:
        os.rename(old_name, new_name)
    except WindowsError:
        os.remove(new_name)
        os.rename(old_name, new_name)
    return new_name


def find_group(new_doc_name,auth_key):
    try :
        group_details['error_code'] = 0
        if os.path.exists(new_doc_name):
            group_no = 0
            group_details['error_msg'] = ''
            group_details['group_no'] = -1
            group_details['unclassified_file_name'] = ''
            group_details['new_group'] = 0
            text_file = ''
            #logger.debug("\n\n\n Find group : Input file {}, file size :{} ",new_doc_name , os.path.getsize(new_doc_name) )
            get_group_details  = document_similarity.similarity(new_doc_name,auth_key)
            logger.debug("\n\n\n Find group:  get_group_details {}", get_group_details)
            group_details['accuracy_rate']= get_group_details['accuracy_rate']
            group_details['group_no'] =  get_group_details['group_no']
            group_no =  get_group_details['group_no']
            group_details['new_group'] = get_group_details['new_group']
            logger.debug("\n\n\n Find group:  get_group_details  {}", group_no)
            if  group_no is not None  and int(group_no) > 0   and  new_doc_name is not None and new_doc_name is not '':
                #group_details['error_msg'] = get_group_details['error_msg']
                logger.debug("\n\n find_group :Group No from similarity : {}", group_no)
                logger.info("\n\n Group No : {}",group_no)
                template_path = os.path.normpath(os.path.join(sim_template,str(group_no)))
                group_file_path = os.path.normpath(os.path.join(sim_group_loc , str(group_no)))
                group_details['group_file_path'] = group_file_path
                group_details['doc_name'] = str(group_no) + group_identifier + get_file_name(new_doc_name) + get_file_ext(new_doc_name)
                access_rights = 0o755
                try:
                    import shutil
                    template_text_file = os.path.normpath(os.path.join(template_path,
                                                              str(group_no) + group_identifier + get_file_name(
                                                                  new_doc_name) + get_file_ext(new_doc_name)))
                    logger.info(template_text_file)
                    dim_doc_location = os.path.normpath(os.path.join(group_file_path,
                                                              str(group_no) + group_identifier + get_file_name(
                                                                  new_doc_name) + get_file_ext(new_doc_name)))
                    if not os.path.exists(group_file_path):
                        os.makedirs(group_file_path, access_rights)
                    if not os.path.exists(template_path) :
                        os.makedirs(template_path, access_rights)
                    if get_group_details['new_group'] == 1:
                        os.rename(new_doc_name, template_text_file)
                        shutil.copy(template_text_file, group_file_path)
                    else:
                        file_rename(new_doc_name, dim_doc_location)

                    #text_file = file_rename(new_temp_file, group_no)
                except OSError:
                    group_details['error_code'] = 3
                    group_details['error_msg'] +=  "find_group : Failed to create the directory , Dir : " +template_path+" , "+group_file_path+", " +str(OSError)
                    group_details['group_no'] = group_no
                    group_details['file_name'] = dim_doc_location
                    logger.debug("\n\n\n ##### Unclassified Grouping : Find Group : {}, \n\n Group File temp loc:{}", group_details, dim_doc_location)
            else:
                group_details['error_msg'] += get_group_details['error_msg']
                group_details['error_code'] += get_group_details['error_code']
        else:
            group_details['error_msg'] += " Resource or Directory is not available  "
            group_details['error_code'] = 3
    except Exception as error:
         group_details['error_code'] = 3
         #print("EXCEPTION in  find_group : ",error)
         error_updation.exception_log(error, "EXCEPTION in  find_group"+str(group_details['error_code']), str(new_doc_name))
         group_details['error_msg'] += "find_group : Issue with Resource to find  the unclassified documents group "

    return group_details



# if __name__ == '__main__':
#     print("\n MAIN:")
#     print(find_group(r"C:\Users\gdnau\Giri\dfx\tmp_source\file%3A%2FC%3A%2FUsers%2Fgdnau%2FGiri%2FMcf_Testdata%2Fwith_space_doc_name%2FService_Agreement1.docx_.txt",'auth_key'))
