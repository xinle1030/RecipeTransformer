"""
Recipe Transformer Project

Given a URL to a recipe from AllRecipes.com, this program uses Natural Language Processing to transform any recipe, based on
user's input, into any or all of the following categories:  
	*   To and from vegetarian and/or vegan
	*   Style of cuisine
	*   To and from healthy (or perhaps even different types of healthy)
	*   DIY to easy
	*   Cooking method (from bake to stir fry, for example)


Authors: 
 	* David Wallach

"""
import re
import requests
from bs4 import BeautifulSoup

DEBUG = True

class Ingredient(object):
	"""
	Represents an Ingredient in the recipe. Ingredients have assoiciated quantities, names, measurements, 
	preperation methods (i.e. finley chopped), and descriptors (i.e. fresh, extra-virgin)
	"""
	def __init__(self, description):
		self.name = self.find_name(description)
		self.amount = self.find_amount(description)
		self.measurement = self.find_measurement(description)
		self.descriptors = self.find_descriptors(description)
		self.preperation = self.find_preperation(description)

		if DEBUG:
			print ('parsing ingredient: {}'.format(description))
			print ('name: {}'.format(self.name))
			print ('amount: {}'.format(self.amount))
			print ('measurement: {}'.format(self.measurement))
			print ('descriptors: {}'.format(self.descriptors))
		


	def find_name(self, description):
		"""
		looks for name of the ingredient from the desciption
		"""
		candidate = description.split(',')[0]
		name = candidate.split(' ')[-1]
		return name


	def find_amount(self, description):
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


	def find_measurement(self, description):
		"""
		looks for measurements such as cups, teaspoons, etc.
		"""
		words = description.split(' ')
		prev_numeric = False
		for word in words:
			numeric = re.search('[0-9]', word)
			if numeric:
				prev_numeric = True

			if not numeric and prev_numeric:
				return word

		return None

	def find_descriptors(self, description):
		"""
		looks for descriptions such as fresh, extra-virgin
		"""
		candidates = []
		candidate = description.split(',')
		if len(candidate) > 1:
			candidates.append(candidate[-1])

		prev_numeric = False
		idx = 0
		for i, word in enumerate(candidate[0].split(' ')):
			numeric = re.search('[0-9]', word)
			if numeric:
				prev_numeric = True

			if not numeric and prev_numeric:
				idx = i
				break
		if idx != 0:
			candidates.extend(candidate[0].split(' ')[idx+1:-1])
					
		return candidates




class Recipe(object):
	"""
	Used to represent a recipe. Data for each recipe can be found 
	on AllRecipes.com. 
	"""
	def __init__(self, **kwargs):
		for key, value in kwargs.items():
			setattr(self, key, value)

		self.ingredients = [Ingredient(ing) for ing in self.ingredients]	# store ingredients in Ingredient objects
	
	

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
		directions: list of strings
		calories: int
		carbs: int
		fat: int
		protien: int
		cholesterol: int
		sodium: int

	}
	"""

	# retrieve data from url
	result = requests.get(url)
	c = result.content

	# store in BeautifulSoup object to parse HTML DOM
	soup = BeautifulSoup(c, "lxml")


	# find name 
	name = soup.find('h1', {'itemprop': 'name'}).text
	
	# find relavent time information
	preptime  = remove_non_numerics(soup.find('time', {'itemprop': 'prepTime'}).text)
	cooktime  = remove_non_numerics(soup.find('time', {'itemprop': 'cookTime'}).text)
	totaltime = remove_non_numerics(soup.find('time', {'itemprop': 'totalTime'}).text)
	
	# find ingredients
	ingredients = [i.text for i in soup.find_all('span', {'class': 'recipe-ingred_txt added'})]

	# find directions
	directions = [i.text for i in soup.find_all('span', {'class': 'recipe-directions__list--item'})] 


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
		print ('it has {} directions'.format(len(directions)))
		print ('it has {} calories, {} g of carbs, {} g of fat, {} g of protien, {} mg of cholesterol, {} mg of sodium'.format(calories, carbs, fat, protien, cholesterol, sodium))


	return {
			'name': name,
			'preptime': preptime,
			'cooktime': cooktime,
			'totaltime': totaltime,
			'ingredients': ingredients,
			'directions': directions,
			'calories': calories,
			'carbs': carbs,
			'fat': fat,
			'protien': protien,
			'cholesterol': cholesterol,
			'sodium': sodium
			}


def user_input():
	"""
	Asks user what kind of transformations they would like to perform
	"""
	options = ['To vegetarian? (y/n) ', 'From vegetarian? (y/n) ', 'To healthy? (y/n) ', 'From healthy? (y/n) ']
	responses = []
	d = {'y': 1, 'n': 0}
	answered = False
	for opt in options:
		while not answered:
			try:
				ans = d[raw_input(opt)]
			except KeyError:
				continue
			else:
				answered = True
				responses.append(ans)
		answered = False
	return responses


def main():
	test_url = 'http://allrecipes.com/recipe/234667/chef-johns-creamy-mushroom-pasta/?internalSource=rotd&referringId=95&referringContentType=recipe%20hub'
	# test_url = 'http://allrecipes.com/recipe/21014/good-old-fashioned-pancakes/?internalSource=hub%20recipe&referringId=1&referringContentType=recipe%20hub'
	
	recipe_attrs = parse_url(test_url)
	recipe = Recipe(**recipe_attrs)

	# transformations = user_input()
	# print (transformations)


if __name__ == "__main__":
	main()



