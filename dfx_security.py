
import os
import error_updation
import configparser
config = configparser.ConfigParser()
config.read('config.ini')


def get_security_token():
    import requests as req
    import json
    try:
        sec_token_url = config['CLASSIFIER']['SEC_TOKEN_URL']
        sec_username = config['CLASSIFIER']['SEC_USERNAME']
        sec_password = config['CLASSIFIER']['SEC_PASSWORD']
        sec_grant_type = config['CLASSIFIER']['SEC_GRANT_TYPE']
        payload = {}
        payload['username']= sec_username
        payload['password']= sec_password
        payload['grant_type']=sec_grant_type
        # print("sec_token_url:",sec_token_url)
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        sec_reqst = req.request("GET", url=sec_token_url, data=payload, headers=headers)
        # print("\n\n Connector reqst:", sec_reqst.json())
        token = ''
        if sec_reqst and sec_reqst.status_code is  200:
            sec_data = sec_reqst.json()
            token = 'bearer '+sec_data['access_token']
    except Exception as error:
        error_updation.exception_log("Security Token issue ", " Security Token issue ", 0)
    return token


# if __name__ == "__main__":
#     print(get_security_token())
