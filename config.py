import requests as req
from time import gmtime, strftime
import json
import time
from flask import Flask
import os
import shutil
import configparser
from loguru import logger
import urllib.parse
from flask import jsonify

import error_updation
from error_updation import *

config = configparser.ConfigParser()
config.read('config.ini')
ini_archive_loc = config['CLASSIFIER']['INI_ARCHIEVE_LOC']
system_config_all = config['CLASSIFIER']['DISCOVERY_API_HOST']
sysytem_config_api= config['CLASSIFIER']['SYSTEM_CONFIG_API']
host = config['CLASSIFIER']['CLASSIFIER_HOST']
config_port = config['CLASSIFIER']['CONFIG_PORT']

logger.add("classifier_loginfo.log", format="{time:YYYY-MM-DD at HH:mm:ss} | {level} | {message}", backtrace=True ,  level='INFO' , rotation="00:00", compression="zip",enqueue=True ,diagnose=True  )
logger.add("classifier_debuglog.log", format="{time:YYYY-MM-DD at HH:mm:ss} | {level} | {message}", backtrace=True ,  level='DEBUG' , rotation="00:00", compression="zip",enqueue=True ,diagnose=True  )

dic_class = {'Config_file_created': "config_file created"}


app = Flask(__name__)
@app.route('/config_data', methods=['POST'])
def config_data():
    try:
        tmp_request_url = urllib.parse.urljoin(system_config_all,sysytem_config_api)
        resp = req.request(method='GET', url=tmp_request_url)
        Filename_config ='config_'+time.strftime("%Y-%m-%d %H%M%S")+'.ini'
        if os.path.exists('config.ini'):
            os.rename('config.ini', Filename_config)
            shutil.move(Filename_config, ini_archive_loc)
            logger.info("File renamed and moved")
        else:
            logger.debug("File not found")
        with open('config.ini', 'w+') as configuration:
            config_classifier = ('[CLASSIFIER]'+"\n")
            configuration.write(config_classifier)
            if resp and resp.status_code == 200:
                json_str_in_db = json.loads(resp.text)
                for json_str_values in json_str_in_db:
                    configuration_name = json_str_values['Name']
                    configuration_value = json_str_values["Value"]
                    config=(configuration_name+"="+configuration_value+"\n")
                    configuration.write(config)
        return json.dumps(dic_class['Config_file_created'])
    except Exception as e:

        error_updation.exception_log(e, "Error in config data", str(''))
        #logger.error("Error in config data {}", e)



'''
if __name__ == '__main__':
       app.run(host=host, port=config_port, debug=True)
'''
