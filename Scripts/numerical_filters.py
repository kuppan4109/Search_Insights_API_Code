
# Libraries

from nltk import pos_tag, RegexpParser


# Get all the numbers and its positions from the input text

def find_numbers(input_text):
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

    num_list, num_posi, num_wrd = [], [], []
    for subtree in tree.subtrees(filter=lambda t: t.label() == 'NP'):
        word = " ".join([a for (a, b) in subtree.leaves()])
        pos = text.find(word)
        if pos < 1:
            pos = len(text)
        num_posi.append(pos)
        num_wrd.append(num_wrd)
        # text = text[:pos] + ("*" * len(word)) + text[pos + len(word):]  # masking the identified numbers

        num_list.append(" ".join([num for num in word.split() if num not in ['and', 'to']]))

    return num_list, num_posi, num_wrd, text


# This function used to find number filters (BETWEEN) in the input text

def find_between(nlu_ents, num, pos, cols, start, end, cols_list):
    # Separate condition/Filter entities
    con_ents = [ent for ent in nlu_ents if
                (ent.label_ in ['num_filter_1', 'num_filter_2']) & (ent.text in ['in', 'not', 'not in'])]
    filters = []

    if len(con_ents) > 0:
        # loop the columns and it positions in reverse
        for col, st, ed, n2 in zip(cols[::-1], start[::-1], end[::-1], range(len(cols))[::-1]):
            if ed < pos:
                for c_ent in con_ents[::-1]:
                    cut = len(col)+5 if c_ent.text == 'following' else 5
                    if (c_ent.start_char < pos) & ((pos - c_ent.end_char) <= cut):
                        txt = 'not in' if c_ent.text == 'not' else c_ent.text
                        x = "filter " + col + ' ' + txt + ' ' + ','.join(num.split())
                        break
                    else:
                        x = col + " between " + num
                n1 = cols_list[1].index(st)
                cols_list[0].pop(n1), cols_list[1].pop(n1), cols_list[2].pop(n1)
                cols.pop(n2), start.pop(n2), end.pop(n2)  # remove identified columns
                filters.append(x)
                break
    else:
        for col, st, ed, n2 in zip(cols[::-1], start[::-1], end[::-1], range(len(cols))[::-1]):
            if st < pos:
                x = col + " between " + num
                n1 = cols_list[1].index(st)
                cols_list[0].pop(n1), cols_list[1].pop(n1), cols_list[2].pop(n1)
                cols.pop(n2), start.pop(n2), end.pop(n2)
                filters.append(x)
                break
    return filters


# function to remove identified columns and entities

def getnlu_rm_cols(term_df, col, cols, start, end, nlu_ents, num_condition, ed, c_ent, num, attri_ents):
    col_func = term_df[term_df['terms'] == c_ent.text]['functions'].iloc[0]
    num_condition.append(col + ' ' + col_func + ' ' + num)
    n1, n2 = attri_ents[2].index(ed), end.index(ed)
    attri_ents[0].pop(n1), attri_ents[1].pop(n1), attri_ents[2].pop(n1)
    cols.pop(n2), start.pop(n2), end.pop(n2), nlu_ents.remove(c_ent)
    return cols, start, end, nlu_ents, num_condition


# This function used to find number filters (At Least, At Most)

def find_opp(nlu_ents, num, pos, term_df, cols, start, end, attri_ents):
    # separate filter entities
    con_ents = [ent for ent in nlu_ents if
                ((ent.label_ in ['num_filter_1', 'num_filter_2']) & (ent.text not in ['in', 'between', 'ranges', 'lies',
                                                                                      'range', 'equal', 'equals']))]
    num_condition = []
    if len(con_ents) > 0:
        for c_ent in con_ents:
            number = 0
            if (c_ent.end_char < pos) & ((pos - c_ent.end_char) <= 5):
                for col, st, ed, n2 in zip(cols[::-1], start[::-1], end[::-1], range(len(cols))[::-1]):
                    cut = len(c_ent.text) + 7
                    if (ed < pos) & ((pos - ed) <= cut):
                        parameters = [term_df, col, cols, start, end, nlu_ents, num_condition, ed, c_ent, num,
                                      attri_ents]
                        cols, start, end, nlu_ents, num_condition = getnlu_rm_cols(*parameters)
                        number = 1
                        break
                if number == 0:
                    for col, st, ed, n2 in zip(cols, start, end, range(len(cols))):
                        if st > pos:
                            parameters = [term_df, col, cols, start, end, nlu_ents, num_condition, ed, c_ent, num,
                                          attri_ents]
                            cols, start, end, nlu_ents, num_condition = getnlu_rm_cols(*parameters)
                            break

            elif (c_ent.start_char > pos) & ((c_ent.start_char - pos) <= 5):
                for col, st, ed, n2 in zip(cols[::-1], start[::-1], end[::-1], range(len(cols))[::-1]):
                    if (st < pos) & ((pos - ed) <= 5):
                        parameters = [term_df, col, cols, start, end, nlu_ents, num_condition, ed, c_ent, num,
                                      attri_ents]
                        cols, start, end, nlu_ents, num_condition = getnlu_rm_cols(*parameters)
                        number = 1
                        break
                if number == 0:
                    for col, st, ed, n2 in zip(cols, start, end, range(len(cols))):
                        if st > pos:
                            parameters = [term_df, col, cols, start, end, nlu_ents, num_condition, ed, c_ent, num,
                                          attri_ents]
                            cols, start, end, nlu_ents, num_condition = getnlu_rm_cols(*parameters)
                            break
            else:
                for col, st, ed, n2 in zip(cols[::-1], start[::-1], end[::-1], range(len(cols))[::-1]):
                    if (st < pos) & ((pos - ed) <= 5):
                        num_condition.append('filter ' + col + ' in ' + num)
                        n1 = attri_ents[1].index(st)
                        attri_ents[0].pop(n1), attri_ents[1].pop(n1), attri_ents[2].pop(n1)
                        cols.pop(n2), start.pop(n2), end.pop(n2)
                        number = 1
                        break
                if number == 0:
                    for col, st, ed, n2 in zip(cols, start, end, range(len(cols))):
                        if st > pos:
                            num_condition.append('filter ' + col + ' in ' + num)
                            n1 = attri_ents[1].index(st)
                            attri_ents[0].pop(n1), attri_ents[1].pop(n1), attri_ents[2].pop(n1)
                            cols.pop(n2), start.pop(n2), end.pop(n2)
                            break

            if len(num_condition) > 0:
                break
    else:
        number = 0
        for col, st, ed, n2 in zip(cols[::-1], start[::-1], end[::-1], range(len(cols))[::-1]):
            if (st < pos) & ((pos - ed) <= 5):
                num_condition.append('filter ' + col + ' in ' + num)
                n1 = attri_ents[1].index(st)
                attri_ents[0].pop(n1), attri_ents[1].pop(n1), attri_ents[2].pop(n1)
                cols.pop(n2), start.pop(n2), end.pop(n2)
                number = 1
                break
        if number == 0:
            for col, st, ed, n2 in zip(cols, start, end, range(len(cols))):
                if st > pos:
                    num_condition.append('filter ' + col + ' in ' + num)
                    n1 = attri_ents[1].index(st)
                    attri_ents[0].pop(n1), attri_ents[1].pop(n1), attri_ents[2].pop(n1)
                    cols.pop(n2), start.pop(n2), end.pop(n2)
                    break
    return num_condition


