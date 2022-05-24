"""
Recipe Transformer Project

Given a URL to a recipe from AllRecipes.com, this program uses Natural Language Processing to transform any recipe, based on
user's input, into any of the following categories:  
	* To and from vegetarian 
	* To and from vegan
	* To and from healthy 
	* To and from pescatarian
	* To Style of cuisine (i.e. to Thai)
	* Cooking method (from bake to stir fry, for example)


Authors: 
 	* David Wallach
 	* Junhao Li
 	* Bodhi Alarcon


 github repository: https://github.com/dwallach1/RecipeTransformer

"""
import time
import random
import re
import json
import sys
from pathlib import Path
import os.path
import argparse
# from urlparse import urlparse
from urllib.parse import urlparse
from collections import defaultdict, OrderedDict
from operator import itemgetter
import textwrap
import copy
from xmlrpc.client import MAXINT
import requests
from bs4 import BeautifulSoup
import web
from web import form

import nltk
from nltk import word_tokenize, pos_tag

from recipe_parser import RecipeParser
nltk.download('wordnet')
nltk.download('omw-1.4')
import re
from nltk.corpus import wordnet
from nltk.tokenize import RegexpTokenizer
from nltk.corpus import stopwords
from nltk import chunk,pos_tag

# https://www.projectpro.io/recipes/install-and-use-spacy-models#mcetoc_1g1fr6f4r7
import spacy
# spacy.load('en')
# from spacy.lang.en import English
# parser = English()
nlp = spacy.load("en_core_web_sm")
import json
import re

DEBUG = False

# simple regex used to find specific attributes in strings 
measure_regex = '(cup|spoon|fluid|ounce|pinch|gill|pint|quart|gallon|pound|drops|recipe|slices|pods|package|can|head|halves)'
tool_indicator_regex = '(pan|skillet|pot|sheet|grate|whisk|griddle|bowl|oven|dish)'
method_indicator_regex = '(boil|bake|baking|simmer|stir|roast|fry)'
time_indicator_regex = '(min|hour)'

# these are used as last resort measures to sort out names, descriptors, and preperation words that our system is having trouble parsing
descriptor_regex = '(color|mini|container|skin|bone|halves|fine|parts|leftover|style|frying|breast)'
preperation_regex = '(room|temperature|divided|sliced|dice|mince|chopped|quartered|cored|shredded|seperated|pieces)'
names_regex = '(garlic|poppy|baking|sour|cream|broth|chicken|olive|mushroom|green|vegetable|bell)'



# start of word banks

healthy_substitutes = {
	# The way this dict is structures is so that the values are used to easily instatiate new Ingredient objects 
	# the quantities are just for parsing, they are updated to be the amount used of the unhealthy version in the recipe
	# inside the Recipe to_healthy method
	'oil': 	'2 tablespoons of Prune Puree',
	'cheese': '3 tablespoons of Nutritional Yeast',
	'pasta': '8 ounces of shredded zucchini',
	'flour': '1 cup of whole-wheat flour',
	'butter': '3 tablespoons of unsweetened applesauce',
	'cream': '3 cups of greek yogurt',
	'eggs': '3 egg whites',
	'milk': '4 ounces of skim milk',
	'potatoes': '4 handfuls of arugula',
	'french fries': '4 handfuls of arugula',
	'yogurt': '2 cups of low-fat cottage cheese'

}

dairy_substitutes = {
	# The way this dict is structures is so that the values are used to easily instatiate new Ingredient objects 
	# the quantities are just for parsing, they are updated to be the amount used of the unhealthy version in the recipe
	# inside the Recipe to_healthy method
	'butter': '2 tablespoons of olive oil',
	'cheese': '3 tablespoons of yeast flakes',
	'milk': '12 ounces of soy milk',
	'sour cream': '2 avacados',
	'cream': '2 cups of almond milk yogurt',
	'ice cream': '2 cups of sorbet'

}

# do not need a dict because we switch based on 'type' attribute instead of 'name' attribute
meat_substitutes = [
			'12 ounces of Tofu', 
			'1 cup ICantBelieveItsNotMeat',
			'12 ounces of Tempeh',
			'12 ounces of grilled Seitan',
			'8 ounces of textured vegetable protien',
			'12 ounces of gluten-free vegan meat',
			'4 cups of Jackfruit',
			'3 large portobello mushrooms',
			'4 cups of lentils',
			'4 cups of legumes'
	]

# use Tuples to tag the substitutes
unhealthy_substitutes = [
		('1 pound of fried chicken', 'M'),
		('4 pieces of milanesa', 'M'),
		('3 fried eggplants', 'V'),
		('10 fried pickles', 'V')


	]


# build list dynamically from wikipedia using the build_dynamic_lists() function -- used to tag the domain of an ingredient
sauce_list = []
vegetable_list = []
herbs_spice_list = []
dairy_list = []
meat_list = []
grain_list = []
fruit_list = []
seafood_list = []

# Initialize Recipe Parser
recipe_parser = RecipeParser()
 
