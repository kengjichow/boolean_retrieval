#!/usr/bin/python
import re
from nltk.stem.porter import PorterStemmer
from nltk.tokenize import sent_tokenize, word_tokenize
import sys
import getopt
import os
import io
import math

def usage():
    print("usage: " + sys.argv[0] + " -i directory-of-documents -d dictionary-file -p postings-file")

helper_postings_file = "helper_postings.txt"

def main():
    '''
    Creates the index. Firstly, the file names in the file directory are sorted.
    Next, a global postings list of all the documents are written to the start of the postings file.
    Then, we retrieve a list of all the terms in the documents. This is used to create helper
    dictionaries. The freq_dictionary stores the current number of documents for each term, and
    the pointer_dictionary stores the pointers to the end of each postings list in the helper postings file.

    The files are then split into batches for indexing. A helper postings file is written padded with '.' characters
    such that writing directly to a specific position is possible. Each batch of files is then processed,
    with additional postings appended to each postings list in the helper file in each iteration. This also
    updates the freq_dictionary and the pointer_dictionary as postings are appended.

    When all the postings have been written into the helper file, the postings in the helper file are processed
    and inserted with skip pointers before being written to postings.txt. The byte address of the start of
    each list is recorded in a dictionary together with the length of the postings list. This information is written
    to dictionary.txt.
    '''
    corpus_path = input_directory if input_directory[-1] == "/" else input_directory + "/"
    files = os.listdir(corpus_path)
    files.sort(key=lambda x: int(x))
    max_postings_line_length = print_all_docIDs(files)
    all_terms = get_all_terms(corpus_path, files)
    pointer_dictionary, line_to_term_dic = create_helper_dictionaries(all_terms, max_postings_line_length)

    file_batches = [files[i:i + 3000] for i in range(0, len(files), 3000)] # split into batches
    freq_dictionary = {}
    open(helper_postings_file, "w").close()
    file = open(helper_postings_file, 'r+')
    file.write("." * max_postings_line_length * len(all_terms)) # write helper file
    pointer_dictionary, freq_dictionary = process_file_batches(file_batches, corpus_path,
                                                               pointer_dictionary, freq_dictionary) # process batches

    # convert postings in helper file to postings.txt
    final_dictionary = convert_raw_postings(pointer_dictionary, line_to_term_dic, freq_dictionary)
    print_dictionary(final_dictionary) # print to dictionary.txt
    os.remove(helper_postings_file)

def normalise_token(token):
    '''
    Normalises tokens using the nltk PorterStemmer and case folds token to lowercase.
    '''
    token = token.lower()
    stemmer = PorterStemmer()
    token = stemmer.stem(token)
    return token

def get_all_terms(corpus_path, files):
    '''
    Returns a set of all unique terms in the whole collection.
    :param corpus_path: the path to the document collection
    :param files: a list of all document IDs
    '''
    all_terms = {}
    for fileID in files:
        file = corpus_path + fileID
        lines = io.open(file, mode="r", encoding="utf-8")
        file_lexicon = process_file_to_lexicon(lines)
        for word in file_lexicon:
            if word not in all_terms:
                all_terms[word] = 0
    return all_terms

def process_file_to_lexicon(file):
    '''
    Takes in a file and tokenises it into individual tokens using the nltk sent_tokenize and word_tokenize.
    Returns a set of unique tokens in the file (as a dictionary).
    '''
    text = file.read()
    lexicon = {}
    sentences = sent_tokenize(text)
    for sentence in sentences:
        words = word_tokenize(sentence)
        words = list(map(lambda x: normalise_token(x), words))
        for word in words:
            if word not in lexicon:
                lexicon[word] = 0
    return lexicon

def print_all_docIDs(all_files):
    '''
    Prints a postings list with skip pointers to the first line of the postings.txt file.
    :param all_files: A list of all the document IDs in the collection.
    :return: The length of the the string written to postings.txt.
    '''
    open(output_file_postings, 'w').close()
    postings_file = open(output_file_postings, 'a')
    string = insert_skip_pointers(all_files) + "\n"
    length = len(string)
    postings_file.write(string)
    return length

def create_helper_dictionaries(terms, length):
    '''
    Creates a pointer_dictionary which maps words to the start byte of each list in the helper file.
    The line_to_term_dic maps the line in the helper file to the term.
    :param terms: a list of all the unique terms in the collection
    :param length: the maximum length of each postings list in the helper file
    :return: pointer_dictionary and line_to_term_dic
    '''
    pointer_dictionary = {}
    line_to_term_dic = {}
    pointer = 0
    line_number = 0
    for term in terms:
        pointer_dictionary[term] = pointer
        pointer += length
        line_to_term_dic[line_number] = term
        line_number += 1
    return pointer_dictionary, line_to_term_dic

