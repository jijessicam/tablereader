#---------------------------------------------------------------
# IMPORTS 
#---------------------------------------------------------------

from flask import render_template
from app import app, db

#---------------------------------------------------------------
# ERROR HANDLERS
#---------------------------------------------------------------

@app.errorhandler(404)
def not_found_error(error):
	return render_template('404.html'), 404

@app.errorhandler(400)
def internal_error(error):
	return render_template('500.html'), 500 