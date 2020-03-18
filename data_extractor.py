import csv
import json
import re
import configparser
from loguru import logger

import error_updation
from error_updation import *


config = configparser.ConfigParser()
config.read('config.ini')
log_location = config['CLASSIFIER']['LOGGER_LOC']

def extract_value(search_pre_str, search_post_str, raw_text):
    search_str = ''
    try:
        if len(raw_text.strip()) >= 1 and search_pre_str is not None and search_post_str is not None and raw_text is not None:
            value = re.search(search_pre_str + '(.*)' + search_post_str + '(.*)', raw_text)
            search_str = value.group(1)
    except Exception as e:
        error_updation.exception_log(e, "extract_value exception:", str(search_pre_str))
        #logger.debug(" extract_value exception:", e)
    logger.debug(" search_str: {}", search_str)

    return search_str


def processing_template(csvfile, input_txtfile, out_json_file):
    try:
        import csv
        with open(input_txtfile, "r+", errors='ignore',
                  encoding='utf-8') as f:
            new_data = f.read().replace("\n", ' ')
        csvfile = open(csvfile, 'r')
        reader = csv.DictReader(csvfile)
        reader.fieldnames = ("field", "begin", "end")
        final_out = {}
        for row in reader:
            final_out[row["field"]] = extract_value(row["begin"], row["end"], new_data).strip()
        csvfile.close()
        with open(out_json_file, "w+", encoding='utf-8') as jsonfile:
            jsonfile.write(json.dumps(final_out))
        logger.info("processing_template , JSON : {}", jsonfile)
    except Exception as error:
        error_updation.exception_log(error, "Error in data extraction", str('input_txtfile') )
        #logger.debug(" Error in data extraction, Error :", error)

    return out_json_file

