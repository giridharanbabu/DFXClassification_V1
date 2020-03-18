import configparser
from elasticsearch import Elasticsearch
from elasticsearch.connection import create_ssl_context
import ssl
config = configparser.ConfigParser()
config.read('config.ini')

es_host = config['CLASSIFIER']['ES_HOST']
es_port = config['CLASSIFIER']['ES_PORT']
index = config['CLASSIFIER']['INDEX']
doc_type = config['CLASSIFIER']['TYPE']

ssl_context = create_ssl_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE
es = Elasticsearch([{'host': es_host, 'port': es_port}],scheme="https",
                       # to ensure that it does not use the default value `True`
                       verify_certs=False,
                       ssl_context= ssl_context,
                       http_auth=("admin", "admin"))


def update_group_no(group_no,group_name):
    return {
        "doc":
            {
                "group_no": group_no,
                "group_name": group_name
            }
    }


def update_group_es(inbound_id,group_no):
    import json
    import os

    group_append = "Group_"
    name = str(group_append+group_no)
    print(name)
    es.update(index= index, doc_type= doc_type, id= inbound_id, body=update_group_no(group_no, name))
    return "updated_data in elasticsearch"
#update_group_es()



def update_model_details(parent,model,child):
    return {
        "doc":
            {
                "parent": parent,
                "model": model,
                "child": child
            }
    }


def update_trained_groups_by_model(inbound_id,parent,model,child):
    es.update(index= index, doc_type= doc_type, id= inbound_id, body=update_model_details(parent,model,child))
    return "updated model details"

