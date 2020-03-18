import werkzeug
from flask import Flask, jsonify
import configparser
import json
from flask import request
from elasticsearch import Elasticsearch
from flask_restplus import Api, Resource
from flask_cors import CORS
from loguru import logger
from build_models import build_model_update
from build_models import get_publish_list
from build_models import regenrate_group
from build_models import revoke_model
from build_models import get_group_details_for_publish
from build_models import subclass_status
from train import build_model
app = Flask(__name__)

logger.add("model{time}.log", rotation="10 min")
@app.errorhandler(werkzeug.exceptions.BadRequest)
def handle_bad_request(e):
    return 'bad request!', 400


CORS(app)

api = Api(app, openapi='3.0.0', title='Models',
          description='''1. Models--->Filter classification model with its parent and subtype 2.Groups---> Filter Groups''')
ns = api.namespace('classificationengine')

config = configparser.ConfigParser()
config.read('config.ini')
es_host = config['CLASSIFIER']['ES_HOST']
es_port = config['CLASSIFIER']['ES_PORT']
index = config['CLASSIFIER']['INDEX']
doc_process_count = config['CLASSIFIER']['DOCUMENT_COUNT']
unclassified_doc = 'classified'
es = Elasticsearch([{'host': es_host, 'port': es_port}])

''''''


def query_filter_model(model_name, inner_type_field):
    return {
        "query": {
            "bool": {
                "should": [
                    {"match": {"model": model_name}}
                ]
            }
        },
        "aggs":
            {
                "by_subtype":
                    {
                        "terms": {
                            "field": inner_type_field
                        }
                    }
            }
    }


# This gives the aggregation count for the pretrained models available and its associated Parent[Type] ,
# Model-Id [model_id] is also listed
def aggregation_for_model():
    return {
        "size": 0,
        "aggs": {
            "my_buckets": {
                "composite": {
                    "sources": [
                        {"model": {"terms": {"field": "model.keyword"}}},
                        {"type": {"terms": {"field": "type"}}},
                        {"model_id": {"terms": {"field": "model_id"}}}
                    ]
                }
            }
        }
    }


# This query retrieves all the inner-subtype[child] for the given [model_id]
def filter_model_by_id(model_id):
    return {
        "size": 0,
        "query": {
            "bool": {
                "should": [
                    {"match": {"model_id": model_id}}
                ]
            }
        },
        "aggs":
            {
                "by_subtype":
                    {
                        "terms": {
                            "field": "child.keyword"
                        }
                    }
            }
    }


# This aggregated query retrieves the group-id with its document count each group
def aggregate_count_by_group():
    return {
        "size": 0,
        "aggs":
            {
                "by_subtype":
                    {
                        "terms": {
                            "field": "GroupNo"
                        }
                    }
            }
    }

def aggregated_model_keyword():
    return {  "size":0,
        "aggs":
                {
                    "by_subtype":
                        {
                            "terms": {
                                "field": "model.keyword"
                            }
                        }
                }
    }


# This query fetches random document for the specific model-id and child-id
def filter_by_child_id(model_id, child_id):
    return {
        "size": 1,
        "_source": ["uri", "model", "type", "child"],
        "query": {
            "function_score": {
                "query":
                    {
                        "bool": {
                            "must": [
                                {"term": {"model_id": model_id}}

                            ],
                            "filter": [
                                {"term": {"child_model_id": child_id}}

                            ]
                        }
                    },

                "random_score": {}
            }

        }
    }


# This query fetches random document from the group for the given group-id
def doc_filter_by_group_id(group_id):
    return {"size": 1,
            "query": {
                "function_score": {
                    "query": {
                        "bool": {
                            "should": [
                                {"match": {"GroupNo": group_id}}
                            ]
                        }
                    },
                    "random_score": {}
                }

            }
            }


# To get the overall available type[parent] and subtype[model] count from the documents
def getmodel_list():
    return {
        "size": 0,
        "query": {
            "match_all": {}
        },
        "aggs": {
            "my_buckets": {
                "composite": {
                    "sources": [
                        {
                            "type": {
                                "terms": {
                                    "field": "type.keyword"
                                }
                            }
                        },
                        {
                            "model": {
                                "terms": {
                                    "field": "model.keyword"
                                }
                            }
                        }
                    ]
                }
            }
        }
    }


