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


def get_group_name(group_name):
    connection = configurations.config(section='POSTGRESQL')
    newreq = dbprocess(connection)
    response = newreq.select(table_name='table_dfx_similiaritygroup', where_field={'name': {group_name}})
    for data in response:
        group_id = data['id']
    return group_id


def update_group(parent, model, child_name, group):
    parent_id = get_parent_id(parent)
    model_id = get_model_id(model)
    group_id = get_group_name(group)
    child_id = get_child_id(child_name)
    print(group_id)
    cur.execute("UPDATE public.table_dfx_similiaritygroup SET status= %s, parenttypeid= %s, modeltypeid= %s, childtypeid= %s  WHERE id= %s",("1", parent_id, model_id[0], child_id, str(group_id)))
    return "updated group"


def get_parent_id(parent):
    connection = configurations.config(section='POSTGRESQL')
    newreq = dbprocess(connection)
    response = newreq.select(table_name='table_dfx_parentmodeldetails', where_field={'name': {parent}})
    for data in response:
        parent_id = data['id']
    return parent_id


def get_model_id(model):
    list_all_id =[]
    connection = configurations.config(section='POSTGRESQL')
    newreq = dbprocess(connection)
    response = newreq.select(table_name='table_dfx_modeldetails', where_field={'name': {model}})
    for data in response:
        model_id = data['id']
        parent_id = data['parentmodelid']
    return model_id,parent_id
    #print(response)
    #return model_id,parent_id


#print(get_model_id("passport"))



def insert_parent_in_db(parent):
    connection = configurations.config(section='POSTGRESQL')
    newreq = dbprocess(connection)
    insert_response = newreq.insert(table_name='table_dfx_parentmodeldetails',
                                    values_list={'name': parent, 'displayname': parent, 'isnew': '1',
                                                 'trainedfilelocation': None, 'isactive': '0',
                                                 'createdtimestamp': sysdate, 'modifiedtimestamp': sysdate})
    # query = """INSERT INTO table_dfx_parentmodeldetails(id, name, displayname, isnew, trainedfilelocation, isactive, createdtimestamp, modifiedtimestamp) VALUES(%(id)s, %(name)s, %(displayname)s, %(isnew)s, %(trainedfilelocation)s, %(isactive)s, %(createdtimestamp)s, %(modifiedtimestamp)s);"""
    connection.close()
    return jsonify({"status":"ok"})


def insert_model_in_db(model, parent):
    connection = configurations.config(section='POSTGRESQL')
    newreq = dbprocess(connection)
    parent_id = get_parent_id(parent)
    insert_response = newreq.insert(table_name='table_dfx_modeldetails',
                                    values_list={'parentmodelid': parent_id, 'name': model, 'displayname': model,
                                                 'isnew': '1', 'trainedfilelocation': "None", 'isactive': '0',
                                                 'createdtimestamp': sysdate, 'modifiedtimestamp': sysdate})
    # query = """INSERT INTO table_dfx_parentmodeldetails(id, name, displayname, isnew, trainedfilelocation, isactive, createdtimestamp, modifiedtimestamp) VALUES(%(id)s, %(name)s, %(displayname)s, %(isnew)s, %(trainedfilelocation)s, %(isactive)s, %(createdtimestamp)s, %(modifiedtimestamp)s);"""
    connection.close()
    return jsonify({"status": "ok"})


def insert_child_in_db(parent, model, child):
    connection = configurations.config(section='POSTGRESQL')
    newreq = dbprocess(connection)
    parent_id = get_parent_id(parent)
    model_id = get_model_id(model)
    print(parent_id)
    print(model_id)
    insert_response = newreq.insert(table_name='table_dfx_childdodeldetails',
                                    values_list={'parentmodelid': parent_id, 'modelid': model_id[0], 'name': child,
                                                 'displayname': child, 'isnew': '1', 'trainedfilelocation': "None",
                                                 'isactive': '0', 'createdtimestamp': sysdate,
                                                 'modifiedtimestamp': sysdate})
    # query = """INSERT INTO table_dfx_parentmodeldetails(id, name, displayname, isnew, trainedfilelocation, isactive, createdtimestamp, modifiedtimestamp) VALUES(%(id)s, %(name)s, %(displayname)s, %(isnew)s, %(trainedfilelocation)s, %(isactive)s, %(createdtimestamp)s, %(modifiedtimestamp)s);"""
    connection.close()
    return {"status": "ok"}


