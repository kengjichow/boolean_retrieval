from nltk.stem.porter import PorterStemmer
from BooleanEval import *

def normalise_token(token):
    '''
    Uses the nltk PorterStemmer to stem the token and case folds token to lowercase.
    '''
    token = token.lower()
    stemmer = PorterStemmer()
    token = stemmer.stem(token)
    return token

def tokenise_query_to_list(string):
    '''
    Tokenises a boolean query from a string to a list, recognising the operators "AND", "OR", "NOT", "(" and ")"
    :param string: the query as a string
    :return: a list of operands and operators in a list (infix notation)
    '''
    string = string.split()
    list = []
    for word in string:
        if word in ["AND", "OR", "NOT", "(", ")"]:
            list.append(word)
        elif word[0] == "(" and word[-1] == ")":
            list.append("(")
            list.append(normalise_token(word[1:-1]))
            list.append(")")
        elif word[0] == "(":
            list.append("(")
            term = word[1:]
            if term in ["AND", "OR", "NOT"]:
                list.append(term)
            else:
                list.append(normalise_token(term))
        elif word[-1] == ")":
            term = word[:-1]
            if term in ["AND", "OR", "NOT"]:
                list.append(term)
            else:
                list.append(normalise_token(term))
            list.append(")")
        else:
            list.append(normalise_token(word))
    return list

def infix_to_postfix(infix_exp):
    '''
    Converts a infix expression to postfix expression using a modification of the Shunting-Yard algorithm
    In particular, a pair of adjacent "NOT"s is eliminated, "ANDNOT" followed by "NOT" is converted to "AND".
    Furthermore, X AND NOT Y is converted to X Y ANDNOT, and NOT X AND Y is converted to X Y NOTAND.
    :param infix_exp: A boolean query in infix notation
    :return: A boolean query in postfix notation, as a list
    '''
    stack = []
    postfix = []
    precedence_dict = {"AND": 2, "OR": 1, "NOT": 3, "ANDNOT": 2, "NOTAND" : 2}
    for term in infix_exp:
        if term == "(":
            stack.append(term)
        elif term == ")":
            while stack[-1] != "(":
                postfix.append(stack.pop())
            stack.pop()
        elif term in ["AND", "OR", "NOT"]:
            if term == "NOT" and stack:
                if stack[-1] == "NOT":
                    stack.pop()
                elif stack[-1] == "AND":
                    stack.pop()
                    term = "ANDNOT"
                elif stack[-1] == "ANDNOT":
                    stack.pop()
                    term = "AND"
            elif term == "AND" and stack:
                if stack[-1] == "NOT":
                    stack.pop()
                    term = "NOTAND"
            while (stack and stack[-1] != "(" and precedence_dict[term] <= precedence_dict[stack[-1]]):
                postfix.append(stack.pop())
            stack.append(term)
        else:
            postfix.append(term)
    while stack:
        postfix.append(stack.pop())
    return postfix

def evaluate_query(query, dictionary):
    '''
    Converts boolean query into a postfix expression, then uses a stack to evaluate the postfix expression.
    In order to do query optimisation such that in a sequence of terms that are related by OR or AND,
    for example X OR Y OR Z, or X AND Y AND Z, the term with the smaller postings list is merged first,
    I maintain an auxiliary op_stack and temp list. For example, in a postfix sequence X Y OR Z OR A AND, [X,Y,Z]
    will be accumulated in the stack while [OR, OR] will be in the op_stack. A will be inserted into a temp list,
    and then since AND is different from the operators in the op_stack, the op_stack will be clearly such that
    X Y OR Z OR is evaluated. (See Additional Details.pdf for detailed trace of various cases)

    :param query: original infix boolean query as a string
    :param dictionary: index dictionary with term frequency and pointers to postings lists
    :return: evaluated boolean query in a (freq, postings) tuple
    '''
    postfix_query = infix_to_postfix(tokenise_query_to_list(query))
    evaluator = BooleanEval(dictionary)
    stack = []
    op_stack = []
    temp = []
    operators = ["AND", "NOT", "OR", "ANDNOT", "NOTAND"]
    while postfix_query:
        term = postfix_query.pop(0)
        # if the operator differs from the operators in the op_stack or temp list has more than 1 item,
        # combine the accumulated terms, then transfer the items in the temp list to the stack
        if op_stack and term in operators:
            if op_stack[-1] == "OR" and (term > "OR" or len(temp) > 1):
                combine_ORs(stack, op_stack, evaluator)
            elif op_stack[-1] == "AND" and (term != "AND" or len(temp) != 1):
                combine_ANDS(stack, op_stack, evaluator)
            while temp:
                stack.append(temp.pop(0))
        if term == "NOT":
            stack.append(evaluator.NOT(stack.pop()))
        elif term in ["OR", "AND"]:
            # accumulate "AND" and "OR" operators in the op_stack until a different operator is found
            op_stack.append(term)
        elif term == "ANDNOT":
            # breaks up "ANDNOT", creating a NOT_element from the top element which is inserted back into the stack,
            # then pushes "AND" into the op_stack
            not_term = NOT_term(stack.pop())
            stack.append(not_term)
            op_stack.append("AND")
        elif term == "NOTAND":
            # breaks up "NOTAND", creating a NOT_element from the second last element,
            # then pushes "AND" into the op_stack
            # this is possible since NOTAND forces the operators in the op_stack to evaluate
            stack[-2] = NOT_term(stack[-2])
            op_stack.append("AND")
        else:
            if op_stack:
                temp.append(term)
            else:
                stack.append(term)
    # clear remaining operators in the op_stack
    if op_stack:
        if op_stack[-1] == "OR":
            combine_ORs(stack, op_stack, evaluator)
        elif op_stack[-1] == "AND":
            combine_ANDS(stack, op_stack, evaluator)
    # evaluate a single term query without operators
    if isinstance(stack[0], str):
        stack[0] = evaluator.eval_single_term(stack[0])
    result = stack[0][1]
    return result

def combine_ORs(stack, op_stack, evaluator):
    '''
    Evaluates the union of n+1 terms on the top of the stack if there are n "OR"s accumulated in the op_stack.
    :param stack: stores the operands
    :param op_stack: stores the accumulated "OR" operators
    :param evaluator: the BooleanEval object
    '''
    or_list = []
    while op_stack:
        or_list.append(stack.pop())
        op_stack.pop()
    or_list.append(stack.pop())
    result = evaluator.OR_lists(or_list)
    stack.append(result)

def combine_ANDS(stack, op_stack, evaluator):
    '''
    Evaluates the intersection of n+1 terms on the top of the stack if there are n "AND"s accumulated in the op_stack.
    Calls the eval.AND_and_ANDNOT_lists method to intersect positive and negative "NOT" terms, stored as NOT_terms.
    :param stack: stores the operands
    :param op_stack: stores the accumulated "AND" operators
    :param evaluator: the BooleanEval object
    '''
    and_list = []
    while op_stack:
        and_list.append(stack.pop())
        op_stack.pop()
    and_list.append(stack.pop())
    result = evaluator.AND_and_ANDNOT_lists(and_list)
    stack.append(result)