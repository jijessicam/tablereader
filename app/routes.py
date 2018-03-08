#---------------------------------------------------------------
# IMPORTS 
#---------------------------------------------------------------

import flask
import tabula
import pandas as pd 
import os
import subprocess
import logging 
import csv 
from flask import Flask, render_template, flash, redirect, url_for, request, jsonify, session, send_file, Response 
from app import app
from app.forms import LoginForm
from werkzeug.utils import secure_filename
import json, boto3
from io import StringIO, BytesIO
import shutil
import requests 
import urllib

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

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

#---------------------------------------------------------------

@app.route('/')
@app.route('/index')
def index():
    return render_template('index.html', title='Home')

#---------------------------------------------------------------

# @app.route('/upload', methods = ['POST'])
# def upload():
#     if request.method == 'POST':
#     	# ADD: error handling: wrong file type (not PDF)
#         file = request.files['file']
#         if file:
#         	filename = secure_filename(file.filename)
#         	file_contents = file.read()
#         	# session['file_data'] = file_contents
#             parse_result = parse(file_contents)
#             print parse_result
#             session['file_data'] = file_contents
#     return jsonify(dict(redirect='/result'))
    # return render_template('upload.html', data=a)
    # return render_template('upload.html', title='Upload Result', data=a)


@app.route('/upload', methods = ['GET', 'POST'])
def upload():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)

            # # temporarily save file on server
            # file.save(os.path.join(app.config['TEMP_FOLDER'], filename))

            # s3_bucket.upload_file(file, Key=filename)
            upload_bucket.put_object(Key=filename, Body=file.stream, ContentType=file.content_type)
            # s3.Bucket('tablereader').put_object(Key=filename, Body=file)
            
            # basedir = os.path.abspath(os.path.dirname(__file__))
            # file.save(os.path.join(basedir, app.config['UPLOAD_FOLDER'], filename)) # upload 
            # file.save(os.path.join(basedir, app.config['TEMP_FOLDER'], filename)) # upload 

            # obj = client.get_object(Bucket=upload_bucket, Key=filename)['Body']
            # obj = s3.Object('tablereader', filename).get()['Body']
            # print obj

            # path_to_bucket = 'http://s3.amazonaws.com/' + upload_bucket_name + '/' + filename
            path_to_bucket = 'https://' + upload_bucket_name + '.s3.amazonsws.com/' + filename
            # example: https://tablereader-uploads.s3.amazonaws.com/arabic.pdf (virtual-hosted style)

            response = client.list_objects_v2(Bucket=upload_bucket_name, Prefix=filename)
            print response 

            # df_result, download_name = (s3.Object('tablereader', filename).get()['Body'], filename)  
            # df_result, download_name = (parse(os.path.join(basedir, app.config['UPLOAD_FOLDER'], filename), filename))        
            # df_result, download_name = (parse(os.path.join(basedir, app.config['TEMP_FOLDER'], filename), filename))  
            df_result, download_name = parse(path_to_bucket, filename)                                                                                                                                                                                   
            df_result_html = df_result.to_html();

            csv_buffer = BytesIO()
            df_result.to_csv(csv_buffer)

            download_bucket.put_object(Key=download_name, Body=csv_buffer.getvalue())

            # # save cleaned file for download 
            # df_result.to_csv(os.path.join(os.path.join(basedir, app.config['DOWNLOAD_FOLDER'], download_name)))
            # df_result.to_csv(os.path.join(os.path.join(basedir, app.config['TEMP_FOLDER'], download_name)))

            return render_template('upload.html', data=df_result_html, filename=filename, dname=download_name)

          
                                                                                                                                                                                            

        

# @app.route('/upload', methods = ['POST'])
# def upload():
#     print "I made it to the upload() function"
#     return render_template('upload.html')


# # Listen for GET request to tablereader.herokuapp.com/sign_s3/
# @app.route('/sign-s3/')
# def sign_s3():
#     # Load info into the application (get bucket name)
#     S3_BUCKET = os.environ.get('S3_BUCKET')

#     # Load data from request 
#     file_name = request.args.get('file_name')
#     file_type = request.args.get('file_type')

#     # Initialize S3 client 
#     s3 = boto3.client('s3')

#     # Generate and return presigned URL 
#     presigned_post = s3.generate_presigned_post(
#       Bucket = S3_BUCKET,
#       Key = file_name,
#       Fields = {"acl": "public-read", "Content-Type": file_type},
#       Conditions = [
#         {"acl": "public-read"},
#         {"Content-Type": file_type}
#       ],
#       ExpiresIn = 3600
#     )

#     # Return data to the client
#     return json.dumps({
#       'data': presigned_post,
#       'url': 'https://%s.s3.amazonaws.com/%s' % (S3_BUCKET, file_name)
#     })


#---------------------------------------------------------------
# Tabula file processing helper method 
def parse(file_contents, filename):
    print "I am in the PARSE method"
    print "file contents: " + file_contents

    r = requests.get(file_contents)
    print "request: ", r
    print "request headers: ", r.headers

    ur = urllib.urlopen(file_contents)
    print "urllib: ", ur

    df = tabula.read_pdf(file_contents) # argument: file name (ex. 'data.pdf')
    file_chopped = ""
    if (filename.endswith(".pdf")):
        file_chopped = filename[:-len(".pdf")]
    download_name = file_chopped + '_output.csv'
    # csv = tabula.convert_into(file_contents, download_name, output_format="csv")
    return df, download_name 

#---------------------------------------------------------------

@app.route('/download', methods = ['GET', 'POST'])
def download():
    download_name = request.form['filename']
    # required: unique filename, location/path to saved CSV
    # basedir = os.path.abspath(os.path.dirname(__file__))
    # location = os.path.join(basedir, app.config['DOWNLOAD_FOLDER'], download_name)
    # return send_file(location, mimetype='text/csv', attachment_filename=download_name, as_attachment=True)
    
    # file = client.get_object(Bucket='tablereader-downloads', Key=download_name)
    # response = make_response(file['Body'].read())
    # response.headers['Content-Type'] = 'text/csv'

    file = client.get_object(Bucket=download_bucket_name, Key=download_name)
    return Response(
        file['Body'].read(),
        mimetype='text/csv',
        headers={"Content-Disposition": "attachment;filename=output.csv"}
        )

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

      print "pid: ", str(os.getpid())
      print folder 

      os.mkdir(folder)
      input_file = os.path.join(folder, secure_filename(file.filename))
      output_file = os.path.join(folder, app.config['OCR_OUTPUT_FILE'])
      file.save(input_file)

      command = ['tesseract', input_file, output_file, '-l', request.form['lang'], hocr]
      proc = subprocess.Popen(command, stderr=subprocess.PIPE)
      proc.wait()

      output_file += ext

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