class Ingredient(object):
	"""
	Represents an Ingredient in the recipe. Ingredients have assoiciated quantities, names, measurements, 
	preperation methods (i.e. finley chopped), and descriptors (i.e. fresh, extra-virgin). Uses NLTK to tag each word's part 
	of speach using the pos_tag fuction. From there the module handles extracting out the relavent information and storing it in the appropiate
	attributes of the object.

	For pos_tag:
		* ADJ	adjective	new, good, high, special, big, local
		* ADP	adposition	on, of, at, with, by, into, under
		* ADV	adverb	really, already, still, early, now
		* CONJ	conjunction	and, or, but, if, while, although
		* DET	determiner, article	the, a, some, most, every, no, which
		* NOUN	noun	year, home, costs, time, Africa
		* NUM	numeral	twenty-four, fourth, 1991, 14:24
		* PRT	particle	at, on, out, over per, that, up, with
		* PRON	pronoun	he, their, her, its, my, I, us
		* VERB	verb
		* .	    punctuation marks	. , ; !
		* X	    other	ersatz, esprit, dunno, gr8, univeristy
	"""
	def __init__(self, description):
		description_tagged = pos_tag(word_tokenize(description))

		# if DEBUG:
		# 	print ('tags: {}'.format(description_tagged))

		self.name = self.find_name(description_tagged)
		self.quantity = self.find_quantity(description)				# do not use tagged description -- custom parsing for quantities
		self.measurement = self.find_measurement(description_tagged, description)
		self.descriptor = self.find_descriptor(description_tagged)
		self.preperation = self.find_preperation(description_tagged)
		self.type = self.find_type()

		if DEBUG:
			print ('parsing ingredient: {}'.format(description))
			print ('name: {}'.format(self.name))
			print ('quantity: {}'.format(self.quantity))
			print ('measurement: {}'.format(self.measurement))
			print ('descriptor: {}'.format(self.descriptor))
			print ('preperation: {}').format(self.preperation)
	

	def __str__(self):
		"""
		String representation of an Ingredient instance
		"""
		return self.name


	def __repr__(self):
		"""
		How a Ingredient object is represented
		"""
		return self.name


	def __eq__(self, other):
		"""
		Defines what makes two Ingredient instances equal
		"""
		if isinstance(self, other.__class__):
			return self.__dict__ == other.__dict__
		return False


	def find_name(self, description_tagged):
		"""
		looks for name of the ingredient from the description. Finds the nouns that are not measurements
		"""
		name = [d[0] for d in description_tagged if ((d[1] == 'NN' or d[1] == 'NNS' or d[1] == 'NNP') 
													and not re.search(measure_regex, d[0], flags=re.I)
													and not re.search(descriptor_regex, d[0], flags=re.I)
													and not re.search(preperation_regex, d[0], flags=re.I))
											or re.search(names_regex, d[0], re.I)]
		if len(name) == 0:
			return description_tagged[-1][0]
		return ' '.join(name)


	def find_quantity(self, description):
		"""
		looks for amount descriptors in the ingredient description.
		if none are apparent, it returns zero. Else it converts fractions to floats and
		aggregates measurement (i.e. 1 3/4 --> 1.75)
		"""
		wholes = re.match(r'([0-9])\s', description)
		fractions = re.search(r'([0-9]\/[0-9])', description)

		if fractions: 
			fractions = fractions.groups(0)[0]
			num = float(fractions[0])
			denom = float(fractions[-1])
			fractions = num / denom
		
		if wholes: wholes = int(wholes.groups(0)[0])

		total = float(wholes or 0.0) + float(fractions or 0.0)

		return total


	def find_measurement(self, description_tagged, description):
		"""
		looks for measurements such as cups, teaspoons, etc. 
		Uses measure_regex which is a compilation of possible measurements.
		"""
		measurement = [d[0] for d in description_tagged if re.search(measure_regex, d[0], flags=re.I)]
		m = ' '.join(measurement)
		if re.search('package', m, flags=re.I):
			extra = description[description.find("(")+1:description.find(")")]
			return extra + ' package(s)'
		if re.search('can', m, flags=re.I):
			extra = description[description.find("(")+1:description.find(")")]
			return extra + ' can(s)'

		if description.find("(") > -1 and any(char.isdigit() for char in description):
			return description[description.find("(")+1:description.find(")")]

		return m


	def find_descriptor(self, description_tagged):
		"""
		looks for descriptions such as fresh, extra-virgin by finding describing words such as
		adjectives
		"""
		descriptors = [d[0] for d in description_tagged if ( 
															(d[1] == 'JJ' or d[1] == 'RB') 
															and not re.search(measure_regex, d[0], flags=re.I)
															and not re.search(names_regex, d[0], flags=re.I)
														)
														or re.search(descriptor_regex, d[0], flags=re.I)]
		return descriptors


	def find_preperation(self, description_tagged):
		"""
		find all preperations (finely, chopped) by finding action words such as verbs 
		"""
		preperations = [d[0] for d in description_tagged if (
															d[1] == 'VB' or d[1] == 'VBD' 
															or re.search(preperation_regex, d[0], flags=re.I)
															)
															and not re.search(names_regex, d[0], flags=re.I)]
		for i, p in enumerate(preperations):
			if p == 'taste':
				preperations[i] = 'to taste'
		return preperations


	def find_type(self):
		"""
		attempts to categorize ingredient for Recipe methods to work more smoothly and correctly

		* H --> Herbs / Spices
		* V --> Vegetable 
		* M --> Meat
		* D --> Dairy
		* F --> Fruit
		* S --> Sauce
		* P --> Pescatarian (Seafood)
		* ? --> Misc. 

		ordered by precedence of how telling the classification is --> bound to one classification
		"""

		# special cases:
		if self.name.lower().find('sauce') >= 0: return 'S'

		# normal execution:
		types = ''
		if any(set(self.name.lower().split(' ')).intersection(set(example.lower().split(' '))) for example in meat_list) and len(types) == 0: types ='M' 
		if any(set(self.name.lower().split(' ')).intersection(set(example.lower().split(' '))) for example in vegetable_list) and len(types) == 0: types = 'V'
		if any(set(self.name.lower().split(' ')).intersection(set(example.lower().split(' '))) for example in dairy_list) and len(types) == 0: types = 'D' 
		if any(set(self.name.lower().split(' ')).intersection(set(example.lower().split(' '))) for example in grain_list) and len(types) == 0: types = 'G'
		if any(set(self.name.lower().split(' ')).intersection(set(example.lower().split(' '))) for example in sauce_list) and len(types) == 0: types = 'S'
		if any(set(self.name.lower().split(' ')).intersection(set(example.lower().split(' '))) for example in seafood_list) and len(types) == 0: types = 'P'
		if any(set(self.name.lower().split(' ')).intersection(set(example.lower().split(' '))) for example in herbs_spice_list) and len(types) == 0: types = 'H'
		if any(set(self.name.lower().split(' ')).intersection(set(example.lower().split(' '))) for example in fruit_list) and len(types) == 0: types = 'F' 
		if len(types) == 0: types = '?'
		return types


