"""
Recipe Transformer Project


"""
import json
import sys
from pathlib import Path
import os.path
import argparse
# from urlparse import urlparse
from urllib.parse import urlparse
from collections import defaultdict, OrderedDict
from operator import itemgetter
from bs4 import BeautifulSoup
import web
from web import form



from recipe_parser import RecipeParser



# Initialize Recipe Parser
recipe_parser = RecipeParser()
 

#============================================================================
# Start webPy environment
#============================================================================


def main_gui(method, txtContent):
	recipe_parser.parse_recipe()
	

	# download json file here
	with open('important_files/recipe_file.json') as f:
		data = json.load(f)
		return data

render = web.template.render('templates/')

urls = ('/', 'index')
class RecipeApp(web.application):
    def run(self, port=8080, *middleware):
        func = self.wsgifunc(*middleware)
        return web.httpserver.runsimple(func, ('127.0.0.1', port))

myform = form.Form( 
	form.File('recipe_file'),
    form.Dropdown('transformation', ['to_JSON', 'print_pretty']),
	)

class index: 
	def GET(self): 
		form = myform()
        # make sure you create a copy of the form by calling it (line above)
        # Otherwise changes will appear globally
		return render.formtest(form)
	
	def POST(self):
		form = myform()
		if not form.validates(): 
			return render.formtest(form)
		else:
			# https://webpy.org/cookbook/fileupload
			x = web.input(recipe_file={})
			recipeFile = x['recipe_file']
			# fileName = recipeFile.filename
			txtContent = recipeFile.file.read().decode(errors='replace')
			return main_gui(form['transformation'].value, txtContent)

if __name__ == "__main__":
	parser = argparse.ArgumentParser()
	parser.add_argument("--gui", help="run application on locally hosted webpage", action="store_true")

	args = parser.parse_args()
	if args.gui:
		sys.argv[1] = ''
		web.internalerror = web.debugerror
		app = RecipeApp(urls, globals())
		app.run()
