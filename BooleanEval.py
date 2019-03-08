def get_docID(list, index):
    '''
    Takes in a list and an index and returns the document ID at that index.
    '''
    return int(list[index].split("/")[0])

def has_skip(list, index):
    '''
    Checks if there is a skip pointer in the postings list at that index.
    '''
    return "/" in list[index]

def get_skip_pointer(list, index):
    '''
    Returns the skip pointer associated with the given index on the list.
    '''
    return int(list[index].split("/")[1])

def get_skip_docID(list, index):
    '''
    Returns the document ID which the skip pointer specified at the given index points to.
    '''
    pointer = int(list[index].split("/")[1])
    return get_docID(list, pointer)

def insert_skip_pointers(postings_list):
    '''
    Inserts skip pointers into a postings list.
    :param postings_list: a list of postings in the form of strings.
    '''
    length = len(postings_list)
    skip_distance = int(length ** 0.5)
    if skip_distance <= 2:
        return postings_list
    new_list = []
    count = 0
    for posting in postings_list:
        if count % skip_distance == 0:
            skip_pointer = count + skip_distance
            if skip_pointer < length:
                new_list.append(posting + "/" + str(skip_pointer))
            else:
                new_list.append(posting)
        else:
            new_list.append(posting)
        count += 1
    return new_list

class NOT_term:
    '''
    A class that stores elements meant to be negated with NOT.
    '''
    def __init__(self, value):
        self.value = value