class Instruction(object):
	"""
	Represents an instruction to produce the Recipe. Each instruction has a set of tools used for cooking and set of 
	methods also used for cooking. There is a time field to denote the amount of time the instruction takes to complete.
	"""
	def __init__(self, instruction):
		self.instruction = instruction
		self.instruction_words = word_tokenize(self.instruction)
		self.cooking_tools = self.find_tools(self.instruction_words)
		self.cooking_methods = self.find_methods(self.instruction_words)
		self.time = self.find_time(self.instruction_words)
		self.ingredients = None


	def find_tools(self, instruction_words):
		"""
		looks for any and all cooking tools apparent in the instruction text by using the tool_indicator_regex
		variable
		"""
		cooking_tools = []
		for word in instruction_words:
			if re.search(tool_indicator_regex, word, flags=re.I):
				cooking_tools.append(word)
		wordset = set(cooking_tools)
		return [item for item in wordset if item.istitle() or item.title() not in wordset]


	def find_methods(self, instruction_words):
		"""
		looks for any and all cooking methods apparent in the instruction text by using the method_indicator_regex
		variable
		"""
		cooking_methods = []
		for word in instruction_words:
			if re.search(method_indicator_regex, word, flags=re.I):
				cooking_methods.append(word)
			if re.search('preheat', word, re.I):
				cooking_methods.append('bake')

		wordset = set(cooking_methods)
		return [item for item in wordset if item.istitle() or item.title() not in wordset]


	def find_time(self, instruction):
		"""
		looks for all time notations apparent in the instruction text by using the time_indicator_regex
		variable and aggregating the total times using typecasting
		"""
		time = 0
		for i, word in enumerate(instruction):
			# if we are talking about degrees, then extracting numbers are not associated with time
			if word == 'degrees': return 0
			
			if re.search(time_indicator_regex, word, flags=re.I):
				try:
					if re.search('(hour)', word, flags=re.I):
						time += int(instruction[i-1]) * 60
					else:
						time += int(instruction[i-1])
				except:
					pass
		return time


	def update_instruction(self):
		"""
		Uses the instances word list to update the objects instruction attribute
		"""
		self.instruction = ' '.join(self.instruction_words)


