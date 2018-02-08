#---------------------------------------------------------------
# IMPORTS 
#---------------------------------------------------------------

import flask
import tabula
import pandas as pd 
import os
from flask import Flask, render_template, flash, redirect, url_for, request, jsonify, session
from app import app
from app.forms import LoginForm
from werkzeug.utils import secure_filename

UPLOAD_FOLDER = './uploads'
ALLOWED_EXTENSIONS = set(['pdf', 'txt', 'jpg'])
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

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
            file.save(os.path.join(basedir, app.config['UPLOAD_FOLDER'], filename))
            
            parse_result = parse(os.path.join(basedir, app.config['UPLOAD_FOLDER'], filename))

            return render_template('upload.html', data=parse_result)

            # return render_template('upload.html', data=filename)

#---------------------------------------------------------------

@app.route('/result', methods = ['GET', 'POST'])
def result():
    file_data = session.get('file_data', None)
    return render_template('upload.html', data=file_data)

#---------------------------------------------------------------
# File processing helper method 

def parse(file_contents):
    df = tabula.read_pdf(file_contents) # argument: file name (ex. 'data.pdf')
    # tabula.convert_into("data_1.pdf", "data_1_output.csv", output_format="csv")
    return df 

#---------------------------------------------------------------

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        flash('Login requested for user {}, remember_me={}'.format(
            form.username.data, form.remember_me.data))
        return redirect(url_for('index'))
    return render_template('login.html', title='Sign In', form=form)


