import cv2
import os
import sys
import PyPDF2
import pytesseract
import configparser
import numpy as np
from loguru import logger
import error_updation
from error_updation import *
import classifier_transactions


# add the handlers to the logger
config = configparser.ConfigParser()
config.read('config.ini')

log_location = config['CLASSIFIER']['LOGGER_LOC']
loginfo_filename = config['CLASSIFIER']['LOGINFO_FILENAME']
logdebug_filename = config['CLASSIFIER']['LOGDEBUG_FILENAME']
temp_directory = config['CLASSIFIER']['TEMP_DIR_LOC']
image_path = config['CLASSIFIER']['IMAGE_PATH']
file_ext_list = config['CLASSIFIER']['SUPPORTED_FILE_EXTENSIONS'].split(",")
pytesseract_install_loc = config['CLASSIFIER']['TESSERACT_INSTALLATION_LOC']
path_separator=config['CLASSIFIER']['PATH_SEP']
pytesseract.pytesseract.tesseract_cmd = pytesseract_install_loc
image2text_path = config['CLASSIFIER']['IMG2TXT_IMG_SAVE_LOC']
img_extension = config['CLASSIFIER']['SUPPORTED_IMG_FILE_EXT'].split(",")
ocr_all_pages = int(config['CLASSIFIER']['OCR_ALL_PAGES'])


def remove_stop_words(text):
    import spacy
    from spacy.lang.en import English
    from spacy.lang.en.stop_words import STOP_WORDS
    nlp = English()
    #  "nlp" Object is used to create documents with linguistic annotations.
    document = nlp(text)
    # Create list of word tokens
    token_list = []
    for token in document:
        token_list.append(token.text)

    # Create list of word tokens after removing stopwords
    filtered_sentence = []
    for word in token_list:
        lexeme = nlp.vocab[word]
        if lexeme.is_stop == False:
            filtered_sentence.append(word)
    return ' '.join(filtered_sentence)


def remove_duplicates(raw_data):
    from collections import Counter
    # split input string separated by space
    raw_data = raw_data.split(" ")
    # joins two adjacent elements in iterable way
    for i in range(0, len(raw_data)):
        raw_data[i] = "".join(raw_data[i])
    Unique_word = Counter(raw_data)
    # joins two adjacent elements in iterable way
    removed_repeated_words = " ".join(Unique_word.keys())
    return removed_repeated_words


def get_file_name(file_path):
    filename = ''
    if len(file_path) > 1:
         filename = os.path.splitext(os.path.basename(file_path))[0]
    return str(filename)


def get_file_ext(file_path):
    ext = ''
    if len(file_path) > 1:
         ext  = os.path.splitext(os.path.basename(file_path))[1]
    return str(ext)


def is_pwdprotected(file_path):
    import msoffcrypto
    file = msoffcrypto.OfficeFile(
        open(file_path, "rb"))
    if file.is_encrypted():
        return True
    else:
        return False


def ocr_processing(img_file_name,inbound_id,auth_key):
    try:
        if os.path.exists(img_file_name):
            pytesseract.pytesseract.tesseract_cmd = pytesseract_install_loc
            logger.info(' \n\n Image processing with openCV & PIL .....')
            img = cv2.imread(img_file_name)  ###reading image
            kernel = np.ones((1, 1), np.uint8)
            img = cv2.dilate(img, kernel, iterations=1)
            img = cv2.erode(img, kernel, iterations=1)
            os.chdir(image2text_path)  #
            new_image = os.path.normpath(os.path.join(temp_directory,str(inbound_id)+"_"+ get_file_name(img_file_name) + ".jpg"))
            cv2.imwrite(new_image, img)
            img2txt = pytesseract.image_to_string(new_image)
            # img2txt = img2txt.replace('\t', ' ')
            if os.path.exists(new_image):
                os.remove(new_image)
            return str(img2txt)
        else:
            logger.info(" Error : Image not found , Error :", img_file_name)
    except Exception as error:
        error_updation.exception_log(error, "Image to Text conversion failed", str(inbound_id))
        classifier_transactions.update_inbound_status(inbound_id, auth_key)
        logger.debug("Image to Text conversion failed , Error :", error)


