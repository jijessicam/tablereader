#---------------------------------------------------------------
# IMPORTS 
#---------------------------------------------------------------

import flask
import tabula
import pandas as pd 
import ast 
import os
import re 
import subprocess
import logging 
import csv 
import zipfile 
from flask import Flask, render_template, flash, redirect, url_for, request, jsonify, session, send_file, Response 
from app import app
from app.forms import LoginForm
from werkzeug.utils import secure_filename
import json, boto3
from io import StringIO, BytesIO
import shutil
import requests 
import urllib
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired
from wtforms import StringField, SubmitField, BooleanField
from wtforms import validators, ValidationError 
import ftfy

#---------------------------------------------------------------
# APP CONFIG 
#---------------------------------------------------------------

# UPLOAD_FOLDER = './uploads'         # previously: './uploads' (on local) (should be 'tmp')
# DOWNLOAD_FOLDER = './downloads' # how to deal with this???
# TEMP_FOLDER = '/tmp'
# app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
# app.config['DOWNLOAD_FOLDER'] = DOWNLOAD_FOLDER
# app.config['TEMP_FOLDER'] = TEMP_FOLDER
# app.config['OCR_OUTPUT_FILE'] = 'ocr'
# app.config['MAX_CONTENT_LENGTH'] = 4 * 1024 * 1024

ALLOWED_EXTENSIONS = set(['pdf'])

client = boto3.client('s3')
resource = boto3.resource('s3')
upload_bucket = resource.Bucket('tablereader-uploads')
upload_bucket_name = 'tablereader-uploads'
download_bucket = resource.Bucket('tablereader-downloads')
download_bucket_name = 'tablereader-downloads'

#---------------------------------------------------------------

# Flask-WTF web form class
class FileUploadForm(FlaskForm):
    file_upload = FileField(validators=[FileRequired("Please select a PDF file to upload.")])
    page_range = StringField('Page Range')
    multiple_tables = BooleanField('Does your file contain multiple tables on the same page?')
    
    unicode_fix = BooleanField('Fix potential Unicode character encoding errors')
    nans_to_none = BooleanField('Replace all NaNs with None (useful for database entry)')
    drop_duplicate_rows = BooleanField('Delete duplicate rows')
    # highlight_duplicate_rows = BooleanField('Highlight duplicate rows')
    highlight_nans = BooleanField('Highlight missing data')
    highlight_headers = BooleanField('Attempt to approximate and highlight table headers')
    color_bad_cells = BooleanField('Color potentially erroneous values red')

    submit = SubmitField('Upload File')

#---------------------------------------------------------------

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

#---------------------------------------------------------------

@app.route('/')
@app.route('/index')
def index():
    form = FileUploadForm()
    return render_template('index.html', title='Home', form=form)

#---------------------------------------------------------------

@app.route('/about')
def about():
    return render_template('about.html', title='About')

#---------------------------------------------------------------

@app.route('/docs')
def docs():
    return render_template('docs.html', title='Documentation')

#---------------------------------------------------------------

@app.route('/upload', methods = ['GET', 'POST'])
def upload():
    form = FileUploadForm()

    if form.validate_on_submit():
        file = form.file_upload.data
        filename = secure_filename(file.filename)

        # Multiple page handling
        if form.page_range.data:
            temp = form.page_range.data.rstrip(',').split(',')
            page_range = [int(x) for x in temp]
        else:
            page_range = list()

        # Multiple table handling (boolean flag)
        multi_table_flag = form.multiple_tables.data

        # Data postprocessing handling (more boolean flags)
        unicode_fix = form.unicode_fix.data
        nans_to_none = form.nans_to_none.data
        drop_duplicate_rows = form.drop_duplicate_rows.data
        # highlight_duplicate_rows = form.highlight_duplicate_rows.data
        highlight_nans = form.highlight_nans.data
        highlight_headers = form.highlight_headers.data
        color_bad_cells = form.color_bad_cells.data

        upload_bucket.put_object(Key=filename, Body=file.stream, ContentType=file.content_type)
        path_to_bucket = 'https://' + upload_bucket_name + '.s3.amazonaws.com/' + filename

        # Call the Tabula helper method 
        df_list, download_name_list = tabulaParse(path_to_bucket, filename, page_range, multi_table_flag)                                                                                                                                                                                   
        
        df_html_list = []

        # Handle each dataframe returned by the helper method 
        for index, df in enumerate(df_list): 
            # df_html_list.append(df.to_html()) # HTML display 

            if unicode_fix:
                df = fixTableEncoding(df)
            if nans_to_none:
                df = convertNansToNone(df)
            if drop_duplicate_rows:
                df = df.drop_duplicates()

            # Highlight problems: create boolean type map 
            bool_map = typeMapper(df)
            header_list, modified_bool_map = identifyHeaders(bool_map)
            val_flag_dict = nonUniqueColumnValues(modified_bool_map)

            colored_table = flagColors(df, highlight_nans, highlight_headers,
                color_bad_cells, header_list, val_flag_dict) # removed highlight_duplicate_rows 
            df_html_list.append(colored_table)

            csv = df.to_csv(path_or_buf=None, encoding='utf-8') # will be a string 
            download_name = download_name_list[index] # match to download name 
            download_bucket.put_object(Key=download_name, Body=csv) # put in download bucket

        return render_template('upload.html', tables=zip(df_html_list, download_name_list), dnames=download_name_list, filename=filename)
        # return render_template('upload.html', tables=zip(df_html_list, download_name_list), dnames=download_name_list, filename=filename)

    # Error handling: form not validated 
    else:
        return render_template('emptyupload.html') 
    