class Recipe(object):
	"""
	Used to represent a recipe. Data for each recipe can be found 
	on AllRecipes.com. 
	"""
	def __init__(self, **kwargs):
		for key, value in kwargs.items():
			setattr(self, key, value)

		self.text_instructions = self.instructions;		# store the original instructions, 
														# idea for right now is to modify the original instructions for transformations
		self.ingredients = [Ingredient(ing) for ing in self.ingredients]		# store ingredients in Ingredient objects
		self.instructions = [Instruction(inst) for inst in self.instructions]	# store instructions in Instruction objects
		self.cooking_tools, self.cooking_methods  = self.parse_instructions()	# get aggregate tools and methods apparent in all instructions
		self.update_instructions()			# as part of the steps requirement, add the associated ingredients to each instruction step


		self.instructions = [i for i in self.instructions if len(i.instruction)]
		# save original copy to compare with the transformations
		self.original_recipe = copy.deepcopy(self)
	

	def parse_instructions(self):
		"""
		Gathers aggregate data from all instructions to provide overall cooking tools and methods instead of 
		per instruction basis
		"""
		cooking_tools =  []
		cooking_methods = []
		for inst in self.instructions:
			cooking_tools.extend(inst.cooking_tools)
			cooking_methods.extend(inst.cooking_methods)
		return list(set(cooking_tools)), list(set(cooking_methods))
	

	def update_instructions(self):
		"""
		To convert instructions into steps, we need to store the associated ingredients as part an attribute for 
		each instruction. This method does that update
		"""
		for i, instruction in enumerate(self.instructions):
			ingredients = [ingredient.name for ingredient in self.ingredients if instruction.instruction.find(ingredient.name) >= 0]
			self.instructions[i].ingredients = list(set(ingredients))


	def to_JSON(self, original=False):
		"""
		convert representation to easily parseable JSON format
		"""
		data = OrderedDict()
		if original: self = self.original_recipe
		data['name'] = self.name
		data['url'] = self.url
		data['cooking tools'] = self.cooking_tools
		data['cooking method'] = self.cooking_methods
		ing_list = []
		for ingredient in self.ingredients:
			ing_attrs = {}
			for attr, value in ingredient.__dict__.iteritems():
				ing_attrs[attr] = value
			ing_list.append(ing_attrs)

		data['ingredients'] = ing_list

		inst_list = []
		for instruction in self.instructions:
			inst_attrs = {}
			include = True
			for attr, value in instruction.__dict__.iteritems():
				if attr == 'instruction_words': continue
				if attr == 'instruction' and len(value) == 0: include = False
				inst_attrs[attr] = value
			if include: inst_list.append(inst_attrs)

		data['steps'] = inst_list
		parsed = json.dumps(data, indent=4)
		return parsed


	def print_pretty(self):
		"""
		print a human friendly version of the recipe
		"""
		s = ""
		s += '\nIngredients List:'
		for ing in self.ingredients:			
			# only add quantity, measurement, descriptor, and preperation if we have them
			quant = ''
			if ing.quantity != 0:
				quant = "{} ".format(round(ing.quantity, 2) if ing.quantity % 1 else int(ing.quantity))

			measure = ''
			if ing.measurement != "":
				measure = ing.measurement + ' '

			descr = ''
			if len(ing.descriptor) > 0:
				descr = ' '.join(ing.descriptor) + ' '
			
			prep = ''
			if len(ing.preperation) > 0:
				prep = ', ' + ' and '.join(ing.preperation)
			
			full_ing = '{}{}{}{}{}'.format(quant, measure, descr, ing.name, prep)

			s += full_ing

		s += '\nInstructions:'
		for i, t_inst in enumerate(self.text_instructions[:-1]):
			s += textwrap.fill('{}. {}'.format(i+1, t_inst), 80)
		return s


	def compare_to_original(self):
		"""
		Compares the current recipe to the original recipe the object was instatiated with.
		If no changes were made, then they will be identical. 
		"""
		s = ""
		try: 
			s += '\n-----------------------'
			s += '\nThe following changes were made to the original recipe: '
			if len(self.original_recipe.ingredients) < len(self.ingredients):
				for i in range(len(self.original_recipe.ingredients), len(self.ingredients)):
					s += '\n* added {}'.format(self.ingredients[i].name)
			else:
				for i in range(len(self.original_recipe.ingredients)):
					if self.original_recipe.ingredients[i].name != self.ingredients[i].name:
						s += '\n* {} ---> {}'.format(self.original_recipe.ingredients[i].name, self.ingredients[i].name)
			if len(self.original_recipe.instructions) < len(self.instructions):
				for i in range(len(self.original_recipe.instructions), len(self.instructions)):
					s += '\n* added {}'.format(self.instructions[i].instruction)
			else:
				for i in range(len(self.original_recipe.instructions)):
					if self.original_recipe.instructions[i].instruction != self.instructions[i].instruction:
						s += '\n* {}\n ---> {}'.format(self.original_recipe.instructions[i].instruction, self.instructions[i].instruction)
			s += '\n-----------------------'
		except:
			s += '\n-----------------------'
		return s


	def to_style(self, style, threshold=1.0):
		"""
		search all recipes for recipes pertaining to the 'style' parameter and builds frequency dictionary.
		Then adds/removes/augemnets ingredients to make it more like the 'style' of cuisine. 
		"""

		url = 'https://www.allrecipes.com/search/results/?wt={}&sort=re'.format(style)

		# retrieve data from url
		result = requests.get(url, timeout=10)
		c = result.content

		# store in BeautifulSoup object to parse HTML DOM
		soup = BeautifulSoup(c, "lxml")

		# find all urls that point to recipe pages 
		style_recipes = [urlparse(url['href']) for url in soup.find_all('a', href=True)]	# find all urls in HTML DOM
		style_recipes = [r.geturl() for r in style_recipes if r.path[1:8] == 'recipe/']		# filter out noise urls 
		style_recipes = list(set(style_recipes))											# don't double count urls 

		# parse the urls and create new Recipe objects
		style_recipes = [Recipe(**parse_url(recipe)) for recipe in style_recipes]	# instantiate all recipe objects for each found recipe
		# print ('found {} recipes cooked {} style'.format(len(style_recipes), style))

		# unpack all ingredients in total set of new recipes of type 'style'
		ingredients_ = [recipe.ingredients for recipe in style_recipes]
		ingredients = []
		for ingredient in ingredients_:
			ingredients.extend(ingredient)
		
		# hold reference to just the ingredient names for frequency distrobutions
		ingredient_names = [ingredient.name for ingredient in ingredients]

		# hold reference to ingredients from original recipe
		current_ingredient_names = [ingredient.name for ingredient in self.ingredients]
		# print ('current ingredients from original recipe are {}'.format(current_ingredient_names))

		# extract only the names and not the freqs -- will be sorted in decreasing order
		key_new_ingredients = [freq[0] for freq in self.freq_dist(ingredient_names)]
		# remove the ingredients that are already in there
		key_new_ingredients = [ingredient for ingredient in key_new_ingredients if not(ingredient in current_ingredient_names)][:10]
		# print ('key ingredients from {} recipes found are {}'.format(style, key_new_ingredients))


		# get the whole ingredient objects -- this is to change actions accorgingly
		# e.g. if we switch from pinches of salt to lemon, we need to change pinches to squeezes
		ingredient_changes = [ingredient for ingredient in ingredients if (ingredient.name in key_new_ingredients) and not(ingredient.name in current_ingredient_names)]
		
		# clear up some memory
		del ingredients_
		del ingredients
		del ingredient_names
		del style_recipes
		del soup


		tmp = []
		new = []
		for ingredient in ingredient_changes:
			if ingredient.name in tmp: continue
			tmp.append(ingredient.name)
			new.append(ingredient)

		ingredient_changes = copy.deepcopy(new)
		
		# no longer needed --> temporary use
		del new
		del tmp


		# Find out most common ingredients from all recipes of type 'style' -- then decide which to switch and/or add to current recipe
		try: most_common_sauce = next(ingredient for ingredient in ingredient_changes if ingredient.type == 'S')
		except StopIteration: most_common_sauce = None 
		try: most_common_meat = next(ingredient for ingredient in ingredient_changes if ingredient.type == 'M')
		except StopIteration: most_common_meat = None
		try: most_common_vegetable = next(ingredient for ingredient in ingredient_changes if ingredient.type == 'V')
		except StopIteration: most_common_vegetable = None
		try: most_common_grain = next(ingredient for ingredient in ingredient_changes if ingredient.type == 'G')
		except StopIteration: most_common_grain = None
		try: most_common_dairy = next(ingredient for ingredient in ingredient_changes if ingredient.type == 'D')
		except StopIteration: most_common_dairy = None
		try: most_common_herb = next(ingredient for ingredient in ingredient_changes if ingredient.type == 'H')
		except StopIteration: most_common_herb = None
		try: most_common_fruit = next(ingredient for ingredient in ingredient_changes if ingredient.type == 'F')
		except StopIteration: most_common_fruit = None
		

		# switch the ingredients
		most_commons = filter(lambda mc: mc != None, 
					[most_common_meat, most_common_vegetable, most_common_sauce, most_common_grain, 
					 most_common_herb, most_common_dairy, most_common_fruit])

		try: most_commons = most_commons[:int(7*threshold)]
		except: pass # this means we didnt find enough to choose -- just keep whole list b/c under threshold anyways

		# print ('most commons {}'.format([m.name for m in most_commons]))


		for new_ingredient in most_commons:
			try: current_ingredient = next(ingredient for ingredient in self.ingredients if ingredient.type == new_ingredient.type)
			except StopIteration: continue
			self.swap_ingredients(current_ingredient, new_ingredient)

		# update name
		self.name = self.name + ' (' + style + ')'

	def freq_dist(self, data):
		"""
		builds a frequncy distrobution dictionary sorted by the most commonly occuring words 
		"""
		freqs = defaultdict(lambda: 0)
		for d in data:
			freqs[d] += 1
		return sorted(freqs.items(), key=itemgetter(1), reverse=True)


	def swap_ingredients(self, current_ingredient, new_ingredient):
		"""
		replaces the current_ingredient with the new_ingredient. 
		Updates the associated instructions, times, and ingredients. 
		"""
		# (1) switch the ingredients in self.ingredients list
		for i, ingredient in enumerate(self.ingredients):
			if ingredient.name == current_ingredient.name:
				self.ingredients[i] = new_ingredient

		# (2) update the instructions that mention it
		name_length = len(current_ingredient.name.split(' '))
		for i, instruction in enumerate(self.instructions):
			for j in range(len(instruction.instruction_words) - name_length):
				if current_ingredient.name == ' '.join(instruction.instruction_words[j:j+name_length]):
					self.instructions[i].instruction_words[j] = new_ingredient.name

					# get rid of any extra words
					for k in range(1, name_length):
						self.instructions[i].instruction_words[j+k] == ''
					self.instructions[i].update_instruction()
									

