# -*- coding: utf-8 -*-
"""
Created on Sat Jul 13 20:48:15 2019

@author: baskaran
"""
import os
import configparser
import sys
from loguru import logger
from datetime import datetime
sys.path.insert(0, os.path.abspath('..'))
time = datetime.now().strftime("%d_%m_%Y_%H_%M_%S")
configfile_name = "config.ini"

# add the handlers to the logger
config = configparser.ConfigParser()
config.read('config.ini')
log_location = config['CLASSIFIER']['LOGGER_LOC']
loginfo_filename = config['CLASSIFIER']['LOGINFO_FILENAME']
logdebug_filename = config['CLASSIFIER']['LOGDEBUG_FILENAME']

logger.add(loginfo_filename, format="{time:YYYY-MM-DD at HH:mm:ss} | {level} | {message}", backtrace=True ,  level='INFO' , rotation="00:00", compression="zip",enqueue=True ,diagnose=True  )
logger.add(logdebug_filename,format="{time:YYYY-MM-DD at HH:mm:ss} | {level} | {message}", backtrace=True ,  level='DEBUG' , rotation="00:00", compression="zip",enqueue=True ,diagnose=True  )
port_list = [3535,3536,3537]


def checkopenport(port):
    import socket
    opensocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = False
    try:
        opensocket.bind(("0.0.0.0", port))
        result = True
    except:
        print("Port is in use")
    opensocket.close()
    return result


