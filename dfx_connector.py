# -*- coding: utf-8 -*-
"""
Created on Sun Jul 21 20:59:42 2019

@author: baskaran
"""

from datetime import datetime
import time
import os
from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask,jsonify
import os
import configparser
import logging
from loguru import logger
import shutil
from apscheduler.schedulers.background import BackgroundScheduler
import time
import urllib.parse
import classifier_transactions
import error_updation
import dfx_security
import socket

config = configparser.ConfigParser()
config.read('config.ini')
log_location = config['CLASSIFIER']['LOGGER_LOC']
loginfo_filename = config['CLASSIFIER']['LOGINFO_FILENAME']
logdebug_filename = config['CLASSIFIER']['LOGDEBUG_FILENAME']


running_status = 0
file_list_count = config['CLASSIFIER']['DISCOVERY_FILE_COUNT_PER_JOB']
get_file_info_request  = urllib.parse.urljoin(config['CLASSIFIER']['DISCOVERY_API_HOST'], config['CLASSIFIER']['CALL_DISCOVERY_FILELIST'])+file_list_count
unclassifier_api = urllib.parse.urljoin(config['CLASSIFIER']['DISCOVERY_API_HOST'], config['CLASSIFIER']['UNCLASSIFIED_2_CLASSIFICATION_API'])
is_authenticated = config['CLASSIFIER']['FILE_AUTHENTICATION']


headers={}
headers['Content-Type'] = "application/json"
headers['cache-control'] = "no-cache"
headers['Authorization'] = None
get_headers = {}
token = ''
app = Flask(__name__)
sec_token = dfx_security.get_security_token()


def find_ipaddress():
    socket_str = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    ipaddress = ''
    try:
        # doesn't even have to be reachable
        socket_str.connect(('10.255.255.255', 1))
        ipaddress = socket_str.getsockname()[0]
    except:
        ipaddress = '127.0.0.1'
    finally:
        socket_str.close()
    return ipaddress


def is_port_open(ip,port):
   soc_ket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
   try:
       soc_ket.connect((ip, int(port)))
       soc_ket.shutdown(2)
       return True
   except:
      return False


def connect_classification(payload):
    import requests as req
    import json
    try:
        ipaddress_str = find_ipaddress()
        classifier_api = "http://%s:%s/%s" % (
                    ipaddress_str, config['CLASSIFIER']['API_PORT_NUMBER'], config['CLASSIFIER']['CLASSIFIER_URL_NAME'])
        # classifier_api="http://192.168.0.21:3535/classifier"
        payload = json.dumps(payload)
        class_headers = {'Content-Type': "application/json", 'cache-control': "no-cache"}
        reqst = req.request("POST", url=classifier_api, data=payload, headers=class_headers)
        print("classifier_api:",classifier_api ,payload )
        logger.debug("\n\n Connector reqst:", reqst)
        if not reqst and reqst.status_code is not 200:
            classifier_transactions.update_inbound_status(payload['inbound_id'])
            error_updation.custom_error_update_log( "Classification service is down",
                                                   "Classification service is down",
                                                   str(payload['inbound_id']))
        # reqst_result = rest_response(reqst, classifier_api)
        logger.debug("\n\n\ reqst_result: {}", reqst.status_code)
    except Exception as error:
        error_updation.exception_log(" Classification API request issue ", " Classification API request issue ", str(payload['inbound_id']))
    return reqst.status_code


