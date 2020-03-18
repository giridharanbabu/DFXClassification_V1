# -*- coding: utf-8 -*-
"""
Created on Wed Aug 14 16:43:10 2019

@author: baskaran
"""



config = configparser.ConfigParser()

config.read('config.ini')
log_location = config['CLASSIFIER']['LOGGER_LOC']
training_location = config['CLASSIFIER']['TRAINING_DATASET_LOCATION']
loginfo_filename = config['CLASSIFIER']['LOGINFO_FILENAME']
logdebug_filename = config['CLASSIFIER']['LOGDEBUG_FILENAME']

unclassified_group_file_loc = config['CLASSIFIER']['SIM_UNCLASSIFIED_GROUP']
unclassified_group_template_loc = config['CLASSIFIER']['SIM_TEMPLATE_GROUP']
classify_training_loc = config['CLASSIFIER']['TRAINING_DATASET_LOCATION']
max_training_doc = config['CLASSIFIER']['TRAINING_DOC_MAX']


group_status='Initiated'
group_in_training='InTraining'
unclass_status_completed='Completed'

import urllib.parse
move_groupto_training  = urllib.parse.urljoin(config['CLASSIFIER']['DISCOVERY_API_HOST'], config['CLASSIFIER']['MOVE_GROUPTO_TRAINING'])
get_subclass_template = urllib.parse.urljoin(config['CLASSIFIER']['DISCOVERY_API_HOST'],config['CLASSIFIER']['SELECT_SUBCLASS_TEMPLATE_BYID'])
get_unclassified_group = urllib.parse.urljoin(config['CLASSIFIER']['DISCOVERY_API_HOST'],config['CLASSIFIER']['SELECT_UNCLASS_BYGROUPID'])
update_unclass_training =  urllib.parse.urljoin(config['CLASSIFIER']['DISCOVERY_API_HOST'],config['CLASSIFIER']['UPDATE_UNCLASS_TRAINING'])
update_group_move_completed =  urllib.parse.urljoin(config['CLASSIFIER']['DISCOVERY_API_HOST'],config['CLASSIFIER']['UPDATE_GROUP_MOVE_COMPLETED'])
update_subclass_active =  urllib.parse.urljoin(config['CLASSIFIER']['DISCOVERY_API_HOST'],config['CLASSIFIER']['UPDATE_SUBCALSS_ACTIVE'])
get_inbound_byid =  urllib.parse.urljoin(config['CLASSIFIER']['DISCOVERY_API_HOST'],config['CLASSIFIER']['GET_INBOUND_BYID'])
update_inbound_api = urllib.parse.urljoin(config['CLASSIFIER']['DISCOVERY_API_HOST'],config['CLASSIFIER']['UPDATE_INBOUND'])
get_training_data_api = urllib.parse.urljoin(config['CLASSIFIER']['DISCOVERY_API_HOST'],config['CLASSIFIER']['GET_TRAINING_DATA_API'])

headers = { 'Content-Type': "application/json", 'cache-control': "no-cache" }
get_headers = {}


def get_file_name(file_path):
    filename = ''
    if len(file_path) > 1:
         filename = os.path.splitext(os.path.basename(file_path))[0]
    return str(filename)


def get_file_ext(file_path):
    if len(file_path) > 1:
         ext  = os.path.splitext(os.path.basename(file_path))[1]
    return str(ext)


def  move_group(token):
    import shutil
    from os import walk
    import os
    import requests as req
    from time import gmtime, strftime
    move_group_dict = {}
    logger.info(" move_group :{}")
    get_headers['Authorization'] = token
    headers['Authorization']=token
     # try:
    group_reqst = req.request(method='GET', url=move_groupto_training + group_status , headers=get_headers)
    group_reqst_data = group_reqst.json()
    move_group_dict['error_msg'] = ''
    move_group_dict['moved_group'] = []
    is_training_require = False
    import shutil
    print(" move_group group_reqst_data :{}",group_reqst_data)
    if group_reqst and group_reqst.status_code == 200 and group_reqst_data is not None:
        for group in group_reqst_data:
            group_porcess_error = 0
            group_id = group['Id']
            get_training_data_url = get_training_data_api + str(group_id) + "&count=" + str(max_training_doc)
            group_unclassified_reqst = req.request(method='GET', url=get_training_data_url, headers=get_headers)
            unclassified_training_data = group_unclassified_reqst.json()
            subtemplate_id = group['SubClassificationTemplateId']
            logger.debug(" group_id : {}, subtemplate_id:{}", group_id, subtemplate_id)
            subclass_template_reqst = req.request(method='GET', url=get_subclass_template + str(subtemplate_id), headers=get_headers)
            if group_unclassified_reqst and group_unclassified_reqst.status_code == 200 and  subclass_template_reqst.json() is not None and subclass_template_reqst and subclass_template_reqst.status_code == 200 and  subclass_template_reqst.json() is not None:
                subclass_template_reqst_data = subclass_template_reqst.json()
                new_category_name = subclass_template_reqst_data['Name']
                new_dir_name = os.path.normpath(os.path.join(classify_training_loc, new_category_name))
                #remove_train_dir = os.path.normpath(os.path.join(unclassified_group_template_loc,str(group_id)))
                if not os.path.exists(new_dir_name):
                    os.makedirs(new_dir_name, mode=0o777, exist_ok=True)
                for training_data in unclassified_training_data:
                    source_file_name = training_data['FileLocation']
                    inbound_id =  training_data['DiscoveryInBoundId']
                    id = training_data['Id']
                    import ntpath
                    destination = os.path.normpath(os.path.join(classify_training_loc,new_category_name,ntpath.basename(source_file_name)))
                    if os.path.exists(source_file_name) and not os.path.exists(destination) and os.path.exists(new_dir_name):
                        shutil.move(source_file_name,new_dir_name)
                        if os.path.exists(destination):
                            training_data["IsTrainingDocument"] = 1
                            training_data["FileLocation"] = destination
                            training_data["Content"]= None
                            training_data["ContentDisplay"] = None
                            training_data["ModifiedBy"]="classifier"
                            sysdate = strftime("%Y-%m-%d %H:%M:%S", gmtime())
                            training_data["ModifiedDateTime"] = sysdate
                            training_data["ClassificationStatus"] = None
                            payload = json.dumps(training_data)
                            req.request("POST", url=update_unclass_training, data=payload, headers=headers)
                        else:
                            classifier_transactions.update_unclassifier_error_status(id,token)
                            exception_log('Failed in training',
                                          'Destination path not exists ' + destination ,
                                          inbound_id)
                    else:
                        classifier_transactions.update_unclassifier_error_status(id,token)
                        exception_log('Failed in training', 'Please check the source -'+source_file_name+'  , destination path - '+destination+' and  new directory -'+new_dir_name ,inbound_id )
                group['Status'] = group_in_training
                payload = json.dumps(group)
                group_status_update_rqst = req.request("POST", url=update_group_move_completed, data=payload,
                                                       headers=headers)
                if group_status_update_rqst and group_status_update_rqst.status_code == 200:
                    move_group_dict['moved_group'].append(str(group_id))
                    is_training_require=True
            else:
                exception_log('Failed in training',' failed to process group for training' + str(group_id))
    else:
        exception_log('Failed in training', ' failed to get group details for training' + move_groupto_training + group_status )
    # except Exception as error:
    #     exception_log('Failed in training', ' failed to get group details for training' +str(error))
    return is_training_require


