# -*- coding: utf-8 -*-
"""
Created on Sun Jul 21 20:59:42 2019

@author: baskaran
"""

from datetime import datetime
import time
import os
from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask, jsonify
import os
import configparser

config = configparser.ConfigParser()
config.read('config.ini')
from loguru import logger
import shutil
import win32wnet
from apscheduler.schedulers.background import BackgroundScheduler
import time
import urllib.parse
import classifier_transactions
import error_updation

config = configparser.ConfigParser()
config.read('config.ini')
log_location = config['CLASSIFIER']['LOGGER_LOC']
loginfo_filename = config['CLASSIFIER']['LOGINFO_FILENAME']
logdebug_filename = config['CLASSIFIER']['LOGDEBUG_FILENAME']

logger.add(loginfo_filename, format="{time:YYYY-MM-DD at HH:mm:ss} | {level} | {message}", backtrace=True, level='INFO',
           rotation="00:00", compression="zip", enqueue=True, diagnose=True)
logger.add(logdebug_filename, format="{time:YYYY-MM-DD at HH:mm:ss} | {level} | {message}", backtrace=True,
           level='DEBUG', rotation="00:00", compression="zip", enqueue=True, diagnose=True)

running_status = 0
file_list_count = config['CLASSIFIER']['DISCOVERY_FILE_COUNT_PER_JOB']
get_file_info_request = urllib.parse.urljoin(config['CLASSIFIER']['DISCOVERY_API_HOST'],
                                             config['CLASSIFIER']['CALL_DISCOVERY_FILELIST']) + file_list_count
is_authenticated = config['CLASSIFIER']['FILE_AUTHENTICATION']
headers = {'Content-Type': "application/json", 'cache-control': "no-cache"}
app = Flask(__name__)


def find_ipaddress():
    import socket
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


def host_connection(host, username, password):
    # unc = ''.join(['\\\\', host])+"$"
    logger.info(" Host : {}, Username :{}, Password:{}", host, username, password)
    isconnected = False
    try:
        win32wnet.WNetAddConnection2(0, None, host, None, username, password)
        isconnected = True
    except Exception as err:
        logger.debug(" Problem with network connection and authetication: host_connection() ", err)
    return isconnected


def disconnect_host(host):
    try:
        win32wnet.WNetCancelConnection2(host, 0, 0)
    except Exception as err:
        logger.debug(" Problem with network connection and authetication: disconnect_host() ", err)


def call_classiciation():
    import requests as req
    import json
    import sys
    ipaddress_str = find_ipaddress()
    classifier_api = "http://%s:%s/%s" % (
        ipaddress_str, config['CLASSIFIER']['API_PORT_NUMBER'], config['CLASSIFIER']['CLASSIFIER_URL_NAME'])
    logger.debug(" \n\n IPAddress : {}", classifier_api)
    prediction_json = {}
    try:
        resp = req.request(method='GET', url=get_file_info_request)
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
                    payload['inbound_id'] = 0
                    payload['IsTrainingSource'] = 0
                    logger.debug("\n\n document: {}", document)

                    json_str = json.loads(document['Value'])
                    tmp_file_name = ''
                    discover_source_id = 0
                    dirpath = json_str.get("FileDirectoryName")
                    filefullpath = json_str.get("FileFullPath")
                    payload['file_name'] = filefullpath
                    payload['inbound_id'] = document['Id']
                    payload['IsTrainingSource'] = document['IsTrainingSource']
                    logger.debug(discover_source_id)

                    # auth_info = json_data['FileAccessValue'].split(",")
                    authinfo = json.loads(document['FileAccessValue'])
                    host = authinfo['ServerName']
                    if is_authenticated == 1:
                        username = authinfo['UserName']
                        pwd = authinfo['PassWord']
                        host_connection(dirpath, username, pwd)

                    logger.debug("\n\n FILE PATH: {}", filefullpath)
                    logger.debug("\n\n payload: {}", payload)
                    payload = json.dumps(payload)
                    reqst = req.request("POST", url=classifier_api, data=payload, headers=headers)
                    logger.debug("\n\n Connector reqst:", reqst)
                    if not reqst and reqst.status_code is not 200:
                        prediction_json["error_msg"] = "Classification service is down"
                        prediction_json['error_code'] = -1
                        classifier_transactions.update_inbound_status(document['Id'])
                        error_updation.custom_error_update_log(prediction_json,
                                                               "Classification service is down",
                                                               str(document['Id']))

                    # reqst_result = rest_response(reqst, classifier_api)
                    logger.debug("\n\n\ reqst_result: {}", reqst.status_code)

                    if is_authenticated == 1:
                        disconnect_host(host)
                except Exception as error:
                    continue
        else:
            time.sleep(5)
    except ConnectionError:
        pass


@app.route('/pause')
def pause_job():
    print("Pause")
    scheduler.pause()
    print(" Pause ->", scheduler.state)
    return jsonify("pause")


@app.route('/dfx_stop')
def stop_job():
    scheduler.remove_job(job_id='my_job_id')
    print(" Stop ->", scheduler.state)
    return jsonify("Stop")


@app.route('/resume')
def resume_job():
    print(" resume")
    scheduler.resume()
    print(" resume ->", scheduler.state)
    return jsonify("resume")


@app.route('/dfx_start')
def startScheduler():
    scheduler.add_job(call_classiciation, 'interval', seconds=1, id='my_job_id')
    import apscheduler
    print(" start ->", apscheduler.schedulers.base.STATE_STOPPED)
    if scheduler.state == apscheduler.schedulers.base.STATE_STOPPED:
        scheduler.start()
        print(" start ->", scheduler.state)
    return jsonify("start")
    print('Press Ctrl+{0} to exit'.format('Break' if os.name == 'nt' else 'C'))
    try:
        while True:
            time.sleep(2)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()


if __name__ == '__main__':
    scheduler = BackgroundScheduler()
    app.run(host=config['CLASSIFIER']['CLASSIFIER_HOST'], port=config['CLASSIFIER']['DFX_CONNECTOR_PORT'], debug=False,
            threaded=True)