def call_classiciation():
    import requests as req
    import json
    import sys
    prediction_json = {}
    try:
        payload = {}
        payload['file_name'] = None
        payload['inbound_id'] = 0
        payload['IsTrainingSource'] = 0
        payload['is_unclassified'] = 1
        payload['Authorization'] = sec_token
        payload['FileLength'] = 0
        print('sec_token  -- >',sec_token)
        get_headers['Authorization'] = sec_token
        ipaddress_str = find_ipaddress()
        port = config['CLASSIFIER']['API_PORT_NUMBER']
        # ipaddress_str = '192.168.0.13'
        # port = 3535
        if is_port_open(ipaddress_str,port) :
            print("\n unclassifier_api", unclassifier_api, ' get_headers',get_headers)
            unclass_resp = req.request(method='GET', url=unclassifier_api , headers=get_headers)
            unclass_data = unclass_resp.json()
            print("\n\n unclass_data :", unclass_data)
            logger.debug("\n\n unclass_data: {}", unclass_data)
            if unclass_resp and unclass_resp.status_code == 200 and unclass_data is not None and len(unclass_data) > 0:
                payload['unclass_id'] = unclass_data['Id']
                payload['file_name'] = unclass_data['FileLocation']
                payload['inbound_id'] = unclass_data['DiscoveryInBoundId']
                payload['IsTrainingSource'] = 0
                payload['FileLength'] = unclass_data['FileLength']
                print(" \n\n Inclassification : payload", payload)
                connect_classification(payload)
            else:
                print("\n classifier_api", get_file_info_request, 'get_headers',get_headers)
                resp = req.request(method='GET', url=get_file_info_request, headers=get_headers)
                discovery_file_details = resp.json()
                logger.debug(" \n\n json_data: {} ", discovery_file_details)
                if resp and resp.status_code == 200 and discovery_file_details is not None and len(discovery_file_details) > 0:
                    logger.debug(" \n\n template_details : {}", discovery_file_details)
                    reqst_result = []
                    for document in discovery_file_details:
                        try:
                            running_status = 1
                            payload = {}
                            payload['file_name'] = None
                            payload['unclass_id'] = 0
                            payload['inbound_id'] = 0
                            payload['IsTrainingSource'] = 0
                            payload['is_unclassified'] = 0
                            payload['Authorization'] = sec_token
                            logger.debug("\n\n document: {}", document)
                            json_str = json.loads(document['Value'])
                            crm_file_name = ''
                            discover_source_id = 0
                            dirpath = json_str.get("FileDirectoryName")
                            payload['inbound_id'] = document['Id']
                            # payload['IsTrainingSource'] = document['IsTrainingSource']
                            payload['IsTrainingSource'] = 0
                            payload['FileLength'] = json_str.get("FileLength")
                            if document['SourceTag'] == 'CRM' and json_str.get("FileFullPath") is not None and json_str.get("FileFullPath").strip() != '' and json_str.get("Annotationid").strip() != '' :
                                print("\n FileFullPath :", json_str.get("FileFullPath"))
                                crm_document_reqst = req.request(method='GET', url=json_str.get("FileFullPath"))
                                crm_document_data = crm_document_reqst.json()
                                if crm_document_reqst and crm_document_reqst.status_code == 200 and crm_document_data is not None and len(crm_document_data) > 0 and os.path.exists(
                                str(crm_document_data[0]['FileDownloadPath'])):
                                    print("crm_document_data", crm_document_data)
                                    payload['file_name'] =  str(crm_document_data[0]['FileDownloadPath'])
                                else:
                                    error_updation.exception_log(" CRM Request : Unable to locate document ",
                                                                 "  CRM Request : Unable to locate document ",
                                                                 str(document['Id']))
                            else:
                                payload['file_name'] = json_str.get("FileFullPath")
                            logger.debug(discover_source_id)
                            logger.debug("\n\n payload: {}", payload)
                            connect_classification(payload)
                        except Exception as error:
                            error_updation.exception_log(" Classification API request issue ",
                                                         "  Classification API service is down ", str(payload['inbound_id']))
                else:
                    time.sleep(10)
        else:
            error_updation.exception_log(" Classification API service is down ", " ", str(0))
            time.sleep(10)
    except ConnectionError:
        pass


@app.route('/pause') 
def pause_job():  
     print("Pause" )
     scheduler.pause()
     print(" Pause ->", scheduler.state)
     return jsonify("pause")


@app.route('/dfx_stop') 
def stop_job():
    scheduler.remove_job(job_id='my_job_id')
    print(" Stop ->" , scheduler.state)
    return jsonify("Stop")


@app.route('/resume') 
def resume_job():
    print(" resume" )
    scheduler.resume()
    print(" resume ->" , scheduler.state)
    return jsonify("resume")


@app.route('/dfx_start') 
def startScheduler():
    time.sleep(30)
    scheduler.add_job(call_classiciation, 'interval', seconds=1, id='my_job_id')
    import  apscheduler
    print(" start ->" , apscheduler.schedulers.base.STATE_STOPPED)
    if scheduler.state == apscheduler.schedulers.base.STATE_STOPPED:
        scheduler.start()
        print(" start ->" , scheduler.state)
    return jsonify("start")
    print('Press Ctrl+{0} to exit'.format('Break' if os.name == 'nt' else 'C'))
    try:
        while True:
            time.sleep(10)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()


if __name__ == '__main__':
    scheduler = BackgroundScheduler()
    # call_classiciation()
    app.run(host=config['CLASSIFIER']['CLASSIFIER_HOST'], port=config['CLASSIFIER']['DFX_CONNECTOR_PORT'], debug=False, threaded = True)