def remove_non_numerics(string): return re.sub('[^0-9]', '', string)


def parse_url(url):
	"""
	reads the url and creates a recipe object.
	Urls are expected to be from AllRecipes.com


	Builds a dictionary that is passed into a Recipe object's init function and unpacked.
	The dictionary is set up as 

	{
		name: string
		preptime: int
		cooktime: int
		totaltime: int
		ingredients: list of strings
		instructions: list of strings
		calories: int
		carbs: int
		fat: int
		protein: int
		cholesterol: int
		sodium: int

	}
	"""
	# retrieve data from url
	result = requests.get(url, timeout=10)
	c = result.content

	# store in BeautifulSoup object to parse HTML DOM
	soup = BeautifulSoup(c, "lxml")


	# find name 
	try: name = soup.find('h1', {'itemprop': 'name'}).text
	except: name = ""
	
	# find relevant time information
	# some recipes are missing some of the times 
	try: preptime  = remove_non_numerics(soup.find('time', {'itemprop': 'prepTime'}).text)
	except: preptime = 0
	try: cooktime  = remove_non_numerics(soup.find('time', {'itemprop': 'cookTime'}).text)
	except: cooktime = 0
	try: totaltime = remove_non_numerics(soup.find('time', {'itemprop': 'totalTime'}).text)
	except: totaltime = 0
	
	# find ingredients
	ingredients = [i.text for i in soup.find_all('span', {'class': 'recipe-ingred_txt added'})]

	# find instructions
	instructions = [i.text for i in soup.find_all('span', {'class': 'recipe-directions__list--item'})] 


	# nutrition facts
	calories = remove_non_numerics(soup.find('span', {'itemprop': 'calories'}).text)				
	carbs = soup.find('span', {'itemprop': 'carbohydrateContent'}).text			    # measured in grams
	fat = soup.find('span', {'itemprop': 'fatContent'}).text						# measured in grams
	protien  = soup.find('span', {'itemprop': 'proteinContent'}).text			    # measured in grams
	cholesterol  = soup.find('span', {'itemprop': 'cholesterolContent'}).text	    # measured in miligrams
	sodium  = soup.find('span', {'itemprop': 'sodiumContent'}).text			        # measured in grams

	if DEBUG:
		print ('recipe is called {}'.format(name))
		print ('prep time is {} minutes, cook time is {} minutes and total time is {} minutes'.format(preptime, cooktime, totaltime))
		print ('it has {} ingredients'.format(len(ingredients)))
		print ('it has {} instructions'.format(len(instructions)))
		print ('it has {} calories, {} g of carbs, {} g of fat, {} g of protien, {} mg of cholesterol, {} mg of sodium'.format(calories, carbs, fat, protien, cholesterol, sodium))


	return {
			'name': name,
			'preptime': preptime,
			'cooktime': cooktime,
			'totaltime': totaltime,
			'ingredients': ingredients,
			'instructions': instructions,
			'calories': calories,
			'carbs': carbs,
			'fat': fat,
			'protien': protien,
			'cholesterol': cholesterol,
			'sodium': sodium,
			'url': url
			}