def convert2str(val, bool):
    import xlrd
    try:
        if type(val) is float and bool == 0:
            return str(int(val))
        elif type(val) is float and bool == 1:
            xldate = xlrd.xldate.xldate_as_datetime(val, 0)
            return xldate
    except Exception as error:
        error_updation.exception_log(error, "Error occurred in Excel date conversion : convert2str ERROR ", str(val))


def pdf_to_image(file_path,inbound_id,auth_key,no_of_pages=ocr_all_pages):
    import os
    file_content = ""
    try:
        if os.path.exists(file_path):
                import fitz
                import os
                doc = fitz.open(file_path)
                pdf_file_name = get_file_name(file_path)
                for i in range(no_of_pages):
                    for img in doc.getPageImageList(i):
                        xref = img[0]
                        pix = fitz.Pixmap(doc, xref)
                        png_file_name = os.path.normpath(os.path.join(image_path, pdf_file_name + "_" + str(xref) + ".png"))
                        logger.info("\nPNG File Name : {}", png_file_name)

                        if pix.n < 5:  # this is GRAY or RGB
                            pix.writePNG(png_file_name)
                        else:  # CMYK: convert to RGB first
                            pix1 = fitz.Pixmap(fitz.csRGB, pix)
                            pix1.writePNG(png_file_name)
                            pix1 = None
                        pix = None
                        file_content = file_content +" "+ ocr_processing(png_file_name,inbound_id,auth_key)
                        #if os.path.exists(png_file_name):
                            #os.remove(png_file_name)
        else:
            logger.info(" \n\n  pdf file not found ")
    except Exception as error:
        error_updation.exception_log(error, "Error with Image processing pdf_to_image", str(inbound_id))
        classifier_transactions.update_inbound_status(inbound_id, auth_key)
    return file_content


def file_validation(file_name) :
    is_valid = False
    if os.path.exists(file_name) and os.path.getsize(file_name) > 1 and os.access(file_name,os.R_OK):
        is_valid =  True
    return is_valid