# This filter the child,type for the given model name and also gives the model -id for its model-name
def filter_for_model_name(model_name):
    return {
        "size": 0,
        "query": {
            "bool": {
                "should": [

                    {"match": {"model": model_name}}
                ]
            }
        },
        "aggs": {
            "my_buckets": {
                "composite": {
                    "sources": [
                        {"child": {"terms": {"field": "child.keyword"}}},
                        {"type": {"terms": {"field": "type.keyword"}}},
                        {"model_id": {"terms": {"field": "model_id"}}}
                    ]
                }
            }
        }
    }


# This query retrieves the child, model and model-id for the given input type
def filter_for_type(type):
    return {
        "query": {
            "bool": {
                "should": [

                    {"match": {"type": type}}
                ]
            }
        },
        "aggs": {
            "my_buckets": {
                "composite": {
                    "sources": [
                        {"child": {"terms": {"field": "child.keyword"}}},
                        {"model": {"terms": {"field": "model.keyword"}}},
                        {"model_id": {"terms": {"field": "model_id"}}}
                    ]
                }
            }
        }
    }


# This query retrieves the child, model and type for the given input model-id
def filter_for_model_id(model_id):
    return {
        "query": {
            "bool": {
                "should": [

                    {"match": {"model_id": model_id}}
                ]
            }
        },
        "aggs": {
            "my_buckets": {
                "composite": {
                    "sources": [
                        {"child": {"terms": {"field": "child.keyword"}}},
                        {"model": {"terms": {"field": "model.keyword"}}},

                        {"type": {"terms": {"field": "type"}}}
                    ]
                }
            }
        }
    }


# def get_publish_status():
#     return {
#               "query": {
#                 "bool": {
#                   "should": [
#                      { "match": { "Publish_status":1 }}
#                   ]
#                 }
#               },
#             "aggs":
#             {
#                 "by_subtype":
#                     {
#                         "terms": {
#                             "field": "GroupNo"
#                         }
#                     }
#             }
#     }

# def get_random_doc():
#     return {
#     "size":1,
#         "_source":["uri"],
#         "query":{
#         "function_score":{
#              "random_score":{}
#                         }
#                     }
#                 }

@ns.route('/models', endpoint='models', doc={"description": "List models"})
@api.doc(
    "Retrieves aggregation count for the pretrained models available and its associated Parent[Type] ,Model-Id [model_id] is also listed")
class filter_model(Resource):
    def get(self):
        '''
                   List all PreTrained models and its Type and child
        '''
        try:
            classification_models = es.search(index=index, body=aggregation_for_model())
            model_aggregated_bucket= classification_models["aggregations"]["my_buckets"]["buckets"]
            logger.info(" PreTrained models are filtered")
            return model_aggregated_bucket
        except Exception as e:

            logger.error("Unable to return model from Elasticsearch", "Error :", e)
            return handle_bad_request(e)

    @api.doc(params={"model_id": "Unique model id for the model name",
                     "child_id": "Unique child id for its associated model name",
                     "model_name": "Pre Trained Model Name"})
    def post(self):
        '''
        Filter documents with model-id / model_name / child

        '''
        try:
            json_text = json.dumps(request.json)
            json_text = json.loads(json_text)
            for value in json_text:
                if value == "type":
                    type = json_text['type']
                    filter_for_model = es.search(index=index, body=filter_for_type(type))
                    type_count=filter_for_model['hits']['total']['value']
                    type_aggregated_bucket=filter_for_model["aggregations"]["my_buckets"]["buckets"]
                    logger.info("filtered model, model-id and child for the type")
                    filter_for_model=jsonify({"count":type_count,"aggregated_bucket":type_aggregated_bucket})
                elif value == "model":
                    model = json_text['model']
                    filter_for_model = es.search(index=index, body=filter_for_model_name(model))
                    model_count=filter_for_model['hits']['total']['value']
                    model_list=filter_for_model['hits']['hits']
                    model_aggregated_bucket=filter_for_model["aggregations"]["my_buckets"]["buckets"]
                    logger.info("filtered type, model-id and child for the model")
                    filter_for_model= jsonify({"count":model_count,"aggregated_bucket":model_aggregated_bucket})

                elif value == "model_id":
                    model_id = json_text['model_id']
                    filter_for_model = es.search(index=index, body=filter_for_model_id(model_id))
                    model_id_count=filter_for_model['hits']['total']['value']
                    model_id_aggregated_bucket=filter_for_model["aggregations"]["my_buckets"]["buckets"]
                    filter_for_model= jsonify({"count":model_id_count,"aggregated_bucket":model_id_aggregated_bucket})
                    logger.info("filtered model, model-id and child for the type")

                else:
                    filter_for_model = es.search(index=index, body=aggregation_for_model())
                    total_count = filter_for_model['hits']['total']['value']
                    aggregated_bucket= filter_for_model["aggregations"]["my_buckets"]["buckets"]
                    filter_for_model=jsonify({"count":total_count,"aggregated_bucket":aggregated_bucket})
                    logger.info("Filtered model, id and type")

                return filter_for_model
        except Exception as e:
            logger.error("Unable to return data from Elasticsearch", "Error :", e)
            return handle_bad_request(e)


