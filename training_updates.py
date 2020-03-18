import configparser
import loguru
import psycopg2
from flask import request
from flask_cors import CORS
from loguru import logger
from time import gmtime, strftime

from flask import Flask, jsonify
import configurations
from datetime import datetime as dt
from dbprocess import dbprocess
sysdate = dt.now()

conn = psycopg2.connect(host="mldbes.datafabricx.com", database="DFX_Classification", user="postgres", password="admin")
conn.autocommit = True
cur = conn.cursor()


def get_training_data(model_id):
    group_list=[]
    connection = configurations.config(section='POSTGRESQL')
    newreq = dbprocess(connection)
    for id in model_id:
        response = newreq.select(table_name='table_dfx_similiaritygroup', where_field={'modeltypeid': id})
        #print(response)
        for data in response:
            group_id = data['id']
            model_id = data['modeltypeid']
            group_list.append((group_id,model_id))
    connection.close()
    return group_list

#print(get_training_data([5,1]))

def get_model_name(model_id):
    model_name_list=[]
    connection = configurations.config(section='POSTGRESQL')
    newreq = dbprocess(connection)
    response = newreq.select(table_name='table_dfx_modeldetails', where_field={'id': model_id})
    for data in response:
        model_name = data['name']
        #model_name_list.append(model_name)
    return model_name

def insert_training_details(starttime,endtime,trained_File_loc,model_path,vectormodel,accuracy):
    connection = configurations.config(section='POSTGRESQL')
    newreq = dbprocess(connection)
    insert_response = newreq.insert(table_name='table_dfx_trainingdetails',
                                    values_list={'modelid': 1, 'noofgroups': 1, 'isreverted': '0',
                                                 'groupdetails': "None", 'starttime': starttime,
                                                 'endtime': endtime, 'trainedfilelocation': trained_File_loc, "status":"1", "modifiedtimestamp":None, "model1filename":model_path, "model2filename":vectormodel, "modelfilelocation":"", "accuracyscore":accuracy, "f1score":0.9})
    connection.close()
    return jsonify({"status":"ok"})

def update_group_status(model_id):
    for id in model_id:
        cur.execute("UPDATE public.table_dfx_similiaritygroup SET status= %s  WHERE modeltypeid= %s",("3",id))
    #conn.close()
    return "updated group status"


