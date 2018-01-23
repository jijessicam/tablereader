import flask
from flask import render_template, flash, redirect, url_for, request
from app import app
from app.forms import LoginForm
from werkzeug.utils import secure_filename

@app.route('/')
@app.route('/index')
def index():

    return render_template('index.html', title='Home')

#---------------------------------------------------------------

@app.route('/upload', methods = ['POST'])
def upload():
    if request.method == 'POST':
    	# ADD: error handling: wrong file type (not PDF)
        file = request.files['file']
        if file:
        	filename = secure_filename(file.filename)
        	a = file.read()
        	print a
    return render_template('upload.html', title='Upload Result', data=a)

#---------------------------------------------------------------

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        flash('Login requested for user {}, remember_me={}'.format(
            form.username.data, form.remember_me.data))
        return redirect(url_for('index'))
    return render_template('login.html', title='Sign In', form=form)


if __name__ == '__main__':
    app.run(debug=True)