from flask import render_template
from classification import *
from flask import Flask, redirect, url_for, jsonify
import urllib.parse
from loguru import logger
from flask_cors import CORS
config = configparser.ConfigParser()
config.read('config.ini')
#print("config:", config)
log_location = config['CLASSIFIER']['LOGGER_LOC']
log_name = os.path.normpath(os.path.join(log_location, "classifier_log.log"))
loginfo_filename = config['CLASSIFIER']['LOGINFO_FILENAME']
logdebug_filename = config['CLASSIFIER']['LOGDEBUG_FILENAME']
host = config['CLASSIFIER']['CLASSIFIER_HOST']
service_port = config['CLASSIFIER']['SERVICE_PORT']
port_check = config['CLASSIFIER']['PORT_CHECK']
port_check_api = config['CLASSIFIER']['PORT_CHECK_API']
classifier = config['CLASSIFIER']['CLASSIFIER_URL_NAME']
start_classifier = config['CLASSIFIER']['START_CLASSIFIER']
stop = config['CLASSIFIER']['STOP_CLASSIFIER']
start_training = config['CLASSIFIER']['START_TRAINING']
ml_service_status = config['CLASSIFIER']['ML_SERVICE_STATUS']
training = config['CLASSIFIER']['TRAINING_URL']
classification_port = int(config['CLASSIFIER']['API_PORT_NUMBER'])
training_port = int(config['CLASSIFIER']['TRAINING_PORT'])

get_file_info_response = urllib.parse.urljoin('http://', port_check_api+":"+str(classification_port)+"/"+classifier)
import datetime
from datetime import timedelta
import os
#loginfo_filename =r'\\192.168.0.14\\dfx\\logs\\classifier_loginfo.log'
#logdebug_filename =r'\\192.168.0.14\\dfx\\logs\\classifier_debuglog.log'

logger.info("Classifier:", config['CLASSIFIER'])

service_dict = {'Training_status': "Alert! Training process is running, Cannot start Classification",
                'classification_port_status': "Classification Started Successfully",
                'training_port_status': "Training Started Successfully",
                'Classification_started': "Classification Started",
                'Training_started': "Training Started",
                'Nothing_status': "Process Already Stopped",
                'Invalid_pid': "Invalid Pid / Pid return 0",
                'Stop_process': "Classification Process Stopped Successfullyq",
                'classification_port_status_while_training': "Alert! Classification Process is Running, Cannot start Training"
                }

app = Flask(__name__)
CORS(app)



@app.route('/'+config['CLASSIFIER']['START_CLASSIFIER'], methods=['GET'])
def start():

    try:
        port_opened_training = isOpen(training_port)
        if port_opened_training is True:
            return jsonify({"status": "Alert! Training process is running, Cannot start Classification"})
        else:
            check_training_port = isOpen(classification_port)
            logger.debug("classification port status {}", check_training_port)
            if check_training_port is True:
                return jsonify({"status": "Classification Started Successfully"})
            elif check_training_port is False:
                import subprocess
                from subprocess import call
                return str(subprocess.call(["python", "classification.py"], shell=False))
                
                
    except Exception as e:
        logger.error("Exception occurred in Starting classification {}", e)
    
    return "OK"
    #return str(subprocess.call(["python", "classification.py"], shell=False))






@app.route('/'+config['CLASSIFIER']['START_TRAINING'], methods=['GET'])
def start_training():
    try:
        from subprocess import call
        check_classfication_port = isOpen(classification_port)
        if check_classfication_port is True:
            return jsonify({ "status":"Alert! Classification Process is Running, Cannot start Training"})
        else:
            check_training_port = isOpen(training_port)
            logger.debug("training port status {}", check_training_port)
            if check_training_port is True:

                return jsonify({"status":"Training Started Successfully"})
            else:
                import subprocess
                from subprocess import call
                
                str(subprocess.call(["python", "training.py"], shell=False))
                #call(["python", "training.py"])


        return jsonify({"status":"Training Started"})

    except Exception as e:
        logger.error("Exception occurred in Starting Training {}", e)
    return "Ok", 200