# def word_document_processing(filename,inbound_id,auth_key) :
#     import os
#     from subprocess import call
#     logger.info('\n****************** Processing docx .....\n')
#     data = ''
#     if not is_pwdprotected(filename):
#         if os.name == 'posix':
#             try:
#                 call(["docx2txt", filename, "tmp"])
#             except Exception as e:
#                 error_updation.exception_log(e, "Data extraction is failed in docx2txt", str(inbound_id) )
#             with open("tmp", encoding="utf-8") as file:
#                 data = file.read()  # .replace('\
#         elif os.name == 'nt':
#             try:
#                 import docx2txt
#                 from  docx2python import docx2python
#                 from time import gmtime, strftime
#                 logger.info('\n****************** Processing docx document .....\n')
#                 data = ''
#                 file = get_file_name(filename)
#                 tmp_dir_name = os.path.normpath(os.path.join(temp_directory, file + "_" + strftime("%Y-%m-%d_%H_%M_%S", gmtime())))
#                 os.makedirs(tmp_dir_name,mode=0o777 ,exist_ok=False)
#                 if os.path.exists(tmp_dir_name):
#                     data = docx2txt.process(filename,tmp_dir_name)
#                     for file in os.listdir(tmp_dir_name):
#                         tmp_file_name =  os.path.normpath(os.path.join(tmp_dir_name ,file))
#                         data = data +"\n"+str(ocr_processing(tmp_file_name, inbound_id,auth_key))
#                         if os.path.exists(tmp_file_name):
#                             os.remove(tmp_file_name)
#                 if os.path.exists(tmp_dir_name):
#                     import shutil
#                     shutil.rmtree(tmp_dir_name)
#             except Exception as error:
#                 print(" error : ",error)
#                 error_updation.exception_log(error, " Issue occurred with document to text ", str(inbound_id))
#                 classifier_transactions.update_inbound_status(inbound_id, auth_key)
#     else:
#         classifier_transactions.update_inbound_pwdprotected_status(inbound_id, auth_key)
#     # print("\n data :", data)
#     data=data.replace(
#         'Created by the trial version of Document .Net 3.8.6.28!\n\nThe trial version sometimes inserts randomly backgrounds.\n\nGet the full version of Document .Net.',
#         '\n')
#     return data
#
#
# def pdf_document_processing(filename,inbound_id,auth_key):
#     logger.info('\n****************** Processing pdf document .....\n')
#     data = ''
#     try:
#         pdf_file = open(filename, 'rb')
#         pdf_read = PyPDF2.PdfFileReader(pdf_file, strict=False)
#         if not pdf_read.isEncrypted:
#             no_pages = pdf_read.getNumPages()
#             logger.info("\n No of pages : {}, ocr_all_pages:{}", no_pages, ocr_all_pages)
#             if ocr_all_pages != 0:
#                 no_pages = ocr_all_pages
#             count = 0
#             while count < no_pages:
#                 logger.info("\n\n count: {}", count)
#                 pageobj = pdf_read.getPage(count)
#                 count += 1
#                 data += pageobj.extractText()
#             pdf_file.close()
#             data += pdf_to_image(filename, inbound_id,auth_key, no_pages)
#         else:
#             classifier_transactions.update_inbound_pwdprotected_status(inbound_id,auth_key)
#     except Exception as e:
#         error_updation.exception_log(e, "Failed process the data in file", str(inbound_id))
#         classifier_transactions.update_inbound_status(inbound_id, auth_key)
#     data = data.replace(
#         'Created by the trial version of Document .Net 3.8.6.28!\nThe trial version sometimes inserts randomly backgrounds.\nGet the full version of Document .Net','\n')
#     return data
#
#
# def excel_document_processing(filename,inbound_id,auth_key):
#     import xlrd
#     logger.info('\n****************** Processing Excel document .....\n')
#     data = ''
#     try:
#         if not is_pwdprotected(filename):
#             # Open the work book
#             book = xlrd.open_workbook(filename)
#             # Get sheet count in excel
#             tabcount = book.nsheets
#             if ocr_all_pages is not 1:
#                 tabcount = 1
#             nlp_text = ""
#             # Iterate through worksheets and get values
#             for i in range(0, tabcount):
#                 sheet = book.sheet_by_index(i)
#                 nlp_text += "Sheet Name: "+sheet.name+ " "
#                 # Get the header values
#                 header = sheet.row(0)
#                 for rx in range(1, sheet.nrows):
#                     for cx in range(0, sheet.ncols):
#                         header_value = convert2str(header[cx].value, 0)
#                         cell_value = sheet.cell_value(rx, cx)
#                         if cell_value is not None and cell_value is not "":
#                             nlp_text += str(cell_value)
#                             nlp = nlp_text.replace('\n', ' ')
#                     nlp += "\n"
#             data = nlp
#         else:
#             classifier_transactions.update_inbound_pwdprotected_status(inbound_id, auth_key)
#     except Exception as e:
#         error_updation.exception_log(e, "Problem with file", str(inbound_id))
#         classifier_transactions.update_inbound_status(inbound_id, auth_key)
#     return data
#
#
# def text_processing(filename,inbound_id,auth_key):
#     logger.info('\n****************** Processing TXT document .....\n')
#     data = ''
#     try:
#         with open(filename, 'rb+') as textfile:
#             data = textfile.read().decode()
#             #  .replace('\n', ' ')
#     except Exception as e:
#         error_updation.exception_log(e, "Problem with file", str(filename))
#         classifier_transactions.update_inbound_status(inbound_id, auth_key)
#     return data


