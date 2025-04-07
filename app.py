# app.py
from flask import Flask, request, jsonify
import json
import re
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from db_connector import get_db_connection
from collections import Counter
import re




app = Flask(__name__)

# In-memory storage for tasks (replace with a database for production use)
tasks = {}

def proccess_text(text):
    # Tokenize the text using nlt
    tokens = word_tokenize(text)
    
    # Set of stop words in English
    stop_words = set(stopwords.words('english'))

    # Filtering out stop words
    filtered_words = [word for word in tokens if word.lower() not in stop_words]
    
    # Original pattern for UUID followed by numbers
    uuid_pattern = r'\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}/\d+-\d+\b' 
    
    # Pattern for specific characters 
    chars_pattern = r'[%%/v<>.]'
    
    # Regular expression pattern to match the desired strings
    pattern = re.compile(f'{uuid_pattern}|{chars_pattern}')
    
    # Filter out the words that match the pattern
    filtered_words = [word for word in filtered_words if not pattern.match(word)]
    
    return filtered_words

def get_blacklist_data():
    
    # Open and read the JSON file with 
    with open('blacklist.json', 'r') as json_file: 
        data = json.load(json_file)
        return data

def clean_vtt_content(vtt_content):
    # A typical .vtt timestamp format is like "00:00:05.000 --> 00:00:10.000"
    lines = vtt_content.splitlines()
    cleaned_lines = []
    
    for line in lines:
        # Ignore lines that are timestamps or blank
        if re.match(r'\d{2}:\d{2}:\d{2}\.\d{3}', line) or line.strip() == '':
            continue
        # Ignore lines that are speaker labels if present
        if line.startswith("NOTE") or line.strip().isdigit():
            continue
        if line.startswith("WEBVTT"):
            continue
        # Add non-empty text lines to cleaned list
        line_removed_empty = re.sub(r'^\w+:\s*', '', line)
        #filter speaker tags  
        remove_speaker_starting_tag = re.sub(r"<v [^>]+>", "", line_removed_empty)
        # filter speaker end tags
        remove_speaker_ending_tag = re.sub(r'</?v>', '', remove_speaker_starting_tag)
        # remove special characters
        clean_all_special_char = re.sub(r'[^A-Za-z0-9 ]+', '', remove_speaker_ending_tag)
    
        cleaned_lines.append(clean_all_special_char)

    # Join the cleaned lines into a single text block
    cleaned_text = ' '.join(cleaned_lines)
    
    
    return cleaned_text

def find_words(text):
    
    # Tokenize the input text into words
    tagged_words = nltk.pos_tag(text)

    # Lists to collect the results
    subjects = []
    

    # Iterate through tagged words
    for word, tag in tagged_words:
       
        if tag.startswith('NN'):  # Noun (subject)
            subjects.append(word)
    return subjects
    

@app.route('/api/upload-vtt/', methods=['POST'])
def upload_vtt():
    print(request.files)
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    if file and file.filename.endswith('.vtt'):
        # Read file content
        vtt_content = file.read().decode('utf-8')
        # Clean the VTT content to get only the conversation text
        cleaned_text = clean_vtt_content(vtt_content)
        #remove stopwords and UUID and return tokenized words
        proccessed_text = proccess_text(cleaned_text)
        #find subjects in token words
        subject_words = find_words(proccessed_text)
        
        counter = Counter(subject_words) 
        
        # get black list data from database.
        DB_blacklist = get_blacklist_data()
        
        removed_blacklisted_words = check_matches(DB_blacklist, counter)
        most_common = removed_blacklisted_words.most_common(20) 
        return json.dumps(most_common)
    else:    
        return jsonify({'error': 'No selected file'}), 400




def check_matches(dictionary, counter): 
    words_to_remove = []
    #return dictionary
    for word in counter: 
        for item in dictionary:
            if isinstance(item, dict) and 'word' in item:
                if word.lower() == item['word'].lower(): 
                    words_to_remove.append(word)
    # Remove the matched words from the counter
    for word in words_to_remove:
        del counter[word] 
    return counter





if __name__ == '__main__':
    app.run(debug=True)
