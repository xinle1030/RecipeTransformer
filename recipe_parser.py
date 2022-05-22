import re
import json

# from urlparse import urlparse
from urllib.parse import urlparse
from collections import defaultdict, OrderedDict
from operator import itemgetter
from bs4 import BeautifulSoup

import nltk
from nltk import word_tokenize, pos_tag
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

class RecipeParser():  
    
    def __init__(self) -> None:
        list_of_id = []
        for i in range(1,10000):    
            id_name = 'AllHealthHub-' + '{0:05}'.format(i)
            list_of_id.append(id_name)
        self.list_of_id = list_of_id
      

    # Get Synonyms for attribute fucntion 
    def get_synonyms(self,word: str):
        synonyms = []
        for syn in wordnet.synsets(word):
            for i in syn.lemmas():
                synonyms.append(i.name())
        synonyms.append(word)
        return set(synonyms) 

    def clean_synonyms(self,synonym_list, unused_synonyms):
        for synonym in unused_synonyms:
            if synonym in synonym_list:
                synonym_list.remove(synonym)
        ret_list = []
        for synonym in synonym_list:
            ret_list.append(synonym.lower())
        return ret_list

    def build_synonyms(self):
        # get synonyms for attribute 
        cook_time_synonyms = self.get_synonyms('cook')
        serving_synonyms = self.get_synonyms('Serving')
        prep_time_synonyms = self.get_synonyms('Prep')
        ingredient_synonyms = self.get_synonyms('Ingredients')
        instruction_synonyms = self.get_synonyms('Method')
        tips_synonyms = self.get_synonyms('tips')
        nutrient_synonyms = self.get_synonyms('Nutrition')
        cuisine_synonyms = self.get_synonyms('Cuisine')
        category_synonyms = self.get_synonyms('Categories')

        # remove some synonyms from wordnet 
        cook_time_synonyms = self.clean_synonyms(cook_time_synonyms, ['James_Cook', 'Captain_Cook', 'Captain_James_Cook', 'wangle', 'ready', 'falsify', 'make', 'Cook', 'prepare', 'misrepresent', 'fake', 'manipulate', 'fix', 'fudge'])
        serving_synonyms = self.clean_synonyms(serving_synonyms, ['attend_to', 'suffice', 'dish_out', 'portion', 'helping', 'function', 'wait_on', 'answer', 'swear_out', 'attend', 'do', 'help', 'process', 'serving', 'dish'])
        serving_synonyms.append("serves")
        prep_time_synonyms = self.clean_synonyms(prep_time_synonyms, ['homework'])
        ingredient_synonyms = self.clean_synonyms(ingredient_synonyms, ['fixings'])
        instruction_synonyms = self.clean_synonyms(instruction_synonyms, ['method_acting'])
        tips_synonyms = self.clean_synonyms(tips_synonyms, ['tippytoe', 'gratuity', 'lead', 'bakshish', 'steer', 'lean', 'summit', 'crest', 'backsheesh', 'tiptoe', 'baksheesh', 'confidential_information', 'hint', 'angle', 'slant', 'topple', 'tumble', 'top', 'wind', 'bakshis', 'crown', 'fee', 'tap', 'tip_off', 'tilt', 'bung', 'pourboire'])
        nutrient_synonyms = self.clean_synonyms(nutrient_synonyms, ['victuals'])
        cuisine_synonyms = self.clean_synonyms(cuisine_synonyms, [])
        category_synonyms = self.clean_synonyms(category_synonyms, [])

        # remove cook time first
        list_of_attribute = [serving_synonyms, prep_time_synonyms, ingredient_synonyms, instruction_synonyms,
                            tips_synonyms, nutrient_synonyms, cuisine_synonyms, category_synonyms]
        
        return list_of_attribute

    # Text Cleaning

    def remove_non_ascii(self,text):
        string_encode = text.encode("ascii", "ignore")  
        string_decode = string_encode.decode()
        return string_decode


    def set_division(self,clean_text_lines):
        with open('result/synonyms.json', 'r') as f:
            syn_json_object = json.load(f)

        with open('result/recipe_template.json') as f:
            data = json.load(f)

        with open('result/recipe_file.json', 'w') as f:
            json.dump(data, f, indent=2)

        with open('result/recipe_file.json', 'r') as f:
            recipe_json_object = json.load(f)

        result = []

        for index, line in enumerate(clean_text_lines):
            for key in syn_json_object:
                # Division for Tips
                if key == "tips":
                    if key in line.lower():
                        result.append((key, index))
                # Division for Serving, Ingredient, Instructions, Nutrients
                else:
                    for attribute in syn_json_object[key]:
                        if attribute in line.lower() and key in recipe_json_object and not recipe_json_object[key]:
                            result.append((key, index))
                            recipe_json_object[key] = True
        return result

    # Write to recipe json file

    def categorize(self,json_obj, result, clean_text_lines):
        # general formatting 
        for i, item in enumerate(result):
            key = item[0]
            index = item[1]
            if key == "serving":
                serving = (re.findall(r'\d+', clean_text_lines[index]))[0]
                json_obj[key] = serving
                # title formatting
                next_item = result[i + 1]
                next_index = next_item[1]
                json_obj["title"] = clean_text_lines[index + 1 : next_index]
            elif key == "nutrient":
                last_index = len(clean_text_lines) - 3  # to exclude page label
                json_obj[key] = clean_text_lines[index + 1 : last_index]
            else:
                next_item = result[i + 1]
                next_index = next_item[1]
                json_obj[key] = clean_text_lines[index + 1 : next_index]
        return json_obj

    def join_string(self,json_obj, key):
        # formatting title
        key_list = json_obj[key]
        json_obj[key] = ' '.join(key_list)
        return json_obj
    
    def give_id(self,json_obj):
        # assign id for recipe
        json_obj['id'] = self.list_of_id.pop(0)
        return json_obj

    def nutrient_formatter(self):
    # Format nutrients element into properly formatted JSON object
        with open('result/recipe_file.json', 'r') as f:
            i = 0
            result = {}
            json_object = json.load(f)
            nutrient = json_object["nutrient"]
            
            #print(nutrient, '\n')
            while i < len(nutrient):
                searched_val = re.search(r"\d", nutrient[i])

                if searched_val: # element contains key and value (split and separate into key and value)
                    index_firstnum = searched_val.start()
                    if index_firstnum != 0: # both key and value
                        key = nutrient[i][0:(index_firstnum-1)].strip() 
                        value = nutrient[i][index_firstnum:len(nutrient[i])].strip()
                        
                        # Fix when bracket is in value instead of key
                        if key[len(key)-1] == "(":
                            key = key[:len(key)]
                            right_brack_index = value.find(")")
                            key = key + value[:right_brack_index+1]
                            value = value[right_brack_index+1:len(value)].strip()
                        i += 1
                        
                else: # only key (make into key)
                    if "Omg" in nutrient[i]: # Fixed issue where 0mg is read as Omg 
                        split = nutrient[i].split(" ", 1)
                        key = split[0]
                        value = split[1]
                        i += 1
                    else:
                        key = nutrient[i]
                        value = nutrient[i + 1]
                        i += 2
                result[key] = value               
            
            # Replace value of nutrient key with correctly formatted JSON 
            json_object["nutrient"] = result

        with open('result/recipe_file.json', 'w') as f:
            json.dump(json_object, f)
            
    

