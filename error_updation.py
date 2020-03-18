import urllib.parse
import configparser
from loguru import logger


config = configparser.ConfigParser()
config.read('config.ini')
system_config_all = config['CLASSIFIER']['DISCOVERY_API_HOST']
system_error_add_api = config['CLASSIFIER']['DISCOVERY_ERROR_LOG']
log_location = config['CLASSIFIER']['LOGGER_LOC']
#loginfo_filename = config['CLASSIFIER']['LOGINFO_FILENAME']
#logdebug_filename = config['CLASSIFIER']['LOGDEBUG_FILENAME']
headers = {'Content-Type': "application/json", 'cache-control': "no-cache"}

# logger.add(loginfo_filename, format="{time:YYYY-MM-DD at HH:mm:ss} | {level} | {message}", backtrace=True,
#            level='DEBUG', rotation="00:00", compression="zip", enqueue=True, diagnose=True)

def exception_log(e, inner_exception, model_id=''):
    import sys
    error_occurred_information = {'ErrorType': type(e).__name__, 'ErrorIdentity': str(e)+str(inner_exception), "info": sys.exc_info()}
    print(error_occurred_information)
    error = error_update_log_table(error_occurred_information, model_id=0)
    return error


def error_update_log_table(error_execution_information, model_id=0):
    import requests as req
    import json
    from datetime import datetime
    import socket
    hostname = socket.gethostname()
    ip_address = socket.gethostbyname(hostname)
    now = datetime.now()
    import time
    add_group_template = urllib.parse.urljoin(system_config_all, system_error_add_api)
    error_dictionary = {'ModelId': model_id,
                        'ExceptionDet': error_execution_information['ErrorType'],
                        'ExceptionDetMessage': error_execution_information['ErrorIdentity'],
                        'ErrorStatus': 'Open',
                        'CreatedBy': 'classifier '+":"+" "+ip_address,
                        'CreatedDateTime': time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()),
                        'ModifiedBy': 'Classifier',
                        'ModifiedDateTime': time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()),
                        'ErrorSource': 'Classifier',
                        "ModelName": "DiscoveryInBound",
                        "InnerExceptionDet": None,
                        "InnerExceptionDetMessage": None
                        }
    error_dictionary_json_data = json.dumps(error_dictionary)
    # print(error_dictionary_json_data)
    group_response_error_data = req.request(method="POST", url=add_group_template, data=error_dictionary_json_data,
                                            headers=headers)
    print ("/n/n./n//",group_response_error_data.status_code)


def custom_error_update_log(error_type,error_message, model_id):
    import requests as req
    import json
    from datetime import datetime
    import socket
    hostname = socket.gethostname()
    ip_address = socket.gethostbyname(hostname)
    now = datetime.now()
    import time
    add_group_template = urllib.parse.urljoin(system_config_all, system_error_add_api)
    error_dictionary = {'ModelId': model_id,
                        'ExceptionDet': error_type,
                        'ExceptionDetMessage': str(error_message),
                        'ErrorStatus': 'Open',
                        'CreatedBy': 'classifier ' + ":" + " " + ip_address,
                        'CreatedDateTime': time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()),
                        'ModifiedBy': 'Classifier',
                        'ModifiedDateTime': time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()),
                        'ErrorSource': 'Classifier',
                        "ModelName": "DiscoveryInBound",
                        "InnerExceptionDet": None,
                        "InnerExceptionDetMessage": None
                        }
    error_dictionary_json_data = json.dumps(error_dictionary)
    print("custom_error_update_log :",error_dictionary)
    logger.info("custom_error_update_log :",error_dictionary_json_data)
    error_log_req = req.request(method="POST", url=add_group_template, data=error_dictionary_json_data, headers=headers)
    logger.info("custom_error_update_log : group_resp :",error_log_req.status_code)
    return error_log_req.status_code
