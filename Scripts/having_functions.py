
# Libraries

from nltk import pos_tag, RegexpParser


def get_number_chunk(input_text):
    """
    Function to get numbers from the input text using chunk parser
    :param input_text: Input text given by user
    :return: identified numbers in list, number positions in list
    """

    # remove commas from text
    input_text = " ".join(input_text.replace(",", "").split())
    text = input_text
    # regex pattern to get the numbers
    grammar = "NP: {<CD>+<CC|TO>?<CD>?}"
    chunk_parser = RegexpParser(grammar)
    tree = chunk_parser.parse(pos_tag(input_text.split()))

    num_list, num_posi, num_list_2 = [], [], []
    for subtree in tree.subtrees(filter=lambda t: t.label() == 'NP'):
        word = " ".join([a for (a, b) in subtree.leaves()])
        pos = text.find(word)
        # get the position of word from text
        if pos < 1:
            pos = len(text)
        # masking the identified numbers
        text = text[:pos] + ("*" * len(word)) + text[pos + len(word):]
        num_list_2.append(word)
        num_posi.append(pos)
        # remove the conjunction words from chunks and append the number in list
        num_list.append(" ".join([num for num in word.split() if num not in ['and', 'to']]))

    return num_list, num_posi, num_list_2, text


def get_in(num, agg, ent):
    """
    Function to make NLU for "in" based number filters

    :param num: number or numbers
    :param agg: column which will be used for aggregation (average of sales)
    :param ent: entity (in or not in)
    :return: Condition to make sql query
    """

    if ent.text == 'not in':
        cond = 'filter ' + '_'.join(agg.split()) + ' not in ' + ','.join(num.split())
    else:
        cond = 'filter ' + '_'.join(agg.split()) + ' in ' + ','.join(num.split())
    return cond


def get_btwn(num, agg, ent):
    """
    Function to make NLU for "in" and "between" based number filters

    :param num: number or numbers
    :param agg: column which will be used for aggregation (average of sales)
    :param ent: entity (in or not in or between)
    :return: Condition to make sql query
    """

    if ent.text in ['in', 'following']:
        cond = 'filter ' + '_'.join(agg.split()) + ' in ' + ','.join(num.split())
    elif ent.text == 'not in':
        cond = 'filter ' + '_'.join(agg.split()) + ' not in ' + ','.join(num.split())
    else:
        cond = '_'.join(agg.split()) + ' between ' + ' and '.join(num.split())
    return cond


def get_op(num, agg, ent, term_df):
    """
    Function to make NLU for operator based number filters (>=, <=)

    :param num: number or numbers
    :param agg: column which will be used for aggregation (average of sales)
    :param ent: entity (in or not in)
    :param term_df: Terms data frame which contains all the key words and corresponding functionalities (greater than)
    :return: Condition to make sql query
    """

    func = term_df[term_df['terms'] == ent.text]['functions'].iloc[0]
    if func == 'in':
        cond = 'filter ' + '_'.join(agg.split()) + ' in ' + num
    else:
        cond = '_'.join(agg.split()) + ' ' + func + ' ' + num
    return cond


def agg_nlt_to_agg_query(string):
    """
    Function to convert Aggregation NLU to SQL query

    :param string: Aggregation NLU (Average of sales)
    :return: Aggregation query (avg(sales)
    """

    str_split = string.split()

    aggregation_query = ''
    col_name = '_'.join([str(i) for i in str_split[2:]])

    if str_split[0] in ['minimum', 'maximum', 'sum']:
        aggregation_query = str_split[0][:3] + "(" + col_name + ")"

    elif 'distinct count' in string:
        aggregation_query = 'count (distinct ' + col_name + ")"

    elif str_split[0] in ['count', 'distinct']:
        aggregation_query = str_split[0] + "(" + col_name + ")"

    elif 'average' in string:
        aggregation_query = 'avg' + "(" + col_name + ")"

    return aggregation_query


