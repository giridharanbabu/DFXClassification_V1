from flask import Flask
import configparser
import json
import requests as req
import re
import entity_extraction
import error_updation
from error_updation import *
from loguru import logger
import urllib.parse
import psycopg2
config = configparser.ConfigParser()
config.read('config.ini')

from time import gmtime, strftime
sysdate = strftime("%Y-%m-%d %H:%M:%S", gmtime())

headers = {'Content-Type': "application/json", 'cache-control': "no-cache"}
get_headers = {}
conn = psycopg2.connect(host="192.168.0.42",database="DFX_Classification", user="postgres", password="admin")
cur = conn.cursor()
conn.autocommit = True


group_dict = {
  "name": "",
  "status": None,
  "parenttypeid": None,
  "modeltypeid": None,
  "createdtimestamp":sysdate,
  "groupfilelocation": "None",
  "isreverted": None,
  "modifiedtimestamp": None
}



def add_group(auth_key):
    add_group = {}
    add_group['group_no'] = 0
    add_group['error_msg'] = ''
    add_group['error_code'] = 0
    cur_group_no = 0
    try:
        get_headers['Authorization'] = auth_key
        headers['Authorization'] = auth_key
        cur.execute("SELECT id FROM public.table_dfx_similiaritygroup WHERE id=(select max(id) from public.table_dfx_similiaritygroup);")
        rows = cur.fetchall()
        if not rows:
            cur_group_no = cur_group_no
        else:
            for cur_group_no in rows:
                cur_group_no = cur_group_no[0]

        group_dict["name"] = "Group_" + str(int(cur_group_no) + 1)
        #payload = json.dumps(group_dict)
        query = """INSERT INTO table_dfx_similiaritygroup(name, status, parenttypeid, modeltypeid, createdtimestamp, groupfilelocation, isreverted, modifiedtimestamp) VALUES(%(name)s, %(status)s, %(parenttypeid)s, %(modeltypeid)s, %(createdtimestamp)s, %(groupfilelocation)s, %(isreverted)s, %(modifiedtimestamp)s);"""
        cur.execute(query, group_dict)
        cur.execute("SELECT id FROM public.table_dfx_similiaritygroup WHERE id=(select max(id) from public.table_dfx_similiaritygroup);")
        rows_ = cur.fetchall()

        for cur_group_no_ in rows_:
            logger.info(cur_group_no_[0])
            add_group['group_no'] = int(cur_group_no_[0])
    except Exception as error:
        add_group['error_code'] = 5
        add_group['error_msg'] += "find_group : Issue with Resource to find  the unclassified documents group "
        error_updation.exception_log(error, add_group['error_code']+add_group['error_msg'], str(add_group['error_code']))
        logger.debug("\n\n exception: {}", str(error))
    return add_group