def build_dynamic_lists():
	"""
	fills the lists of known foods from websites -- used to tag ingredients 
	"""
	global vegetable_list
	global sauce_list
	global herbs_spice_list
	global dairy_list
	global meat_list
	global grain_list
	global fruit_list
	global seafood_list

	# build vegetable list
	url = 'https://simple.wikipedia.org/wiki/List_of_vegetables'
	result = requests.get(url, timeout=10)
	c = result.content

	# store in BeautifulSoup object to parse HTML DOM
	soup = BeautifulSoup(c, "lxml")

	lis = [li.text.strip() for li in soup.find_all('li')]
	lis_clean = []
	for li in lis:
		if li == 'Lists of vegetables': break
		if len(li) == 1: continue
		if re.search('\d', li): continue
		if re.search('\n', li): continue
		lis_clean.append(li.lower())
	vegetable_list = lis_clean


	# build herbs and spices list
	url = 'https://en.wikipedia.org/wiki/List_of_culinary_herbs_and_spices'
	result = requests.get(url, timeout=10)
	c = result.content

	# store in BeautifulSoup object to parse HTML DOM
	soup = BeautifulSoup(c, "lxml")

	lis = [li.text.strip() for li in soup.find_all('li')][3:]
	lis_clean = []
	for li in lis:
		if len(li) == 1: continue
		if re.search('\d', li): continue
		if re.search('\n', li): continue
		if li == 'Category': break
		lis_clean.append(li.lower())
	herbs_spice_list = lis_clean


	# build sauces list
	url = 'https://en.wikipedia.org/wiki/List_of_sauces'
	result = requests.get(url, timeout=10)
	c = result.content

	# store in BeautifulSoup object to parse HTML DOM
	soup = BeautifulSoup(c, "lxml")

	lis = [li.text.strip() for li in soup.find_all('li')]
	lis_clean = []
	for li in lis:
		if len(li) == 1: continue
		if re.search('\d', li): continue
		if re.search('\n', li): continue
		if li == 'Category': break
		lis_clean.append(li.lower())
	sauce_list = lis_clean


	# build meat list
	url = 'http://naturalhealthtechniques.com/list-of-meats-and-poultry/'
	result = requests.get(url, timeout=10)
	c = result.content

	# store in BeautifulSoup object to parse HTML DOM
	soup = BeautifulSoup(c, "lxml")

	# div = soup.find('div', {'class': 'entry-content'})
	# lis = [li.text.strip() for li in div.find_all('li')]
	lis = [li.text.strip() for li in soup.find_all('li')]
	lis_clean = []
	for li in lis:
		if len(li) == 1: continue
		if re.search('\d', li): continue
		if re.search('\n', li): continue
		lis_clean.append(li.lower())
	meat_list = lis_clean

	# build seafood_list and also extend to the meat_list
	url = 'http://naturalhealthtechniques.com/list-of-fish-and-seafood/'
	result = requests.get(url, timeout=10)
	c = result.content

	# store in BeautifulSoup object to parse HTML DOM
	soup = BeautifulSoup(c, "lxml")

	# div = soup.find('div', {'class': 'entry-content'})
	# lis = [li.text.strip() for li in div.find_all('li')]
	lis = [li.text.strip() for li in soup.find_all('li')]
	lis_clean = []
	for li in lis:
		if len(li) == 1: continue
		if re.search('\d', li): continue
		if re.search('\n', li): continue
		lis_clean.append(li.lower())
	meat_list.extend(lis_clean)
	seafood_list = lis_clean

	# build dairy list
	url = 'http://naturalhealthtechniques.com/list-of-cheese-dairy-products/'
	result = requests.get(url, timeout=10)
	c = result.content

	# store in BeautifulSoup object to parse HTML DOM
	soup = BeautifulSoup(c, "lxml")

	# div = soup.find('div', {'class': 'entry-content'})
	# lis = [li.text.strip() for li in div.find_all('li')]
	lis = [li.text.strip() for li in soup.find_all('li')]
	lis_clean = []
	for li in lis:
		if len(li) == 1: continue
		if re.search('\d', li): continue
		if re.search('\n', li): continue
		lis_clean.append(li.lower())
	dairy_list = lis_clean


	# build grains list 
	url = 'http://naturalhealthtechniques.com/list-of-grains-cereals-pastas-flours/'
	result = requests.get(url, timeout=10)
	c = result.content

	# store in BeautifulSoup object to parse HTML DOM
	soup = BeautifulSoup(c, "lxml")

	# div = soup.find('div', {'class': 'entry-content'})
	# lis = [li.text.strip() for li in div.find_all('li')]
	lis = [li.text.strip() for li in soup.find_all('li')]
	lis_clean = []
	for li in lis:
		if len(li) == 1: continue
		if re.search('\d', li): continue
		if re.search('\n', li): continue
		lis_clean.append(li.lower())
	grain_list = lis_clean


	# build grains list 
	url = 'http://naturalhealthtechniques.com/list-of-fruits/'
	result = requests.get(url, timeout=10)
	c = result.content

	# store in BeautifulSoup object to parse HTML DOM
	soup = BeautifulSoup(c, "lxml")

	# div = soup.find('div', {'class': 'entry-content'})
	# lis = [li.text.strip() for li in div.find_all('li')]
	lis = [li.text.strip() for li in soup.find_all('li')]
	lis_clean = []
	for li in lis:
		if len(li) == 1: continue
		if re.search('\d', li): continue
		if re.search('\n', li): continue
		lis_clean.append(li.lower())
	fruit_list = lis_clean