def build_model_update(parent, model, child, group):
    connection = configurations.config(section='POSTGRESQL')
    newreq = dbprocess(connection)
    cur = connection.cursor()
    cur.execute("select exists(select id, name from table_dfx_parentmodeldetails where name = '" + parent + "');")
    parent_exists = [parent[0] for parent in cur.fetchall()]
    print(parent_exists)
    response={}
    if not parent_exists[0] or parent_exists == []:
        response = insert_parent_in_db(parent)
        response['type'] = 'type created'
        #return jsonify(response)
    elif parent_exists[0]:

        response['type_exists']="parent exists"
        cur.execute("select exists(select id, name from table_dfx_modeldetails where name = '" + model + "');")
        model_exists = [model[0] for model in cur.fetchall()]
        if not model_exists[0] or model_exists == []:
            response= insert_model_in_db(model, parent)

            response['model'] = 'model created and group updated'

        elif model_exists[0]:

            response['model_exists'] = "model exists"
            cur.execute("select exists(select id, name from table_dfx_childdodeldetails where name = '" + child + "');")
            child_exists = [child[0] for child in cur.fetchall()]
            if child_exists[0] == False or child_exists == []:
                response['created'] = "model created"
                response = insert_child_in_db(parent, model, child)
                update_group(parent, model, child, group)
                response['child'] = 'child created and group updated'
                #response = "child_created"
                #response= jsonify({'status':'Ok', 'response':'child created'})
                #return jsonify(response)
            elif child_exists[0]:
                update_group(parent, model, child, group)
                response['created'] = "model created"
                response['child_exist'] = "updated data child_exists no need to update"
                #response =jsonify( {'status': 'None', 'response': 'child not created  or already exists'})
                loguru.logger.info("child_exists no need to update")
                #return response
            else:
                response['error_child'] = "error updating the child"
        else:
            response['error_model']="error updating the model"
            #response = jsonify({'status': 'None', 'response': 'model not  created or already exists'})
           # return jsonify(response)
            loguru.logger.info("model not  created or already exists")
    else:
        response['error_type'] = "error updating the type"
        #response = jsonify({'status': 'None', 'response': 'type not  created or already exists'})
        loguru.logger.info("type not  created or already exists")
    connection.close()
    return response


def regenrate_group(parent, model, child, group):
    cur.execute("UPDATE public.table_dfx_similiaritygroup SET status= %s, parenttypeid= %s, modeltypeid= %s   WHERE name= %s",("1", None, None, group))
    response = build_model_update(parent, model, child, group)
    conn.close()
    return response


#print((regenrate_group("fudiciary","passport","ukpassport","Group_203")))



def get_publish_list():
    publish_group_list=[]
    connection = configurations.config(section='POSTGRESQL')
    newreq = dbprocess(connection)
    response = newreq.select(table_name='table_dfx_similiaritygroup', where_field={'status': {"1"}})
    #print(response)
    for group_list in response:
        #for group in group_list:
        child_name = get_child_name(group_list['childtypeid'])

        publish_group_list.append({"group_no":group_list['id'],"group_name":group_list['name'], "child_name": child_name})
    connection.close()
    return publish_group_list


# build_model_update('fudiciary','Birth_certificate','UK_birth_certificate','203')

def revoke_model(group_name):
    revoke_list=[]
    connection = configurations.config(section='POSTGRESQL')
    newreq = dbprocess(connection)
    group = get_group_name(group_name)
    cur.execute("UPDATE public.table_dfx_similiaritygroup SET parenttypeid= %s, modeltypeid= %s status= %s isreverted= %s WHERE id= %s",
                (None, None, "0", "1", group))
    response = newreq.select(table_name='table_dfx_similiaritygroup', where_field={'isreverted': {"1"}})
    for group_list in response:
        #for group in group_list:
        revoke_list.append({"group_id":group_list['id'],"group_name":group_list['name']})
    connection.close()
    return revoke_list


#print(revoke_model("Group_203"))
#print(update_group('fudiciary', 'passport', 'Group_204'))

