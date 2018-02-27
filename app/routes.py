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

UPLOAD_FOLDER = '/tmp'         # previously: './uploads' (on local)
DOWNLOAD_FOLDER = './downloads' # how to deal with this???
ALLOWED_EXTENSIONS = set(['pdf', 'txt', 'jpg'])
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['DOWNLOAD_FOLDER'] = DOWNLOAD_FOLDER

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
            basedir = os.path.abspath(os.path.dirname(__file__))
            file.save(os.path.join(basedir, app.config['UPLOAD_FOLDER'], filename)) # upload 
            
            df_result, download_name = (parse(os.path.join(basedir, app.config['UPLOAD_FOLDER'], filename), filename))                                                                                                                                                                                        
            df_result_html = df_result.to_html();

            # save cleaned file for download 
            df_result.to_csv(os.path.join(os.path.join(basedir, app.config['DOWNLOAD_FOLDER'], download_name)))
        

            return render_template('upload.html', data=df_result_html, filename=filename, dname=download_name)

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