@ns.route('/buildmodel', endpoint='buildmodel', doc={"description": "Generate the new models"})
@api.doc("Generate the new  Parent[Type] ,Model-Id [model_id]  and child")
class Generate_model(Resource):
    def post(self):
        '''
                   Generate models and its Type and child
        '''
        try:
            json_text = json.dumps(request.json)
            json_text = json.loads(json_text)
            print(json_text)

            parent= json_text['type']
            model = json_text['model']
            child= json_text['child']
            group= json_text['group']
            print(parent,model,child,group)
            return build_model_update(parent,model,child,group)
        except Exception as e:
            logger.error("Unable to build or generate model", "Error :", e)
            return handle_bad_request(e)

@ns.route('/regeneratemodel', endpoint='regeneratemodel', doc={"description": "ReGenerate the models"})
@api.doc("Generate the new  Parent[Type] ,Model-Id [model_id]  and child")
class Regenerate_model(Resource):
    def post(self):
        '''
                   ReGenerate models and its Type and child
        '''
        try:
            json_text = json.dumps(request.json)
            json_text = json.loads(json_text)
            print(json_text)

            parent= json_text['type']
            model = json_text['model']
            child= json_text['child']
            group= json_text['group']
            print(parent,model,child,group)
            return regenrate_group(parent,model,child,group)
        except Exception as e:
            logger.error("Unable to build or generate model", "Error :", e)
            return handle_bad_request(e)


@ns.route('/revokegroup/<group_id>', endpoint='revokegroup', doc={"description": "revoke the models to rebuild "})
@api.doc("Generate the new  Parent[Type] ,Model-Id [model_id]  and child")
class Regenerate_model(Resource):
    def get(self,group_id):
        '''
                   ReGenerate models and its Type and child
        '''
        try:
            # json_text = json.dumps(request.json)
            # json_text = json.loads(json_text)
            # print(json_text)
            # group= json_text['group']
            # print(group)
            return revoke_model(group_id)
        except Exception as e:
            logger.error("Unable to build or generate model", "Error :", e)
            return handle_bad_request(e)


@ns.route('classificationengine/groups/train', doc={"description": "train the groups to build the model "})
@api.doc("train the groups to build the model ")
class Regenerate_model(Resource):
    def put(self):
        '''
                  train the groups to Generate models and its Type and child
        '''
        try:
            json_text = json.dumps(request.json)
            json_text = json.loads(json_text)
            model_id= json_text['model_id']
            status = json_text['status']

            #status = json_text['status']
            group_train_list = build_model(model_id, status)
            print(group_train_list)
            return group_train_list
        except Exception as e:
            logger.error("Unable to build or generate model", "Error :", e)
            return handle_bad_request(e)



@ns.route("/models/<model_id>")
@api.doc("Return subtypes for the model_id")
@api.doc(params={"model_id": "Unique model id for the model name"})
class filter_by_model(Resource):

    def get(self, model_id):
        '''
        Retrieves all the inner-subtype [child] for the given model_id
        '''
        try:
            filter_by_id = es.search(index=index, body=filter_model_by_id(model_id))
            total_model_count=filter_by_id['hits']['total']['value']
            model_bucket=filter_by_id["aggregations"]["by_subtype"]["buckets"]
            logger.info("filtered child for the model-id")
            return jsonify({"Total_model_count":total_model_count,"model_bucket":model_bucket})

        except Exception as e:
            logger.error("Unable to return subtypes for the model_id from Elasticsearch", "Error :", e)
            return handle_bad_request(e)