# def filter_text_from_file(filename,inbound_id,auth_key):
#     import os
#     import re
#     processed_data = ""
#     response_data = {}
#     new_text_file = ''
#     error_msg = ''
#     logger.info('\n****************** filter_text_from_file :')
#     try:
#         response_data['error_code'] = 0
#         src_file_name, file_extension = os.path.splitext(filename)
#         file_extension = file_extension.lower()
#         logger.info('\n****************** File extension : {}', file_extension)
#         logger.info('\n****************** supported files : {}', file_ext_list)
#         if os.path.exists(filename) and  file_extension in file_ext_list:
#             if file_extension in img_extension :
#                 processed_data += ocr_processing(filename,inbound_id,auth_key)
#             elif file_extension == ".docx":
#                 processed_data += word_document_processing(filename,inbound_id,auth_key)
#             elif file_extension == ".pdf":
#                 processed_data += pdf_document_processing(filename, inbound_id,auth_key)
#             elif file_extension == ".txt":
#                 processed_data += text_processing(filename,inbound_id,auth_key)
#             elif file_extension == '.xls' or file_extension == '.xlsx':
#                 processed_data = excel_document_processing(filename, inbound_id,auth_key)
#             if len(processed_data.strip()) > 0:
#                 new_text_file = os.path.normpath(os.path.join(temp_directory , str(inbound_id) + "_" + get_file_name(
#                     filename) + ".txt"))
#                 logger.debug("\n\n new_text_file: {}", new_text_file)
#                 # processed_data.replace('\n', ' ')
#                 processed_data.replace('Created by the trial version of Document .Net 3.8.6.28!\n\nThe trial version sometimes inserts randomly backgrounds.\n\nGet the full version of Document .Net.','\n')
#                 processed_data = re.sub(r'[^\x00-\x7F]+', ' ', str(processed_data))
#                 processed_data = re.sub('[^a-zA-Z0-9-_*$@:;''.]', ' ', processed_data)
#                 processed_data = remove_stop_words(processed_data)
#                 from string import digits
#                 remove_digits = str.maketrans('', '', digits)
#                 processed_data = processed_data.translate(remove_digits)
#                 # processed_data = remove_duplicates(processed_data)
#                 with open(new_text_file, "w", encoding='utf-8',errors='ignore' ) as text_file:
#                     text_file.write(processed_data)
#                 if len(new_text_file) > 1 and file_validation(new_text_file):
#                     response_data["text_file_name"] = new_text_file
#                 else:
#                     response_data['error_msg'] = 'Failed to read the content from  document : ' + filename + " Inbound ID " + str(inbound_id)
#                     response_data['error_code'] = 2
#                     classifier_transactions.update_inbound_status(inbound_id, auth_key)
#                     error_updation.custom_error_update_log(response_data['error_msg'],
#                                                            response_data['error_msg'],
#                                                            str(inbound_id))
#             else:
#                 response_data['error_code'] = 2
#                 response_data['error_msg'] = '\n Data processing failed with document : '+filename+", Inbound ID :"+str(inbound_id)
#                 classifier_transactions.update_inbound_status(inbound_id, auth_key)
#                 error_updation.custom_error_update_log(response_data['error_msg'],
#                                                        response_data['error_msg'],
#                                                        str(inbound_id))
#         else:
#             response_data['error_code'] = 2
#             response_data['error_msg'] = "\n Application is not supporting the mentioned file format :" + str(file_extension)
#             classifier_transactions.update_inbound_status(inbound_id, auth_key)
#             error_updation.custom_error_update_log(response_data['error_msg'],
#                                                    response_data['error_msg'],
#                                                    str(inbound_id))
#     except Exception as error:
#         response_data['error_code'] = 2
#         response_data["error_msg"] = "\n filter_text_from_file : "+str(inbound_id)+ " Error occurred in filter_text_from_file : "+ str(error)
#         classifier_transactions.update_inbound_status(inbound_id,auth_key)
#         error_updation.custom_error_update_log(response_data['error_msg'],
#                                            response_data['error_msg'],
#                                            str(inbound_id))
#         error_updation.exception_log(error, response_data, str(inbound_id))
#     print(processed_data)
#     return response_data