def get_h_cond(condition):
    """
    Main function to generate SQL query from NLU

    :param condition: NLU for having contions
    :return: SQL query for having filter
    """

    h_condition = []
    for h_cond in condition:
        # Split the nlu
        split_nlu_list = h_cond.split()

        if split_nlu_list[1] in ['at', 'not']:
            agg = split_nlu_list[0].replace('_', ' ')
            ag_str = agg_nlt_to_agg_query(agg)
            # when filter like average of sales greater than 100
            if split_nlu_list[2] == 'least':
                qry = ag_str + " >= '" + split_nlu_list[-1] + "'"
            # when filter like average of sales less than 100
            elif split_nlu_list[2] == 'most':
                qry = ag_str + " <= '" + split_nlu_list[-1] + "'"
            # when filter like average of sales is not 100
            else:
                qry = ag_str + " not in ('" + split_nlu_list[-1] + "')"

        elif split_nlu_list[0] == 'filter':
            agg = split_nlu_list[1].replace('_', ' ')
            ag_str = agg_nlt_to_agg_query(agg)
            # when filter like average of sales in (100, 200)
            if split_nlu_list[2] == 'in':
                numbers = ','.join(["'" + i + "'" for i in split_nlu_list[-1].split(',')])
                qry = ag_str + " in (" + numbers + ")"
            else:
                # when filter like average of sales not in (100, 200)
                numbers = ','.join(["'" + i + "'" for i in split_nlu_list[-1].split(',')])
                qry = ag_str + " not in (" + numbers + ")"
        else:
            agg = split_nlu_list[0].replace('_', ' ')
            ag_str = agg_nlt_to_agg_query(agg)
            # when filter like average of sales between 100 and 200
            numbers = ' and '.join(["'" + i + "'" for i in [split_nlu_list[-3], split_nlu_list[-1]]])
            qry = ag_str + " between " + numbers

        h_condition.append(qry)

    return h_condition


def get_having(agg_list, end_loc, nlu_ents, term_df, text_1):
    """
    Main function to identify numbers from text and creates aggregation NLu and generate SQl query from the NLUs

    :param agg_list: Aggregation NLU (average of sales)
    :param end_loc: end location of aggregation NLU in text
    :param nlu_ents: Entity list
    :param term_df: keyword data frame
    :param text: Input text
    :return: Aggregation NLU list, input text, having filter and entity list
    """

    text_2 = text_1
    # Get the number chunks from the text
    num_list_1, num_posi, num_list_2, _ = get_number_chunk(text_1)
    # Get the relevant entities
    nlu_2 = [i for i in nlu_ents if i.label_ in ['num_filter_1', 'num_filter_2']]
    # Initialize the requires lists
    condition, rm_num, rm_po, ag_loc = [], [], [], []
    # Loop the numbers and its position in reverse order
    for num, pos, num_2 in zip(num_list_1, num_posi, num_list_2):
        # number to break the loop
        number = 0
        for ent in nlu_2:
            if (ent.end_char < pos) & ((pos - ent.end_char) <= 3):

                for end, agg in zip(end_loc, agg_list):
                    if (end < ent.start_char) & ((ent.start_char - end) <= 6):
                        cnt = num.split()
                        # conditions like > or <
                        if len(cnt) == 1:
                            cond = get_op(num, agg, ent, term_df)
                            condition.append(cond)
                        # conditions like between 10 and 20
                        elif len(cnt) == 2:
                            cond = get_btwn(num, agg, ent)
                            condition.append(cond)
                        # conditions like sales in (10,20,30)
                        else:
                            cond = get_in(num, agg, ent)
                            condition.append(cond)
                        # Append the end location of NLU in list
                        ag_loc.append(end_loc.index(end))
                        nlu_ents.remove(ent), rm_num.append(num_2), rm_po.append(pos)
                        number = 1
                        break

            if number == 1:
                break
    # Check for masking identified numbers from the text
    if len(rm_num) > 0:
        for num, pos in zip(rm_num, rm_po):
            pos2 = pos + len(num)
            text_2 = text_2[:pos] + ('*' * len(num)) + text_2[pos2:]
        # Get the Query for NLUs
        h_cond = get_h_cond(condition)
        # Join the queries
        h_cond = ' and '.join(h_cond)
        # Remove the used aggregations from the aggregation list
        agg_list = [x for n, x in enumerate(agg_list) if n not in ag_loc]
    else:
        h_cond = ''

    condition = [nlu.replace('_',' ') for nlu in condition]

    return text_2, nlu_ents, h_cond, condition, agg_list