@ns.route("/model_list")
@api.doc("Return all the model")
class filter_all_model(Resource):
    def get(self):
        '''
        Retrieves all the inner-subtype [child] for the given model_id
        '''
        try:
            filter_by_id = es.search(index=index, body=aggregated_model_keyword())
            #total_model_count=filter_by_id['hits']['total']['value']
            model_bucket=filter_by_id["aggregations"]["by_subtype"]["buckets"]
            logger.info("filtered child for the model-id")
            return jsonify(model_bucket)

        except Exception as e:
            logger.error("Unable to return subtypes from Elasticsearch", "Error :", e)
            return handle_bad_request(e)



@ns.route("/groups")
class filter_by_group(Resource):
    def get(self):
        '''
        List all available groups and its aggregated count of documents for each group-id

        '''
        try:
            filter_by_group_id = es.search(index=index, body=aggregate_count_by_group())
            group_bucket = filter_by_group_id["aggregations"]["by_subtype"]["buckets"]
            logger.info("Retrieved  aggregated count for each Group ")
            return group_bucket
        except Exception as e:
            logger.error("Unable to return group count from Elasticsearch", "Error :", e)
            return handle_bad_request(e)


@ns.route("groups/discovered")
class filter_by_group(Resource):
    def get(self):
        '''
        List all available groups name and group id which are published or model generated

        '''
        try:
            published_group_list= get_publish_list()
            return published_group_list
        except Exception as e:
            logger.error("Unable to return group list from postgres", "Error :", e)
            return handle_bad_request(e)



@ns.route("/groups/documents/<group_id>")
@api.doc(params={"group_id": "Group similar documents Under Particular group"})
class filter_by_group_id(Resource):

    def get(self, group_id):
        '''
        This Fetches random document from the group for the given group-id
        '''
        try:
            filter_random_doc_by_group_id = es.search(index=index, body=doc_filter_by_group_id(group_id))
            group_count = filter_random_doc_by_group_id['hits']['total']['value']
            group_list= filter_random_doc_by_group_id['hits']['hits']
            logger.info("successfully retrieved random documents  for the group")
            json_data = {'doc_count':group_count,'group_list':group_list}
            return jsonify(json_data)
        except Exception as e:
            logger.error("Unable to return random coduments for this group_id from Elasticsearch", "Error :", e)
            return handle_bad_request(e)



@ns.route("/classificationengine/<group_id>")
@api.doc(params={"group_id": "group with detail"})
class publish_list(Resource):

    def get(self,group_id):
        '''
        This Fetches random document from the group for the given group-id
        '''
        try:
            get_subclass_name= subclass_status(group_id)
            for data in get_subclass_name:
                if data['status'] == 1:
                    response =get_group_details_for_publish(data['subclass_id'],data['status'])
                else:
                    response = "status is not set or status not set to publish list"
        except Exception as e:
            logger.error("Unable to fetch data from postgres for publish list", "Error :", e)
            return handle_bad_request(e)
        return response

@ns.route("/models/<model_id>/<child_id>")
@api.doc(params={"model_id": "Unique model id for the model name",
                 "child_id": "Unique child id for its associated model name"})
class random_doc_filter_by_child_id(Resource):
    def get(self, model_id, child_id):
        '''
        Fetches random document for the specific model-id and child-id
        '''
        try:
            filter_by_inner_type_id = es.search(index=index, body=filter_by_child_id(model_id, child_id))
            child_document_count=filter_by_inner_type_id['hits']['total']['value']
            random_doc_list=filter_by_inner_type_id['hits']['hits']
            logger.info("successfully retrieved random documents  for the child")
            return jsonify({"child_document_count": child_document_count,"random_doc_list":random_doc_list})
        except Exception as e:
            print("Unable to return random documents for the child_id from Elasticsearch", "Error :", e)
            return handle_bad_request(e)


#
# @ns.route("/classificationengine/groups/discovered")
# class initialize_publish(Resource):
#     def get(self):
#         try:
#             filter_by_publish_id = es.search(index=index, body=get_publish_status())
#             return filter_by_publish_id
#         except Exception as e:
#             print("Unable to return publish status from Elasticsearch", "Error :", e)
#


#
# @ns.route("/random")
# class Fetch_random_doc(Resource):
#     def get(self):
#         try:
#             random_doc = es.search(index=index, body=get_random_doc())
#             return random_doc
#         except Exception as e:
#             print("Unable to return random documents from Elasticsearch", "Error :", e)


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=2001, debug=True)