def timeit(method):
    def timed(*args, **kw):
        ts = time.time()
        result = method(*args, **kw)
        te = time.time()
        if 'log_time' in kw:
            name = kw.get('log_name', method.__name__.upper())
            kw['log_time'][name] = int((te - ts))
        else:
            print('%r  %2.2f s' % \
                  (method.__name__, (te - ts)))
        return result
    return timed

@timeit
def main():
	"""
	main function -- runs all initalization and any methods user wants 
	"""

	# parse websites to build global lists -- used for Ingredient type tagging
	build_dynamic_lists()

	URL = 'http://allrecipes.com/recipe/234667/chef-johns-creamy-mushroom-pasta/?internalSource=rotd&referringId=95&referringContentType=recipe%20hub'
	# URL = 'http://allrecipes.com/recipe/21014/good-old-fashioned-pancakes/?internalSource=hub%20recipe&referringId=1&referringContentType=recipe%20hub'
	# URL = 'https://www.allrecipes.com/recipe/60598/vegetarian-korma/?internalSource=hub%20recipe&referringId=1138&referringContentType=recipe%20hub'
	# URL = 'https://www.allrecipes.com/recipe/8836/fried-chicken/?internalSource=hub%20recipe&referringContentType=search%20results&clickId=cardslot%202'
	# URL = 'https://www.allrecipes.com/recipe/52005/tender-italian-baked-chicken/?internalSource=staff%20pick&referringId=201&referringContentType=recipe%20hub'

	# URLS = [
	# 	'https://www.allrecipes.com/recipe/213717/chakchouka-shakshouka/?internalSource=hub%20recipe&referringContentType=search%20results&clickId=cardslot%201',
	# 	'https://www.allrecipes.com/recipe/216756/baked-ham-and-cheese-party-sandwiches/?internalSource=hub%20recipe&referringContentType=search%20results&clickId=cardslot%205',
	# 	'https://www.allrecipes.com/recipe/234592/buffalo-chicken-stuffed-shells/',
	# 	'https://www.allrecipes.com/recipe/23109/rainbow-citrus-cake/',
	# 	'https://www.allrecipes.com/recipe/219910/homemade-cream-filled-sponge-cakes/',
	# 	'https://www.allrecipes.com/recipe/16700/salsa-chicken/?internalSource=hub%20recipe&referringId=1947&referringContentType=recipe%20hub',
	# 	'https://www.allrecipes.com/recipe/109190/smooth-sweet-tea/',
	# 	'https://www.allrecipes.com/recipe/220943/chef-johns-buttermilk-biscuits/',
	# 	'https://www.allrecipes.com/recipe/24501/tangy-honey-glazed-ham/?internalSource=hub%20recipe&referringId=15876&referringContentType=recipe%20hub',
	# 	'https://www.allrecipes.com/recipe/247204/red-split-lentils-masoor-dal/?internalSource=staff%20pick&referringId=233&referringContentType=recipe%20hub'
	# 	'https://www.allrecipes.com/recipe/233856/mauigirls-smoked-salmon-stuffed-pea-pods/?internalSource=staff%20pick&referringId=416&referringContentType=recipe%20hub',
	# 	'https://www.allrecipes.com/recipe/169305/sopapilla-cheesecake-pie/?internalSource=hub%20recipe&referringId=728&referringContentType=recipe%20hub',
	# 	'https://www.allrecipes.com/recipe/85389/gourmet-mushroom-risotto/?internalSource=hub%20recipe&referringId=723&referringContentType=recipe%20hub',
	# 	'https://www.allrecipes.com/recipe/138020/st-patricks-colcannon/?internalSource=staff%20pick&referringId=197&referringContentType=recipe%20hub',
	# 	'https://www.allrecipes.com/recipe/18241/candied-carrots/?internalSource=hub%20recipe&referringId=194&referringContentType=recipe%20hub',
	# 	'https://www.allrecipes.com/recipe/18870/roast-leg-of-lamb-with-rosemary/?internalSource=hub%20recipe&referringId=194&referringContentType=recipe%20hub',
	# 	'https://www.allrecipes.com/recipe/8270/sams-famous-carrot-cake/?internalSource=hub%20recipe&referringId=188&referringContentType=recipe%20hub',
	# 	'https://www.allrecipes.com/recipe/13717/grandmas-green-bean-casserole/?internalSource=hub%20recipe&referringId=188&referringContentType=recipe%20hub'

	# ]

	# for url in URLS:
	# 	recipe_attrs = parse_url(url)
	# 	recipe = Recipe(**recipe_attrs)
	# 	print(recipe.to_JSON())

	recipe_attrs = parse_url(URL)
	recipe = Recipe(**recipe_attrs)
	print(recipe.to_JSON())	
	# recipe.to_vegan()
	# recipe.from_vegan()

	# recipe.to_vegan()
	# recipe.from_vegan()
	# recipe.to_vegetarian()
	# recipe.from_vegetarian()
	# recipe.to_pescatarian()
	# recipe.from_pescatarian()
	# recipe.to_healthy()
	# recipe.from_healthy()
	# recipe.to_style('Thai')
	recipe.to_style('Mexican')
	# recipe.to_method('bake')
	# recipe.to_easy();
	print(recipe.to_JSON())
	print(recipe.compare_to_original())
	# recipe.to_method('fry')
	# # recipe.print_pretty()