def remove_alphanumeric(words):
    """Stem words in list of tokenized words"""
    cleandata = []
    validation = re.compile(r'\D*\d')
    for word in words:
        if not validation.match(word) :
            cleandata.append(word)
    return cleandata


def filter_text_from_file(inbound_id ,content ,auth_key):
    import os
    import re

    from datetime import datetime as dt
    sysdate = str(dt.now()).replace(":", "_")
    import urllib.parse
    processed_data = ""
    response_data = {}
    new_text_file = ''
    error_msg = ''
    logger.info('\n****************** filter_text_from_file :')
    try:
        processed_data = content
        if len(processed_data.strip()) > 0:
            new_text_file = os.path.normpath(os.path.join(temp_directory, str(str(inbound_id) )+ "_"+ sysdate + ".txt"))
            logger.debug("\n\n new_text_file: {}", new_text_file)
            # processed_data.replace('\n', ' ')
            processed_data.replace(
                'Created by the trial version of Document .Net 3.8.6.28!\n\nThe trial version sometimes inserts randomly backgrounds.\n\nGet the full version of Document .Net.',
                '\n')
            processed_data = re.sub(r'[^\x00-\x7F]+', ' ', str(processed_data))
            processed_data = re.sub('[^a-zA-Z0-9-_*$@:;''.]', ' ', processed_data)
            processed_data = remove_stop_words(processed_data)
            #processed_data = remove_alphanumeric(processed_data)
            from string import digits
            remove_digits = str.maketrans('', '', digits)
            processed_data = processed_data.translate(remove_digits)
            # processed_data = remove_duplicates(processed_data)
            with open(new_text_file, "w", encoding='utf-8', errors='ignore') as text_file:
                text_file.write(processed_data)
            if len(new_text_file) > 1 and file_validation(new_text_file):
                response_data["text_file_name"] = new_text_file
            else:
                response_data[
                    'error_msg'] = 'Failed to read the content from  document : ' + "1" + " Inbound ID " + str(
                    inbound_id)
                response_data['error_code'] = 2
                # classifier_transactions.update_inbound_status(inbound_id, auth_key)
                # error_updation.custom_error_update_log(response_data['error_msg'],
                #                                    response_data['error_msg'],
                #                                    str(inbound_id))
        else:
            response_data['error_code'] = 2
            response_data[
                'error_msg'] = '\n Data processing failed with document : ' + "filename" + ", Inbound ID :" + str(
                inbound_id)
            # classifier_transactions.update_inbound_status(inbound_id, auth_key)
            # error_updation.custom_error_update_log(response_data['error_msg'],
            #                                        response_data['error_msg'],
            #                                        str(inbound_id))

    except Exception as error:
        response_data['error_code'] = 2
        response_data["error_msg"] = "\n filter_text_from_file : " + str(
            inbound_id) + " Error occurred in filter_text_from_file : " + str(error)
        # classifier_transactions.update_inbound_status(inbound_id, auth_key)
        # error_updation.custom_error_update_log(response_data['error_msg'],
        #                                        response_data['error_msg'],
        #                                        str(inbound_id))
        # error_updation.exception_log(error, response_data, str(inbound_id))

    return response_data


#
# if __name__ == '__main__':
#    # print("\n MAIN:")
#     filter_text_from_file(r"C:\Users\baskaran\Desktop\dms\LkqhnRjs_ps.pdf", 135, 'bearer 9jYF-wEagkECw_DX75Y80W69TT3m6YQGqQNST4XHhaxb3uiUYTlAYxJnrddmLVB3YXl4p-zPK_KecjmVX3LAZEd0gvbpcILM4ItbYyCwe8dB3Huj8qScXsFpH_ccUAOZydigKLxKR_Px4OICZKGsbxQYQOEhHdDGuDMPxybNDksFNp1L7PrBSWAzs18AmfUDE7RDiHCRDmdkBihJHLPU_AdqAwfJy5Oj2dahFGZVhfcoIb7u-7dr0ok-u5dymJlziEc40M3A9hTYHS4bj9wkAfCuJX7iDx550RW20hh2dZI')
#

