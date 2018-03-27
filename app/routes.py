#---------------------------------------------------------------
# IMPORTS 
#---------------------------------------------------------------

import flask
import tabula
import pandas as pd 
import ast 
import os
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

#---------------------------------------------------------------
# APP CONFIG 
#---------------------------------------------------------------

UPLOAD_FOLDER = './uploads'         # previously: './uploads' (on local) (should be 'tmp')
DOWNLOAD_FOLDER = './downloads' # how to deal with this???
TEMP_FOLDER = '/tmp'
ALLOWED_EXTENSIONS = set(['pdf', 'txt', 'jpg', 'png', 'jpeg'])
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['DOWNLOAD_FOLDER'] = DOWNLOAD_FOLDER
app.config['TEMP_FOLDER'] = TEMP_FOLDER
app.config['OCR_OUTPUT_FILE'] = 'ocr'
app.config['MAX_CONTENT_LENGTH'] = 4 * 1024 * 1024

client = boto3.client('s3')
resource = boto3.resource('s3')
upload_bucket = resource.Bucket('tablereader-uploads')
upload_bucket_name = 'tablereader-uploads'
download_bucket = resource.Bucket('tablereader-downloads')
download_bucket_name = 'tablereader-downloads'

#---------------------------------------------------------------

# Flask-WTF web form class
class FileUploadForm(FlaskForm):
    file_upload = FileField(validators=[FileRequired()])
    page_range = StringField('Page Range')
    multiple_tables = BooleanField('Does your file contain multiple tables on the same page?')
    submit = SubmitField('Upload')

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

        upload_bucket.put_object(Key=filename, Body=file.stream, ContentType=file.content_type)
        path_to_bucket = 'https://' + upload_bucket_name + '.s3.amazonaws.com/' + filename

        # Call the Tabula helper method 
        df_list, download_name_list = tabulaParse(path_to_bucket, filename, page_range, multi_table_flag)                                                                                                                                                                                   
        
        df_html_list = []
        # Handle each dataframe returned by the helper method 
        for index, df in enumerate(df_list): 
            df_html_list.append(df.to_html()) # HTML display 
            csv = df.to_csv(path_or_buf=None, encoding='utf-8') # will be a string 
            download_name = download_name_list[index] # match to download name 
            download_bucket.put_object(Key=download_name, Body=csv) # put in downlad bucket

        return render_template('upload.html', data=df_html_list, filename=filename, dnamelist=download_name_list)

    # Error handling: form not validated 
    else:
        return render_template('404.html') 
    
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

@app.route('/download', methods = ['GET', 'POST'])
def download():

    download_list = request.form['filename']
    download_list = ast.literal_eval(download_list) # convert string to list

    memory_file = BytesIO()
    zipf = zipfile.ZipFile(memory_file, mode='w', compression=zipfile.ZIP_DEFLATED)
    # zipf = zipfile.ZipFile('output.zip', mode='w', compression=zipfile.ZIP_DEFLATED)
    for download_name in download_list: 
        print "DOWNLOAD NAME IN THE LOOP: ", download_name 
        file = client.get_object(Bucket=download_bucket_name, Key=download_name)
        zipf.writestr(download_name, file['Body'].read())
    zipf.close()
    memory_file.seek(0)

    return send_file(memory_file, attachment_filename="output.zip", as_attachment=True)

    # required: unique filename, location/path to saved CSV
    # basedir = os.path.abspath(os.path.dirname(__file__))
    # location = os.path.join(basedir, app.config['DOWNLOAD_FOLDER'], download_name)
    # return send_file(location, mimetype='text/csv', attachment_filename=download_name, as_attachment=True)
    
    # file = client.get_object(Bucket='tablereader-downloads', Key=download_name)
    # response = make_response(file['Body'].read())
    # response.headers['Content-Type'] = 'text/csv'

    # file = client.get_object(Bucket=download_bucket_name, Key=download_name)
    # return Response(
    #     file['Body'].read(),
    #     mimetype='text/csv',
    #     headers={"Content-Disposition": "attachment;filename=output.csv"}
    #     )

#----------------------------------------------------

@app.route('/test', methods = ['GET'])
def test():
  return render_template('upload_form.html', landing_page = 'process')

@app.route('/process', methods = ['GET','POST'])
def process():
  if request.method == 'POST':
    file = request.files['file']
    hocr = request.form.get('hocr') or ''
    ext = '.hocr' if hocr else '.txt'
    if file and allowed_file(file.filename):
      folder = os.path.join(app.config['TEMP_FOLDER'], str(os.getpid()))

      os.mkdir(folder)
      input_file = os.path.join(folder, secure_filename(file.filename))
      output_file = os.path.join(folder, app.config['OCR_OUTPUT_FILE'])
      file.save(input_file)

      print "input file check: ", os.path.isfile(input_file)
      print "input file path: ", input_file 
      print "output file path: ", output_file 

      command = ['tesseract', input_file, output_file, '-l', request.form['lang'], hocr]
      proc = subprocess.Popen(command, stderr=subprocess.PIPE)
      proc.wait()

      output_file += ext

      print output_file 
      print "output file exists check: ", os.path.exists(output_file)
      print "output file is file check: ", os.path.isfile(output_file)

      if os.path.isfile(output_file):
        f = open(output_file)
        resp = jsonify( {
          u'status': 200,
          u'ocr':{k:v.decode('utf-8') for k,v in enumerate(f.read().splitlines())}
        } )
      else:
        resp = jsonify( {
          u'status': 422,
          u'message': u'Unprocessable Entity'
        } )
        resp.status_code = 422

      shutil.rmtree(folder)
      return resp
    else:
      resp = jsonify( { 
        u'status': 415,
        u'message': u'Unsupported Media Type' 
      } )
      resp.status_code = 415
      return resp
  else:
    resp = jsonify( { 
      u'status': 405, 
      u'message': u'The method is not allowed for the requested URL' 
    } )
    resp.status_code = 405
    return resp