# This is to identify "in & not" based numerical filters

def get_in_and_notin(num, pos, cols, start, end, attri_ents, nlu_ents, term_df):
    num_condition = []
    number = 0
    ent_filters = ['num_filter_1', 'num_filter_2', 'dt_filter_1']
    con_ents = [ent for ent in nlu_ents if
                ((ent.label_ in ent_filters) & (ent.text in ['in', 'not', 'not in', 'following']))]
    if len(con_ents) > 0:
        for c_ent in con_ents[::-1]:
            for col, st, ed, n2 in zip(cols[::-1], start[::-1], end[::-1], range(len(cols))[::-1]):
                cut = len(col)+6 if c_ent.text == 'following' else 5
                if (c_ent.end_char < pos) & ((pos - c_ent.end_char) <= cut):
                    cut_2 = 4 if c_ent.text == 'following' else len(c_ent.text) + 3
                    if (st < pos) & ((pos - ed) <= cut_2):
                        col_func = term_df[term_df['terms'] == c_ent.text]['functions'].iloc[0]
                        num_condition.append('filter ' + col + ' ' + col_func + ' ' + ','.join(num.split()))
                        n1 = attri_ents[1].index(st)
                        attri_ents[0].pop(n1), attri_ents[1].pop(n1), attri_ents[2].pop(n1)
                        cols.pop(n2), start.pop(n2), end.pop(n2)
                        number = 1
                        break
            if number == 1:
                break
            else:
                continue

    return num_condition


def mask_numbers(input_text, num_posi_2, num_wrd_2):
    """ function for masking numbers which are used in numerical filters """

    for pos, wrd in zip(num_posi_2, num_wrd_2):
        input_text = input_text[:pos] + ("*" * len(wrd)) + input_text[pos + len(wrd):]
    return input_text

# Main function for numerical filters

def find_number_filter(input_text, attri_ents, des_df, term_df, nlu_ents, nlu_ents_copy):
    num_list, num_posi, num_wrd, input_text = find_numbers(input_text)
    num_list_2, num_posi_2, num_wrd_2 = [], [], []
    num_cond = []
    cols, start, end = [], [], []
    for col, st, ed in zip(*attri_ents):
        d_type = des_df[des_df['column_names'] == col]['data_type'].iloc[0]
        if d_type == 'numeric':
            cols.append(col), start.append(st), end.append(ed)
    if (len(cols) > 0) & (len(num_list) > 0):

        for num, pos, wrd in zip(num_list, num_posi, num_wrd):

            if len(num.strip().split()) == 2:
                num_1 = find_between(nlu_ents, num, pos, cols, start, end, attri_ents)
                num_cond = num_cond + num_1
                if len(num_1)>0:
                    num_list_2.append(num), num_posi_2.append(pos), num_wrd_2.append(wrd)

            elif len(num.strip().split()) == 1:
                num_2 = find_opp(nlu_ents, num, pos, term_df, cols, start, end, attri_ents)
                num_cond = num_cond + num_2
                if len(num_2)>0:
                    num_list_2.append(num), num_posi_2.append(pos), num_wrd_2.append(wrd)

            else:
                num_3 = get_in_and_notin(num, pos, cols, start, end, attri_ents, nlu_ents, term_df)
                num_cond = num_cond + num_3
                if len(num_3)>0:
                    num_list_2.append(num), num_posi_2.append(pos), num_wrd_2.append(wrd)

    if len(num_posi_2) > 0:
        input_text = mask_numbers(input_text, num_posi_2, num_wrd_2)

    text = input_text
    if len(nlu_ents_copy) > 0:
        for i in nlu_ents_copy:
            if i.text not in ['not', 'not in', 'in', 'not equal', 'is not']:
                text = text[:i.start_char] + ('*' * len(i.text)) + text[i.end_char:]
    # replace excluding with not in
    text = text.replace("exclude", "not in").replace("excluding", "not in")
    return num_cond, text
