import nltk
nltk.download('omw-1.4')
nltk.download('wordnet')
from nltk.corpus import wordnet
from nltk.tokenize import RegexpTokenizer
from nltk.corpus import stopwords
import spacy
from nltk import chunk,pos_tag
from spacy.lang.en import English
parser = English()
nlp = spacy.load("en_core_web_sm")
import json
import re
import zipfile


nlp = spacy.load("en_core_web_sm")


class RecipeParser():  
    
    def __init__(self) -> None:
        self.clean_text_lines = []
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

    # Remove unused synonyms from list of synonyms
    def clean_synonyms(self,synonym_list, unused_synonyms):
        for synonym in unused_synonyms:
            if synonym in synonym_list:
                synonym_list.remove(synonym)
        ret_list = []
        for synonym in synonym_list:
            ret_list.append(synonym.lower())
        return ret_list 

    # Text Cleaning

    # Remove non-ascii characters
    def remove_non_ascii(self,text):
        return re.sub('[^-*.A-Za-z0-9,! ]+', '', text)


    # Write to recipe json file

    def categorize(self,json_obj, result):
        # Variable to flag whether the title has been stored in recipe_file.json file or not
        title_done = False

        # If there's no serving amount   listed in recipe, use first few lines before first category's index as title 
        first_category_index = result[0][1] # Get the index of the first category
        if (first_category_index != 0):
            # Store title value in recipe_file.json file     
            json_obj["title"] = self.clean_text_lines[0: first_category_index]
            title_done = True

        # General formatting 
        for i, item in enumerate(result):
            key = item[0]
            index = item[1]
            if (key == "serving"):
                serving_arr = re.findall(r'\d+', self.clean_text_lines[index])
                
                if len(serving_arr) > 0:  # If serving size exists
                    serving = serving_arr[0]
                    next_item = result[i + 1]
                else:
                    serving = 0
                    next_item = result[i]
                json_obj[key] = serving

                # If title already stored in recipe_file.json file, do not do title formatting
                if not title_done:     
                    # Store title value in recipe_file.json file        
                    next_index = next_item[1]
                    json_obj["title"] = self.clean_text_lines[index + 1 : next_index]
                
            # When the last important category is reached, exclude page label and
            # append the remaining categories and their values 
            elif ((i + 1) >= len(result)):  
                last_index = len(self.clean_text_lines) - 3  # Exclude page label
                json_obj[key] = self.clean_text_lines[index + 1 : last_index]
            else:
                next_item = result[i + 1]
                next_index = next_item[1]
                json_obj[key] = self.clean_text_lines[index + 1 : next_index]
        return json_obj

    # Clear all non-relevant characters
    def clear_text(self,text):
        return re.sub('[^-.A-Za-z0-9*,! ]+', '', text)
    
    def format_steps(self,str_list):
        ret = []
        current = []
        for i in range(0, len(str_list)):
            string = str_list[i]
            if bool(re.match('^[\.a-zA-Z0-9,! ]*$', string[0])):
                current.append(string)
            else:
                step = " ".join(current)
                ret.append(self.clear_text(step.strip()))
                current = [string]
            if i == len(str_list) - 1:
                step = " ".join(current)
                ret.append(self.clear_text(step.strip()))
        if len(ret) > 0:
            ret.pop(0)
        return ret
    
   # Join strings in the same category
    def join_string(self,json_obj, key):
        # formatting title
        if key in json_obj:
            key_list = json_obj[key]
            if (key == "instruction") or (key == "tips") or (key == "ingredient"):
                json_obj[key] = self.format_steps(key_list)
            else:
                json_obj[key] = ' '.join(key_list)
        return json_obj
    
    def give_id(self,json_obj):
        # assign id for recipe
        json_obj['id'] = self.list_of_id.pop(0)
        return json_obj

    def nutrient_formatter(self, filenum):
        with open(f'recipe_file_{filenum}.json', 'r') as f:
            i = 0
            result = {}
            json_object = json.load(f)
            nutrient = json_object["nutrient"]
  
        # Loop through all different nutrients
            while i < len(nutrient):  
                searched_val = re.search(r"\d", nutrient[i])  # Search for a numeric value in each nutrient

                # If the element contains key and value (split and separate into key and value)
                if searched_val: 
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
                    # Fix issue where 0mg is read as Omg 
                    if "Omg" in nutrient[i]: 
                        split = nutrient[i].split(" ", 1)
                        key = split[0]
                        value = "0mg"
                        i += 1
                    else:
                        if (i >= len(nutrient)) or ((i + 1) >= len(nutrient)):
                            break # Break while loop if a word has been identified wrongly as a nutrient key
                        key = nutrient[i]
                        value = nutrient[i + 1]
                        i += 2
                result[key] = value               
            
            # Replace value of nutrient key with correctly formatted JSON 
            json_object["nutrient"] = result

        # Save updated json to recipe_file.json
        with open(f'recipe_file_{filenum}.json', 'w') as f:
            json.dump(json_object, f, indent=2)
            
    def parse_recipe(self, txtfilenames):
        # Get synonyms for attribute 
        cook_time_synonyms = self.get_synonyms('cook')
        serving_synonyms = self.get_synonyms('Serving')
        prep_time_synonyms = self.get_synonyms('Prep')
        ingredient_synonyms = self.get_synonyms('Ingredients')
        instruction_synonyms = self.get_synonyms('Method')
        tips_synonyms = self.get_synonyms('tips')
        nutrient_synonyms = self.get_synonyms('Nutrition')
        cuisine_synonyms = self.get_synonyms('Cuisine')
        category_synonyms = self.get_synonyms('Categories')
        
        # Remove some synonyms from wordnet 
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
        
        # Combine all synonyms in a single list
        list_of_attribute = [serving_synonyms, prep_time_synonyms, ingredient_synonyms, instruction_synonyms,
                            tips_synonyms, nutrient_synonyms, cuisine_synonyms, category_synonyms]
        
        # Write value stored in list_of_attribute to synonyms.json file

        with open('synonyms.json', 'r') as f:
            json_object = json.load(f)
            for i, key in enumerate(json_object):
                json_object[key] = list(list_of_attribute[i])

        with open('synonyms.json', 'w') as f:
            json.dump(json_object, f, indent=2)

        outputs_zip = zipfile.ZipFile("outputs.zip", "w")
        for i in range(len(txtfilenames)):
            txtfilename = txtfilenames[i]

            # open text file in read mode
            text_file = open(txtfilename, 'rb')
            text = text_file.read().decode(errors='replace')

            # close files
            text_file.close()

            # Make the lines into a list
            flag = True
            for line in text.splitlines():
                self.clean_text_lines.append(line.replace("\n", "").strip())   # remove newline character and space

            # Read synonyms and recipe template
            with open('synonyms.json', 'r') as f:
                syn_json_object = json.load(f)

            with open('recipe_template.json') as f:
                data = json.load(f)

            # Append the recipe template to recipe_file.json (output json file)
            with open(f'recipe_file_{i+1}.json', 'w') as f:
                json.dump(data, f, indent=2)

            # Read the updated recipe_file.json file
            with open(f'recipe_file_{i+1}.json', 'r') as f:
                recipe_json_object = json.load(f)

            # Carry out division
            result = []

            for index, line in enumerate(self.clean_text_lines):
                for key in syn_json_object:
                    # Division for Tips
                    if key == "tips" and key in line.lower():
                        result.append((key, index))
                    # Division for Serving, Ingredient, Instructions, Nutrients
                    else:
                        for attribute in syn_json_object[key]:
                            if (attribute in line.lower()) and (key in recipe_json_object) and (not recipe_json_object[key]):
                                result.append((key, index))
                                recipe_json_object[key] = True

            # Append categorized strings to their respective category keys
            # using the template in recipe_template.json
            with open('recipe_template.json') as f:
                data = json.load(f)
                data = self.categorize(data, result)
                data = self.join_string(data, "title")
                data = self.join_string(data, "ingredient")
                data = self.join_string(data, "instruction")
                data = self.join_string(data, "tips")
                data = self.give_id(data)

            # Save updated json to recipe_file.json
            with open(f'recipe_file_{i+1}.json', 'w') as f:
                json.dump(data, f, indent=2)

            self.nutrient_formatter(i+1)
            outputs_zip.write(f'recipe_file_{i+1}.json')

        outputs_zip.close()