#---------------------------------------------------------------

# Tabula file processing helper method 
def tabulaParse(file_contents, filename, pages, multitable):

    # Multiple page handling
    if pages: 
        df = tabula.read_pdf(file_contents, pages=pages, multiple_tables=True)     
    else:
        # Multiple table handling
        if multitable is True: 
            df = tabula.read_pdf(file_contents, multiple_tables=True) 
        else:
            df = []
            temp = tabula.read_pdf(file_contents) 
            df.append(temp)

    # File download name handling 
    download_name_list = []
    number_of_files = len(df) 

    file_chopped = ""
    if (filename.endswith(".pdf")):
        file_chopped = filename[:-len(".pdf")]
    # download_name = file_chopped + '_output.csv'

    for i in range(0, number_of_files):
        download_name = file_chopped + '_' + str(i + 1) + '_output.csv'
        download_name_list.append(download_name)

    # Returns a list of dataframes and a list of download names 
    return df, download_name_list 

#---------------------------------------------------------------

# Postprocessing: drop duplicate rows if boolean flag is True
def dropDuplicateRows(input_dataframe):
    df = input_dataframe
    df = df.drop_duplicates()
    return df 

#---------------------------------------------------------------

# Postprocessing: convert all NaN values to None 
def convertNansToNone(input_dataframe):
    df = input_dataframe
    df = df.where((pd.notnull(df)), None)
    return df 

#---------------------------------------------------------------

# Postprocessing: fix Unicode encoding if boolean flag is True 
def fixTableEncoding(input_dataframe):
    df = input_dataframe
    df = df.applymap(fixTextEncoding)
    return df 

def fixTextEncoding(text):
    if isinstance(text, basestring):
        if isinstance(text, str):
            t = bytes.decode(text) # decode to utf-8
        elif isinstance(text, unicode):
            t = text 
        return ftfy.fix_text(t) # ftfy library call
    else:
        return 

#---------------------------------------------------------------

# Helper method: dataframe coloring 
# Takes dataframe, boolean map as input 
def flagColors(input_dataframe, highlight_nans, highlight_headers, color_bad_cells, header_list, index_dict):
    df = input_dataframe
    df = df.applymap(mapAllToString)

    RED = '#fc5d58'

    func_call = 'df.style'

    if highlight_headers: 
        func_call += '.set_properties(subset=pd.IndexSlice[header_list, :], **{\'background-color\': \'green\'})'
    if highlight_nans:
        func_call += '.highlight_null(null_color=RED)'
    # if highlight_duplicates:
    #     func_call += '.apply(highlightDuplicateRows)'
    if color_bad_cells: 
        func_call += '.apply(colorProblematicCells, args=(index_dict,))'

    func_call += '.set_table_attributes(\'border=1\')'

    # # ALL FLAGS SET 
    # if highlight_duplicates and highlight_nans and highlight_headers and color_bad_cells: 
    #     df = df.style. \
    #         set_properties(subset=pd.IndexSlice[header_list, :], **{'background-color': 'green'}). \
    #         highlight_null(null_color=RED). \
    #         apply(highlightDuplicateRows). \
    #         apply(colorProblematicCells, args=(index_dict,)). \
    #         set_table_attributes('border=1')

    # # NO FLAGS SET 
    # if not highlight_duplicates and not highlight_nans and not highlight_headers and not color_bad_cells: 
    #     df = df.style.set_table_attributes('border=1')

    df = eval(func_call)

    return df.render() 

#---------------------------------------------------------------

def mapAllToString(value):
    strval = str(value)
    return strval 

#---------------------------------------------------------------