#============================================================================
# Start webPy environment
#============================================================================


def main_gui(method, txtContent):
	#print(txtContent)
	
	# parse websites to build global lists -- used for Ingredient type tagging
	build_dynamic_lists()

	list_of_attribute = recipe_parser.build_synonyms()
            
	# Write to Synonym Json file
	with open('result/synonyms.json', 'r') as f:
		json_object = json.load(f)
		for i, key in enumerate(json_object):
			json_object[key] = list(list_of_attribute[i])

	with open('result/synonyms.json', 'w') as f:
		json.dump(json_object, f, indent=2)

	# make the line into a list  
	clean_text_lines = []
	for line in txtContent.splitlines():
		clean_line = recipe_parser.remove_non_ascii(line)
		clean_text_lines.append(clean_line.replace("\n", "").strip())   # remove newline character and space
	
	result = recipe_parser.set_division(clean_text_lines)

	with open('result/recipe_template.json') as f:
		data = json.load(f)
		data = recipe_parser.categorize(data,result,clean_text_lines)
		data = recipe_parser.join_string(data, "title")
		data = recipe_parser.join_string(data, "instruction")
		data = recipe_parser.join_string(data, "tips")
		data = recipe_parser.give_id(data)
		
	with open('result/recipe_file.json', 'w') as f:
		json.dump(data, f, indent=2)
		#print(data, '\n')
		#for key in data:
			#if key == "nutrient":
				#print(key, ":", data[key])
	
	recipe_parser.nutrient_formatter()

	# download json file here

	with open('result/recipe_file.json') as f:
		data = json.load(f)
		
		# get downloads path
		download_path = str(Path.home() / "Downloads")
		download_json_location = download_path + '/recipe_file.json'

		i = 1
		if os.path.exists(download_json_location):
			while i < MAXINT:
				if os.path.exists(download_path + '/recipe_file_'+str(i)+'.json'):
					i += 1
				else:
					download_json_location = download_path + '/recipe_file_'+str(i)+'.json'
					break

		# create json file and write json data into file
		with open(download_json_location, 'w') as e: 
			json.dump(data, e, indent=2)
		
		return data

	# URL = ""
	# recipe_attrs = parse_url(URL)

	# recipe = Recipe(**recipe_attrs)
	# s = ""
	# s += recipe.to_JSON()

	# if method == 'to_JSON':
	# 	recipe.to_JSON()
	# elif method == 'print_pretty':
	# 	recipe.print_pretty()
	
	# s += recipe.to_JSON() 
	# s += recipe.compare_to_original()

	# return s

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
	else:
		main()