def isOpen(port):
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.connect((port_check, int(port)))
        s.shutdown(2)
        return True
    except Exception as e:
        return False


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




@app.route('/stop_training')
def stop_training():
    import os
    import signal
    response_list = [405, 500, 400, 200, 404]
    connection_status = isOpen(training_port)
    print(connection_status)
    if connection_status is True:
        pid_opened = address_to_pid(host, training_port)
        print(pid_opened)
        if pid_opened == 'Nothing':
            return jsonify({ "status":"Process Already Stopped"})
        elif pid_opened < 0 or pid_opened  is None :
            return jsonify({ "status":"invalid id"})
        elif pid_opened is not None and pid_opened == 0:
            return 'invalid PID 0'
                #     os.kill(pid_opened, signal.SIGTERM)
                #     return "invalid PID 0"
        else:
            os.kill(pid_opened, signal.SIGTERM)
            print("Process Stopped")

    else:
        return jsonify({ "status": "Process Already Stopped"})

    return  jsonify({ "status": "OK Process Stopped"})


@app.route('/'+config['CLASSIFIER']['STOP_CLASSIFIER'], methods=['GET'])
def stop():
    import os
    import signal
    try:
        response_list = [405, 500, 400, 200, 404]
        time = 0
        import requests
        response = requests.post(get_file_info_response)
        logger.info("classifier response {}", response)
        timer = 0
        pid_opened = address_to_pid(host, classification_port)
        if response.status_code in response_list:
            connection_status = isOpen(classification_port)
            if connection_status :
                pid_opened = address_to_pid(host, classification_port)
                print(pid_opened)
                if pid_opened is not None and pid_opened == 'Nothing':
                    return jsonify({ "status": "Classification Process Stopped Successfully" })
                elif pid_opened is None or pid_opened <= 0:
                    return jsonify({"status": "Invalid Pid / Pid return 0" })
                else:
                    os.kill(pid_opened, signal.SIGTERM)
                    return jsonify({ "status": "Classification Process Stopped Successfully" })
            elif not connection_status :
                return jsonify({ "status": "Classification Process Stopped Successfully" })
            else:
                os.kill(pid_opened, signal.SIGTERM)
                return jsonify({ "status": "Process Stopped Successfully" })

           #return json.dumps(service_dict['Nothing_status'])

        return jsonify({ "status": "Classification Process Stopped Successfully" })
    except Exception as e:
        logger.error("Exception occurred in stopping classifier {}", e)


def clasification_status():
    classification_service = isOpen(classification_port)
    if classification_service :
        return True
    else:
        return False


def training_status():
    training_service = isOpen(training_port)
    if not training_service :
        return False
    else:
        return True


@app.route('/'+config['CLASSIFIER']['ML_SERVICE_STATUS'], methods=['GET'])
def ml_service_status():
    try:
        classifier_status = clasification_status()
        train_status = training_status()
        return jsonify({"classifier_status":classifier_status, "training_status":train_status})

    except Exception as e:
        return ("Exception occurred in service_status {}", e)


@app.route('/'+config['CLASSIFIER']['TRAINING_URL'], methods=['GET'])
def training():
    try:
        import urllib.parse
        import requests
        import urllib.request
        #training_url = (urllib.parse.urljoin('http://','+":"+str(training_port)))
        #trainig_url = urllib.request.urlopen("http://"+config['CLASSIFIER']['IP_ADDRESS']+":"+str(training_port)+"/"+"training")
        trainig_url = "http://"+config['CLASSIFIER']['CLASSIFIER_IP_DFX']+":"+str(training_port)+"/"+config['CLASSIFIER']['TRAINING_URL']
        trainig_url = urllib.request.urlopen(trainig_url)
        
        return jsonify("model_trained and stopped")
        
    except Exception as e:
        return ("Exception occurred in service_status {}", e)
            

if __name__ == '__main__':
    print("host:",host,"port:",service_port)
    app.run(host=host, port=service_port, debug=False)