def highlightDuplicateRows(input_dataframe):

    df = input_dataframe 
    d = df.duplicated()
    dupe_rows = [i for i, x in enumerate(d) if x] # list of dupe indices
    for index in dupe_rows:
        df.iloc[[index]] = 'background-color: yellow'
    return df 

#---------------------------------------------------------------

# Helper method: return a list of dataframe row indices that could be headers 
def identifyHeaders(boolean_map):
    df = boolean_map 
    num_rows = df.shape[0]
    num_cols = df.shape[1]

    last_row = df.iloc[[num_rows-1]].reset_index(drop=True)

    mismatch_index = -1 

    for index, row in df.iterrows():
        if (last_row.equals(df.iloc[[index]].reset_index(drop=True))):
            mismatch_index = index
            break 
        else:
            continue 

    if mismatch_index > 0:
        header_list = range(0, mismatch_index)
    else: 
        header_list = []
        return header_list, df 

    df = df.drop(df.index[header_list])
    df = df.drop(df.index[0])
    return header_list, df 

#---------------------------------------------------------------

# def colorProblematicCells(input_dataframe, index_dict):

#     df = input_dataframe 
#     for col_name, index_list in index_dict.iteritems():
#         for index in index_list:
#             # print index, ", ", col_name 
#             # print df.name 
#             if df.name == col_name:
#                 df.iloc[index] = 'background-color: gray'
#             # df.iloc[index, df.columns.get_loc(col_name)] = 'color: red'

#     print df 
#     print "DATA TYPES: "
#     print df.dtypes

#     return df 

def colorProblematicCells(input_dataframe, index_dict):
    df = input_dataframe.copy()

    for col_name, index_list in index_dict.iteritems():
        for index in index_list: 
            df.loc[index, col_name] = 'background-color: blue'

    return df 
#---------------------------------------------------------------

# Helper method: returns a dict of {col name, [list of row indices]} to flag irregular data 
def nonUniqueColumnValues(boolean_map):
    df = boolean_map

    uniques = df.apply(lambda x: x.nunique())

    df = df.drop(uniques[uniques==1].index, axis=1)

    val_counts = df.apply(pd.value_counts)

    flag_dict = {}

    for col_name, column in df.iteritems():
        if (2*val_counts.iloc[0][col_name]) < val_counts.iloc[1][col_name]:
            index_list = df.index[df[col_name] == val_counts.iloc[0].name].tolist()
            flag_dict[col_name] = index_list
        elif (2*val_counts.iloc[1][col_name]) < val_counts.iloc[0][col_name]:
            index_list = df.index[df[col_name] == val_counts.iloc[1].name].tolist()
            flag_dict[col_name] = index_list

    return flag_dict 

#---------------------------------------------------------------

# Helper method: regex mapping 

def typeMapper(input_dataframe):
    df = input_dataframe 
    df = df.applymap(regexMapHelper)
    return df 

def regexMapHelper(obj):

    num = re.compile(r"^[+-]?\d+(?:(\.|,)\d+)?$")

    # Matches numbers in this format: 1,234,567 
    num2 = re.compile(r"^((?:\d{1,3},(?:\d{3},)*\d{3})|(?:\d{1,3}))$")

    # Modification to accomodate commas and decimals 
    num3 = re.compile(r"^[+-]?[\d,]+(?:(\.|,)\d+)?$")

    cell = str(obj) # convert to string 

    if num.match(cell):
        return True 
    elif num2.match(cell):
        return True 
    elif num3.match(cell):
        return True 
    else: 
        return False
#---------------------------------------------------------------

@app.route('/download', methods = ['GET', 'POST'])
def download():

    dlist = request.form['filename']
    if dlist: 
      download_list = ast.literal_eval(dlist) # convert string to list
    else: 
      return render_template('404.html') 

    # Single file handling 
    if (len(download_list) == 1):
        # memory_file = BytesIO()
        download_name = download_list[0]
        file = client.get_object(Bucket=download_bucket_name, Key=download_name)
        return Response(
            file['Body'].read(),
            mimetype='text/csv',
            headers={"Content-Disposition": "attachment;filename=output.csv"}
            )
    # Multi-file/zip directory handling 
    else:   
        memory_file = BytesIO()
        zipf = zipfile.ZipFile(memory_file, mode='w', compression=zipfile.ZIP_DEFLATED)
        # zipf = zipfile.ZipFile('output.zip', mode='w', compression=zipfile.ZIP_DEFLATED)
        for download_name in download_list: 
            file = client.get_object(Bucket=download_bucket_name, Key=download_name)
            zipf.writestr(download_name, file['Body'].read())
        zipf.close()
        memory_file.seek(0)

        return send_file(memory_file, attachment_filename="output.zip", as_attachment=True)