def create_ini_file(root_dir,server_name):
    # Check if there is already a configurtion file
    print("Directory :",root_dir)
    if os.path.exists(root_dir) and os.access(root_dir, mode=os.W_OK) and os.path.exists(configfile_name) and os.access(configfile_name, mode=os.W_OK):
        import shutil
        try:
            if os.path.isfile(configfile_name) and os.access(configfile_name, mode=os.W_OK):
                os.rename(configfile_name, configfile_name + '_backup_' + time)
        except Exception as error :
            print("Error occured when renaming the config.ini file ", error)
        else:
            # Create the configuration file as it doesn't exist yet
            ini_file = open(configfile_name, 'w')
            file_permission = ''
            # Add content to the file
            config = configparser.ConfigParser()
            config.optionxform = lambda option: option.upper()
            config.add_section('CLASSIFIER')
            training_location = os.path.normpath(os.path.join(root_dir,'dfxdataset'))
            os.makedirs(training_location ,mode=0o777, exist_ok=False)
            config.set('CLASSIFIER', 'TRAINING_DATASET_LOCATION', training_location)

            model_save_loc = os.path.normpath(os.path.join(root_dir, 'model'))
            os.makedirs(model_save_loc ,mode=0o777, exist_ok=False)
            config.set('CLASSIFIER', 'MODEL_SAVE_LOCATION', model_save_loc)

            class_prediction_loc = os.path.normpath(os.path.join(root_dir, 'prediction'))
            os.makedirs(class_prediction_loc,mode=0o777, exist_ok=False)
            config.set('CLASSIFIER', 'CLASS_PREDICTED_LOCATION', class_prediction_loc)

            unclassified_doc_loc = os.path.normpath(os.path.join(root_dir, 'unclassified_doc'))
            os.makedirs(unclassified_doc_loc,mode=0o777, exist_ok=False)
            config.set('CLASSIFIER', 'SIM_UNCLASSIFIED_DOC_LOC', unclassified_doc_loc)

            tmp_source_loc = os.path.normpath(os.path.join(root_dir, 'tmp_source'))
            os.makedirs(tmp_source_loc, mode=0o777, exist_ok=False)
            config.set('CLASSIFIER', 'TEMP_DIR_LOC', tmp_source_loc)

            sim_training_loc = os.path.normpath(os.path.join(root_dir, 'sim_training'))
            os.makedirs(sim_training_loc, mode=0o777, exist_ok=False)
            config.set('CLASSIFIER', 'SIM_MODEL_LOC', sim_training_loc)

            sim_unclassified_loc = os.path.normpath(os.path.join(root_dir,'unclassified_doc', 'doc_group'))
            os.makedirs(sim_unclassified_loc, mode=0o777, exist_ok=False)
            config.set('CLASSIFIER', 'SIM_UNCLASSIFIED_GROUP', sim_unclassified_loc)

            sim_template_loc = os.path.normpath(os.path.join(root_dir,'unclassified_doc', 'template'))
            os.makedirs(sim_template_loc, mode=0o777, exist_ok=False)
            config.set('CLASSIFIER', 'SIM_TEMPLATE_GROUP', sim_template_loc)

            imagetotext_loc = os.path.normpath(os.path.join(root_dir, 'imagetotext'))
            os.makedirs(imagetotext_loc, mode=0o777, exist_ok=False)
            config.set('CLASSIFIER', 'IMG2TXT_IMG_SAVE_LOC', imagetotext_loc)

            config.set('CLASSIFIER', 'IMAGE_BRIGHTNED', imagetotext_loc)

            ocr_image_loc = os.path.normpath(os.path.join(root_dir, 'image'))
            os.makedirs(ocr_image_loc, mode=0o777, exist_ok=False)
            config.set('CLASSIFIER', 'IMAGE_PATH', ocr_image_loc)

            logger_loc = os.path.normpath(os.path.join(root_dir, 'logs'))
            os.makedirs(logger_loc, mode=0o777, exist_ok=False)
            config.set('CLASSIFIER', 'LOGGER_LOC', logger_loc)

            class_output_loc = os.path.normpath(os.path.join(root_dir,root_dir, 'classified_result'))
            os.makedirs(class_output_loc, mode=0o777, exist_ok=False)

            class_output_loc = os.path.normpath(os.path.join(root_dir,root_dir, 'classified_result' ,'classified_output'))
            os.makedirs(class_output_loc, mode=0o777, exist_ok=False)
            config.set('CLASSIFIER', 'CLASSIFIED_RESULT', class_output_loc)


            class_error_loc = os.path.normpath(os.path.join(root_dir,root_dir, 'classified_result' ,'classified_error'))
            os.makedirs(class_error_loc, mode=0o777, exist_ok=False)
            config.set('CLASSIFIER', 'CLASSIFIED_ERROR', class_error_loc)

            class_metadata_loc = os.path.normpath(os.path.join(root_dir, root_dir, 'classified_result', 'metadata_extraction'))
            os.makedirs(class_metadata_loc, mode=0o777, exist_ok=False)
            config.set('CLASSIFIER', 'CLASSIFIED_METADATA', class_metadata_loc)

            class_extraction_templ = os.path.normpath(os.path.join(root_dir, root_dir, 'extraction'))
            os.makedirs(class_extraction_templ, mode=0o777, exist_ok=False)
            config.set('CLASSIFIER', 'EXTRACTION_TEMPLATE', class_extraction_templ)

            config.set('CLASSIFIER', 'GSM_MODEL_NAME', 'gsm_sim_unclassified.model')
            config.set('CLASSIFIER', 'CLASSIFICATION_FINAL_ACCURACY', '0.90')
            config.set('CLASSIFIER', 'DOC_SIMILIARITY_ACCURACY', '0.70')
            config.set('CLASSIFIER', 'SUPPORTED_FILE_EXTENSIONS', '.txt,.docx,.pdf,.jpg,.tiff,.jpeg,.bmp,.xls,.xlsx,.png,.doc')
            config.set('CLASSIFIER', 'SUPPORTED_IMG_FILE_EXT', '.jpg,.tiff,.jpeg,.bmp,.png')
            config.set('CLASSIFIER', 'GROUP_IDENTIFIER', '~~__~~')
            config.set('CLASSIFIER', 'PATH_SEP', '\\')

            config.set('CLASSIFIER', 'TESSERACT_INSTALLATION_LOC', 'C:\Program Files\Tesseract-OCR\\tesseract.exe')
            config.set('CLASSIFIER', 'VEC_MODEL_PKL_NAME', 'dfidfvec.pkl')
            config.set('CLASSIFIER', 'CLASS_PKL_NAME','model.pkl')
            config.set('CLASSIFIER', 'PDF_NO_OF_PAGES_READ', '1')

            config.set('CLASSIFIER', 'UNCLASS_GROUP_STATUS', 'Initiated')
            config.set('CLASSIFIER', 'NEW_TEMPLATE_STATUS', 'WaitingForTemplat')
            config.set('CLASSIFIER', 'MOVED_UNCLASSIFICATION_TEMPLATE_STATUS','Completed')
            config.set('CLASSIFIER', 'CLASSIFIER_ERROR_CODE', "1")
            config.set('CLASSIFIER', 'DATA_PROCESSING_ERROR_CODE', 2)
            config.set('CLASSIFIER', 'OCR_PROCESSING_ERROR_CODE', 3)
            config.set('CLASSIFIER', 'GROUPING_ERROR_CODE', 4)
            config.set('CLASSIFIER', 'SIM_ERROR_CODE', 5)
            config.set('CLASSIFIER', 'MOVE_TO_TEMPLATE_ERROR_CODE', 6)
            config.set('CLASSIFIER', 'DATA_EXTRACTOR_ERROR_CODE', 7)
            config.set('CLASSIFIER', 'FILE_AUTHENTICATION', 1)

            config.set('CLASSIFIER', 'API_HOST', server_name)
            config.set('CLASSIFIER', 'CLASSIFIER_API_NAME', 'classifier')
            if checkopenport(port_list[0]):
               config.set('CLASSIFIER', 'CLASSIFIER_API_PORT', port_list[0])
            elif checkopenport(port_list[len(port_list)-1] + 1):
                config.set('CLASSIFIER', 'CLASSIFIER_API_PORT', port_list[len(port_list)-1] + 1)
                port_list.append(port_list[len(port_list)-1] + 1)
            config.set('CLASSIFIER', 'TRAINING_API', 'training')
            if checkopenport(port_list[1]):
               config.set('CLASSIFIER', 'TRAINING_API_PORT', port_list[1])
            elif checkopenport(port_list[len(port_list)-1] + 1):
                config.set('CLASSIFIER', 'TRAINING_API_PORT', port_list[len(port_list)-1] + 1)
                port_list.append(port_list[len(port_list)-1] + 1)
            config.set('CLASSIFIER', 'DATA_EXTRACTION_API', 'extraction')
            if checkopenport(port_list[2]):
               config.set('CLASSIFIER', 'DATA_EXTRACTION_API', port_list[2])
            elif checkopenport(port_list[len(port_list)-1] + 1):
                config.set('CLASSIFIER', 'DATA_EXTRACTION_API', port_list[len(port_list)-1] + 1)
                port_list.append(port_list[len(port_list)-1] + 1)
            config.write(ini_file,space_around_delimiters=False)
            ini_file.close()

            return ini_file
    else:
        print('Issue with  input location')


if __name__ == '__main__':
    root_dir = r"\\192.168.0.14\DFX"
    #api_server =
    create_ini_file(root_dir,"localhost")
    #app.run(host=host, port=port, debug=True)