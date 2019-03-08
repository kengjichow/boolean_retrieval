= Indexing stage =

index.py writes a dictionary and postings file from the files in the corpus. The indexing is done in
batches of 3000 files. In fact, an index of the entire collection can be read into memory and this is more
efficient, but for purposes of demonstration, the indexing is separated into batches. Firstly, the files
in the file directory are sorted by their document ID (file names). Then, a global postings list of all
the documents are written to the start of the postings file. Then, a set of all the unique terms in the
collection is found. This is done first to facilitate the preparation of a helper postings file which will be
populated with '.' so that it is possible to write directly to a specific byte address. The helper file
contains (in theory) n lines of length m, where n is the number of unique terms and m is the maximum length
of the postings list, which is found from the postings list of all the documents. A pointer dictionary used to
keep track of the byte address of the end of each postings list of each term is also created with the
address initialised to the start of each list.

The files are then separated into batches for indexing, which are still sorted. Each document is processed using
nltk tokenisers and the terms are stemmed using the Porter stemmer. Each batch is processed into a sub-index,
which is written directly to the helper postings file. The postings of each term in the sub-index is appended
directly to the end of the postings list in the helper postings file using the pointer dictionary, which is
updated after every inserted. At the end of the indexing of all the batches, the postings lists in
the helper file are processed and inserted with skip pointers before being written to postings.txt.
Skip pointers are direct indices representing the index of posting it points to the list.
After printing postings.txt, the byte offset and length of each list is stored in a dictionary which is
written out to dictionary.txt, where each line contains a term, the term frequency and the byte offset
which is a pointer to the posting list in posting.txt.

(General note: the submitted postings.txt and dictionary.txt was generated on tembusu. The output is
slightly different on a Windows machine)

= Query processing stage =

search.py reads in the dictionary into memory and evaluates each query in the queries file
line by line. Each query is parsed into a list by tokenise_query_to_list and converted into a
postfix expression using the Shunting Yard algorithm by infix_to_postfix. The algorithm but
modified in order to eliminate adjacent NOTs and collapse AND NOT into ANDNOT for optimisation purposes.
For example, NOT NOT X becomes X, X AND NOT Y becomes X Y ANDNOT, and NOT X AND Y becomes X NOTAND Y.

Then, the evaluate_query function uses a stack to evaluate the postfix expression, but an auxiliary stack is
also used to accumulate terms evaluated with the same operator. For example, a query X OR Y OR Z
should be evaluated together such that optimisation can be done whereby the terms with smaller
posting lists are merged first. In processing a postfix sequence ANDNOT operator,
the negated "NOT" term is wrapped into a NOT_term class, and ANDNOT is replaced by AND.
A detailed trace of examples of this algorithm with explanations can be found in Additional Details.pdf, which
also explains how a postfix sequence X Y ANDNOT Z AND is handled.

The BooleanEval class merges terms, supporting AND, OR, NOT and ANDNOT operations.
The OR_lists and AND_and_ANDNOT_lists methods help to merge sequences involving the same operator in
an optimal sequence based on the length of the posting lists. When a sequence such as X AND NOT Y AND Z AND W
is to be merged, the positive terms X, Z and W are first intersected, followed by the negative term Y.
When there are more than two positive terms, choosing the shortest lists to be merged first is more efficient.

The individual query terms are used to retrieve a (frequency, postings_list)
tuple from the postings file, following which the intermediate results of merging are
also stored in such a tuple. This is to facilitate the ordering of the posting lists by size.
The postings lists are stored as lists, where each term is either a document ID string,
or a docID/skip_pointer string, where the skip pointer is the index of the document ID it points to
in the list. For example, the posting 13/4 represents the document ID 13 and a skip pointer to
the fifth element (zero-based index) in the list. Skip pointers are also inserted into the intermediate
result of merges to facilitate future merges.

= Experiments =

1. I experimented with reading in the postings list byte by byte and implementing skip pointers as
byte addresses, but this was significantly less efficient than reading in the entire postings list for a
single term into memory due to the numerous calls to read(). Hence, I decided on simply storing
each node as a docID(/skip_pointer) string, where the skip pointer is a direct index of the
element in the list, as this bare data structure, although less elegant, proved to be the most efficient.
2. I experimented with using a tree to evaluate the expression after creating the postfix
expression, which would allow for grouping of terms and reordering more elegantly. However,
this was also less efficient, possibly because of the use of recursion and the creation of node objects.
3. I also initially created a wrapper list class to keep track of the current index of each list while
performing merge operations, but this also incurred costs on efficiency.