class BooleanEval:
    '''
    The BooleanEval class helps to evaluate boolean expressions.
    The methods may take in query terms or previously evaluated results, which are represented
    in the form of a (freq, postings list) tuple containing the length of the list to
    facilitate optimisation, and a list of postings.
    The results of merge are also inserted with skip pointers to allow for future merges.
    '''

    def __init__(self, dictionary):
        self.dictionary = dictionary

    def get_postings_list(self, word):
        '''
        Returns a (freq, postings list) tuple given a word as a query.
        :param word: a single query term as a string.
        '''
        postings = open("./postings.txt", "r")
        if word in self.dictionary:
            freq = self.dictionary[word][0]
            postings_pointer = self.dictionary[word][1]
            postings.seek(postings_pointer)
            posting_list = list(postings.readline().split(","))
        else:
            return (0, [])
        posting_list[-1] = posting_list[-1][:-1]
        return (freq, posting_list)

    def get_postings_lists(self, input):
        '''
        Takes in a list of input, which may contain either query terms or previously evaluated
        (freq, postings list) tuples, and retrieves the (freq, postings list) tuples for all the query terms.
        '''
        lists = []
        for item in input:
            if isinstance(item, str):
                lists.append(self.get_postings_list(item))
            else:
                lists.append(item)
        return lists

    def get_all_docIDs(self):
        '''
        Returns a list of all document IDs in the postings file.
        '''
        postings = open("./postings.txt", "r")
        postings.seek(0)
        posting_list = list(postings.readline().split(","))
        posting_list[-1] = posting_list[-1][:-1]
        return posting_list

    def eval_single_term(self, term):
        '''
        Returns a (freq, postings list) tuple for a single query term e.g. "the".
        :param term: A single query term
        :return: A (freq, postings list) tuple
        '''
        postings = self.get_postings_list(term)[1]
        result = []
        for index in range(len(postings)):
            result.append(str(get_docID(postings, index)))
        return (len(result), result)

    def OR_lists(self, terms):
        '''
        Returns a (freq, postings list) tuple that represents the disjunction/union of 2 or more search terms.
        :param terms: A list containing either search terms or already computed (freq, postings list) tuples.
        :return: A (freq, postings list) tuple
        '''
        lists = self.get_postings_lists(terms)
        lists.sort(key=lambda x: x[0])
        lists = list(map(lambda x: x[1], lists))
        while len(lists) > 1:
            new_list = self.OR(lists[0], lists[1])
            lists.pop(0)
            lists.pop(0)
            lists = [new_list] + lists
        result = insert_skip_pointers(lists[0])
        result = (len(result), result)
        return result

    def OR(self, listA, listB):
        '''
        Returns the union of listA and listB, both of which are postings lists.
        '''
        result = []
        i, j = 0, 0
        lengthA = len(listA)
        lengthB = len(listB)
        while i < lengthA and j < lengthB:
            docID_A = get_docID(listA, i)
            docID_B = get_docID(listB, j)
            if docID_A == docID_B:
                result.append(str(docID_A))
                i += 1
                j += 1
            elif docID_A < docID_B:
                result.append(str(docID_A))
                i += 1
            elif docID_A > docID_B:
                result.append(str(docID_B))
                j += 1
        while i < lengthA:
            result.append(str(get_docID(listA, i)))
            i += 1
        while j < lengthB:
            result.append(str(get_docID(listB, j)))
            j += 1
        return result

    def AND_and_ANDNOT_lists(self, terms):
        '''
        Returns the intersection of either positive or negative search terms e.g. A AND B AND C AND NOT D.
        The elements in terms may be query terms or (freq, postings list) tuples.
        Positive terms are placed in positive_posting_lists and negative terms are placed in negative_posting_lists.
        Positive terms are intersected first, and the resulting intersection is intersected with the complement
        of the postings lists in negative_posting_lists. This ensures that reordering of an expression with both
        AND and AND NOT does not influence the final result.
        For example, A AND B AND NOT C AND D can be evaluated as (A AND B AND D) AND NOT C. Evaluating in another order,
        e.g. ((A AND B) AND NOT C) AND D, would be incorrect.
        The terms are sorted by length of the postings list so that the shorter lists are merged first.
        :return: A (freq, postings list) tuple
        '''
        negative_list = []
        positive_list = []
        for item in terms:
            if isinstance(item, NOT_term):
                negative_list.append(item.value)
            else:
                positive_list.append(item)
        positive_posting_lists = self.get_postings_lists(positive_list)
        positive_posting_lists.sort(key=lambda x: x[0]) # sort by length
        negative_posting_lists = self.get_postings_lists(negative_list)
        negative_posting_lists.sort(key=lambda x: x[0]) # sort by length
        intersection = self.AND_lists(positive_posting_lists)
        intersection = intersection[1]
        negative_posting_lists = list(map(lambda x: x[1], negative_posting_lists))
        while negative_posting_lists:
            intersection = self.ANDNOT(intersection, negative_posting_lists.pop(0))
        intersection = insert_skip_pointers(intersection)
        return (len(intersection), intersection)

    def AND_lists(self, lists):
        '''
        Returns a (freq, postings list) tuple that represents the intersection of 2 or more search terms.
        :param lists: A list containing (freq, postings list) tuples.
        '''
        lists = list(map(lambda x: x[1], lists))
        while len(lists) > 1:
            new_list = self.AND(lists[0], lists[1])
            lists.pop(0)
            lists.pop(0)
            lists = [new_list] + lists
        result = insert_skip_pointers(lists[0])
        result = (len(result), result)
        return result

    def AND(self, listA, listB):
        '''
        Returns the intersection of listA and listB, both of which are postings lists.
        '''
        result = []
        i, j = 0, 0
        while i < len(listA) and j < len(listB):
            docID_A = get_docID(listA, i)
            docID_B = get_docID(listB, j)
            if docID_A == docID_B:
                result.append(str(docID_A))
                i += 1
                j += 1
            elif docID_A < docID_B:
                if has_skip(listA, i) and get_skip_docID(listA, i) <= docID_B:
                    while has_skip(listA, i) and get_skip_docID(listA, i) <= docID_B:
                        i = get_skip_pointer(listA, i)
                else:
                    i += 1
            elif docID_A > docID_B:
                if has_skip(listB, j) and get_skip_docID(listB, j) <= docID_A:
                    while has_skip(listB, j) and get_skip_docID(listB, j) <= docID_A:
                        j = get_skip_pointer(listB, j)
                else:
                    j += 1
        return result

    def NOT(self, term):
        '''
        Returns a (freq, postings list) tuple of all the document IDs that are not in the postings list of term.
        :param term: A (freq, postings list) tuple
        '''
        if isinstance(term, str):
            posting_list = self.get_postings_list(term)
        else:
            posting_list = term
        all = self.get_all_docIDs()
        result = self.ANDNOT(all, posting_list[1])
        result = insert_skip_pointers(result)
        return (len(result), result)

    def ANDNOT(self, listA, listB):
        '''
        Returns a list of all document IDs which are in listA but not in listB.
        '''
        result = []
        i, j = 0, 0
        while i < len(listA) and j < len(listB):
            docID_A = get_docID(listA, i)
            docID_B = get_docID(listB, j)
            if docID_A == docID_B:
                i += 1
                j += 1
            elif docID_A < docID_B:
                result.append(str(docID_A))
                i += 1
            elif docID_A > docID_B:
                if has_skip(listB, j) and get_skip_docID(listB, j) <= docID_A:
                    while has_skip(listB, j) and get_skip_docID(listB, j) <= docID_A:
                        j = get_skip_pointer(listB, j)
                else:
                    j += 1
        while i < len(listA):
            result.append(str(get_docID(listA, i)))
            i += 1
        return result