def update_groupto_category(token):
    import shutil
    from os import walk
    import os
    import requests as req
    logger.info(" move_group :{}")
    update_training_group = {}
    get_headers['Authorization'] = token
    headers['Authorization']=token
    try:
        group_reqst = req.request(method='GET', url=move_groupto_training + group_in_training, headers=get_headers)
        group_reqst_data = group_reqst.json()
        update_training_group['error_msg'] = ''
        update_training_group['moved_group'] = []
        print(" update_groupto_category GROUP :{}",group_reqst_data)
        if group_reqst and group_reqst.status_code == 200 and group_reqst.json() is not None:
            for group in group_reqst_data:
                group_id = group['Id']
                group_unclassified_reqst = req.request(method='GET', url=get_unclassified_group + str(group_id),headers=get_headers)
                unclass_reqst_data = group_unclassified_reqst.json()
                logger.debug(" \n \n unclass_reqst_data: {}", unclass_reqst_data)
                if group_unclassified_reqst and group_unclassified_reqst.status_code == 200 and unclass_reqst_data is not None:
                    for unclass_rec in unclass_reqst_data:
                        if int(unclass_rec['IsTrainingDocument']) == 1:
                            inbound_id = unclass_rec['DiscoveryInBoundId']
                            payload=None
                            #inbound_req = req.request("POST", url=update_inbound_api+str(inbound_id)+"&status=Open", data=payload, headers=headers)
                            unclass_rec["IsDeleted"] = 1
                            unclass_rec["ClassificationStatus"] = None
                            payload = json.dumps(unclass_rec)
                            unclass_rec_request = req.request("POST", url=update_unclass_training, data=payload, headers=headers)
                            logger.debug(" \n \n unclass_rec_request: {}", unclass_rec_request.status_code)
                subtemplate_id = group['SubClassificationTemplateId']
                logger.debug(" \n \n subtemplate_id: {}", subtemplate_id)
                subclass_template_reqst = req.request(method='GET', url=get_subclass_template + str(subtemplate_id), headers=get_headers)
                if subclass_template_reqst and subclass_template_reqst.status_code == 200 and subclass_template_reqst.json() is not None:
                    subclass_template_reqst_data = subclass_template_reqst.json()
                    subclass_template_reqst_data["IsActive"] = 1
                    subclass_template_reqst_data["IsNew"] = 0
                    class_id = subclass_template_reqst_data["ClassificationTemplateId"]
                    logger.debug(" \n \n subclass_template_reqst_data : class_id: {}", class_id)
                    payload_active = json.dumps(subclass_template_reqst_data)
                    update_subclass_rest = req.request("POST", url=update_subclass_active, data=payload_active, headers=headers)
                    logger.debug(" \n \n update_subclass_rest : class_id: {}", update_subclass_rest.status_code)
                    update_classification_isnew(class_id,token,is_new=0,is_active=1)
                group["Status"] = "Completed"
                payload = json.dumps(group)
                req.request("POST", url=update_group_move_completed, data=payload, headers=headers)
            update_training_group['move_msg'] = ' After Training Group status is updated successfully '
        else:
            update_training_group['error_msg'] = 'Please check the rest point fo: ' + move_groupto_training + group_status
    except Exception as error:
        print(" Error occurred in update completed status in group', error :", str(error))
    return update_training_group

#
# if __name__ == "__main__":
#    print(update_groupto_category())
