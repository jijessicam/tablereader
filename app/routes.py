#---------------------------------------------------------------
# IMPORTS 
#---------------------------------------------------------------

import flask
import tabula
import pandas as pd 
import os
import csv 
from flask import Flask, render_template, flash, redirect, url_for, request, jsonify, session, send_file
from app import app
from app.forms import LoginForm
from werkzeug.utils import secure_filename
import json, boto3


UPLOAD_FOLDER = './uploads'         # previously: './uploads' (on local) (should be 'tmp')
DOWNLOAD_FOLDER = './downloads' # how to deal with this???
TEMP_FOLDER = './tmp'
ALLOWED_EXTENSIONS = set(['pdf', 'txt', 'jpg'])
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['DOWNLOAD_FOLDER'] = DOWNLOAD_FOLDER
app.config['TEMP_FOLDER'] = TEMP_FOLDER

client = boto3.client('s3')
resource = boto3.resource('s3')
s3_bucket = resource.Bucket('tablereader')

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
            print "filename: " + filename

            # s3_bucket.upload_file(file, Key=filename)
            # s3_bucket.put_object(Key=filename, Body=file)
            # s3.Bucket('tablereader').put_object(Key=filename, Body=file)
            basedir = os.path.abspath(os.path.dirname(__file__))
            # rootdir = os.path.abspath(os.path.dirname(basedir))
            # print "rootdir: " + rootdir 
            # rootdir = app.root_path

            # file.save(os.path.join(basedir, app.config['UPLOAD_FOLDER'], filename)) # upload 
            file.save(os.path.join(basedir, app.config['TEMP_FOLDER'], filename)) # upload 

            # obj = client.get_object(Bucket=s3_bucket, Key=filename)['Body']
            # obj = s3.Object('tablereader', filename).get()['Body']
            # print obj
            # df_result, download_name = (s3.Object('tablereader', filename).get()['Body'], filename)  
            # df_result, download_name = (parse(os.path.join(basedir, app.config['UPLOAD_FOLDER'], filename), filename))        
            df_result, download_name = (parse(os.path.join(basedir, app.config['TEMP_FOLDER'], filename), filename))                                                                                                                                                                                     
            df_result_html = df_result.to_html();

            # # save cleaned file for download 
            # df_result.to_csv(os.path.join(os.path.join(basedir, app.config['DOWNLOAD_FOLDER'], download_name)))
            df_result.to_csv(os.path.join(os.path.join(basedir, app.config['TEMP_FOLDER'], download_name)))

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
# File processing helper method 
def parse(file_contents, filename):
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
    basedir = os.path.abspath(os.path.dirname(__file__))
    location = os.path.join(basedir, app.config['DOWNLOAD_FOLDER'], download_name)
    return send_file(location, mimetype='text/csv', attachment_filename=download_name, as_attachment=True)

