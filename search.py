#!/usr/bin/python
import re
import sys
import getopt
from BooleanParser import evaluate_query

def usage():
    print("usage: " + sys.argv[0] + " -d dictionary-file -p postings-file -q file-of-queries -o output-file-of-results")

def main():
    '''
    Main function reads in the dictionary file into memory, then processes each query in the query file,
    writing the evaluated output to the output file line by line.
    '''
    dictionary = read_dictionary()
    file = open(file_of_queries, "r")
    open(output_file_of_results, "w").close()
    output = open(output_file_of_results, 'a')
    for line in file:
        query = line[:-1] if line[-1] == "\n" else line
        if query:
            try:
                postings = evaluate_query(query, dictionary)
            except:
                postings = []
            output.write(print_output(postings) + "\n")

def print_output(list):
    '''
    Converts a list into a string to be written to output.
    Also removes skip pointers from the output.
    '''
    string = ""
    for posting in list:
        docID = posting.split("/")[0]
        string += docID + " "
    return string[:-1]

def read_dictionary():
    '''
    Read the dictionary file into a dictionary mapping each term to a (frequency, term_pointer) tuple.
    '''
    dictionary = {}
    file = open(dictionary_file, "r")
    for line in file:
        line = line[:-1]
        entry = line.split()
        word = entry[0]
        freq = int(entry[1])
        pointer = int(entry[2])
        dictionary[word] = (freq, pointer)
    return dictionary

dictionary_file = postings_file = file_of_queries = output_file_of_results = None

try:
    opts, args = getopt.getopt(sys.argv[1:], 'd:p:q:o:')
except getopt.GetoptError as err:
    usage()
    sys.exit(2)

for o, a in opts:
    if o == '-d':
        dictionary_file = a
    elif o == '-p':
        postings_file = a
    elif o == '-q':
        file_of_queries = a
    elif o == '-o':
        output_file_of_results = a
    else:
        assert False, "unhandled option"

if dictionary_file == None or postings_file == None or file_of_queries == None or output_file_of_results == None:
    usage()
    sys.exit(2)

main()