def process_file_batches(file_batches, corpus_path, pointer_dictionary, freq_dictionary):
    '''
    Takes in file batches and for each file batch, the files are processed into a sub_index which maps
    terms to a postings list for that file batch. The print_postings function is then called to
    append the postings lists in the sub_index into the helper postings file.
    :param file_batches: a list of list of document IDs, where each list is a file batch.
    :param corpus_path: the path to the collection.
    :param pointer_dictionary: a dictionary mapping terms to the end of each postings list in the helper file
    :param freq_dictionary: a dictionary mapping terms to their current frequency in the helper file
    :return: the updated pointer_dictionary and freq_dictionary
    '''
    for files in file_batches:
        sub_index = {}
        for fileID in files:
            file = corpus_path + fileID
            lines = io.open(file, mode="r", encoding="utf-8")
            file_lexicon = process_file_to_lexicon(lines)
            for word in file_lexicon:
                if word not in sub_index:
                    sub_index[word] = []
                sub_index[word].append(fileID)
        freq_dictionary, pointer_dictionary = print_postings(sub_index, pointer_dictionary, freq_dictionary)
    return pointer_dictionary, freq_dictionary

def print_postings(sub_index, pointer_dictionary, freq_dictionary):
    '''
    Writes the additional postings from the lexicon to the helper file.
    For each word, it uses the pointer_dictionary to find the byte address of the end of the
    postings list in the file and appends the additional postings directly to that address.
    The freq_dictionary is also updated with the number of additional postings appended.
    :param sub_index: A mapping from terms to postings from a subset of the document collection.
    :param pointer_dictionary: A dictionary mapping terms to the byte address of the end of each postings list.
    :param freq_dictionary: A dictionary mapping terms to the number of postings for that term.
    :return: the updated pointer_dictionary and freq_dictionary.
    '''
    file = open(helper_postings_file, 'r+')
    for word in sub_index:
        start_pointer = pointer_dictionary[word]
        file.seek(start_pointer)
        string = ","
        for docID in sub_index[word]:
            string += str(docID) + ","
        string = string[:-1]
        string_length = len(string)
        file.write(string)
        new_pointer = start_pointer + string_length
        pointer_dictionary[word] = new_pointer
        if word not in freq_dictionary:
            freq_dictionary[word] = 0
        freq_dictionary[word] += len(sub_index[word])
    return freq_dictionary, pointer_dictionary

def convert_raw_postings(pointer_dictionary, line_to_term_dic, freq_dictionary):
    '''
    Converts the helper file into the actual postings.txt file. Reads each postings list in the helper file,
    inserts skip pointers and writes the line to postings.txt. The start_byte of each postings list
    is also stored in the final_dictionary together with the frequency of each term.
    :param pointer_dictionary: A dictionary mapping terms to the byte address of the end of each postings list.
    :param line_to_term_dic: A dictionary mapping the line in the helper file to the term.
    :param freq_dictionary: A dictionary mapping each term to its frequency in the collection.
    :return: The final dictionary to be printed to dictionary.txt
    '''
    helper_file = open(helper_postings_file, 'r+')
    # end off each postings list with endline char
    for word in pointer_dictionary:
        helper_file.seek(pointer_dictionary[word])
        helper_file.write('\n')
    postings_file = open(output_file_postings, 'a')
    start_byte = postings_file.tell()
    final_dictionary = {}
    line_no = 0
    helper_file = open(helper_postings_file, 'r')
    for line in helper_file:
        postings = line.replace(".", "")
        if not postings or postings == "\n":
            continue
        postings = postings.split(",")[1:]
        postings[-1] = postings[-1][:-1]
        postings_list = insert_skip_pointers(postings) + '\n'
        postings_file.write(postings_list)
        word = line_to_term_dic[line_no]
        line_no += 1
        final_dictionary[word] = (freq_dictionary[word], start_byte)
        start_byte = postings_file.tell()
    return final_dictionary

def print_dictionary(dictionary):
    '''
    Writes the dictionary to the dictionary file. Each line has a term, the term frequency and
    the pointer to the beginning of the posting list, separated by a space.
    '''
    open(output_file_dictionary, "w").close()
    file = open(output_file_dictionary, 'a')
    for entry in dictionary:
        freq = dictionary[entry][0]
        value = dictionary[entry][1]
        file.write(str(entry) + " " + str(freq) + " " + str(value) + "\n")

def insert_skip_pointers(postings):
    '''
    Inserts skip pointers in the form of indices into a postings list with a skip distance
    of the root of the length of the list. Skip pointers are only inserted if the skip distance
    exceeds 2.
    :param postings: a list of postings as integers.
    :return: a list of postings as strings, including skip pointers.
    '''
    length = len(postings)
    skip_distance = int(math.sqrt(length))
    if skip_distance <= 2:
        return ",".join(postings)
    string = ""
    count = 0
    for posting in postings:
        string += posting
        if count % skip_distance == 0:
            skip_pointer = count + skip_distance
            if skip_pointer < length:
                string += "/" + str(skip_pointer)
        string += ","
        count += 1
    return string[:-1]

input_directory = output_file_dictionary = output_file_postings = None

try:
    opts, args = getopt.getopt(sys.argv[1:], 'i:d:p:')
except getopt.GetoptError as err:
    usage()
    sys.exit(2)
    
for o, a in opts:
    if o == '-i': # input directory
        input_directory = a
    elif o == '-d': # dictionary file
        output_file_dictionary = a
    elif o == '-p': # postings file
        output_file_postings = a
    else:
        assert False, "unhandled option"

if input_directory == None or output_file_postings == None or output_file_dictionary == None:
    usage()
    exit(2)

main()