def unclassified_doc_update(uri,probability_accuracy,text,group_no,grouplocation,filenameingroup):
    connection = configurations.config(section='POSTGRESQL')
    newreq = dbprocess(connection)
    insert_response = newreq.insert(table_name='table_dfx_unclassifieddetails',
                                    values_list={'isdeleted': '0','docuriid': uri,
                                                 'istrainingdocument': None, 'createdtimestamp': sysdate,
                                                  'modifiedtimestamp': sysdate,'accuracyrate': probability_accuracy,'matchingtext':text,'groupid':group_no, 'grouplocation':grouplocation, 'filenameingroup':filenameingroup})
    connection.close()
    return insert_response

#unclassified_doc_update("file//c:jhhef","0.7","new_doc","200")


def classified_doc_update (model,probability_accuracy,text,uri):
    connection = configurations.config(section='POSTGRESQL')
    newreq = dbprocess(connection)
    list_model_and_parent_id = get_model_id(model)

    insert_response = newreq.insert(table_name='table_dfx_classificationdetails',
                                    values_list={'parentmodelid': list_model_and_parent_id[1], 'modelid': list_model_and_parent_id[0],
                                                 'childmodelid': '0', 'noofgroups':'0', 'isreverted':'0', 'classifiedtimestamp': sysdate,
                                                 'modifiedtimestamp':None, 'accuracyrate': probability_accuracy,
                                                 'matchingtext': text, 'docuriid':uri})
    connection.close()
    return "updated_classification_details"

#classified_doc_update("passport","0.7","new_doc","file://jsdhb.txt")

def get_doc_count_by_group():
    cur.execute("SELECT count(groupid) as count, groupid FROM table_dfx_unclassifieddetails GROUP BY groupid")
    print(cur.fetchall())


def get_child_id(child_name):
    connection = configurations.config(section='POSTGRESQL')
    newreq = dbprocess(connection)
    response = newreq.select(table_name='table_dfx_childdodeldetails', where_field={'name': {child_name}})
    for data in response:
        child_id = data['id']
        return child_id

def get_child_name(child_id):
    connection = configurations.config(section='POSTGRESQL')
    newreq = dbprocess(connection)
    response = newreq.select(table_name='table_dfx_childdodeldetails', where_field={'id': {str(child_id)}})
    for data in response:
        child_name = data['name']
        return child_name


def get_model_name(model_id):
    connection = configurations.config(section='POSTGRESQL')
    newreq = dbprocess(connection)
    response = newreq.select(table_name='table_dfx_modeldetails', where_field={'id': {model_id}})
    for data in response:
        model_name = data['name']
        return model_name

def get_parent_name(parent_id):
    connection = configurations.config(section='POSTGRESQL')
    newreq = dbprocess(connection)
    response = newreq.select(table_name='table_dfx_parentmodeldetails', where_field={'id': {parent_id}})
    for data in response:
        parent_name = data['name']
        return parent_name


def get_group_details_for_publish(sub_class_name,status):
    publish_list=[]
    connection = configurations.config(section='POSTGRESQL')
    newreq = dbprocess(connection)
    response = newreq.select(table_name='table_dfx_similiaritygroup', where_field={'status': {status}})
    for data in response:
        print(data)
        child_name  = get_child_name(data['childtypeid'])
        model_name = get_model_name(data['modeltypeid'])
        parent_name = get_parent_name(data['parenttypeid'])
        publish_list.append({"parent_name": parent_name,"parent_id":data['parenttypeid'], "model_name": model_name,"model_id":data['modeltypeid'] ,"child_name":child_name,"child_id" :data['childtypeid']})

    return publish_list

#print(get_doc_count_by_group())

#print(get_group_details_for_publish('uk_passport',1))


def subclass_status(group_name):
    subclass_list = []
    connection = configurations.config(section='POSTGRESQL')
    newreq = dbprocess(connection)
    response = newreq.select(table_name='table_dfx_similiaritygroup', where_field={'name': {group_name}})
    for data in response:
        subclass_id= data['childtypeid']
        status = data['status']
        subclass_list.append({"subclass_id":subclass_id,"status":status})
    return subclass_list

#print(subclass_status("Group_10"))