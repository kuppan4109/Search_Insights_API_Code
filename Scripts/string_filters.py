

# load the Libraries

import pandas as pd
from nltk.util import ngrams
from nltk import RegexpParser
from fuzzywuzzy import fuzz as fz


fzr = fz.ratio
fzt = fz.token_sort_ratio


def get_startwith_endwith(input_text, custom_postag):
    """
    Function to find and get chunks from the input text which wiil be used for string filters like (starts with la)

    :param input_text: input text asked by user
    :param custom_postag: customized pos tag
    :return: filterd chunks and it's positions in the input text
    """

    # choose the tag names which are needed to get relevant chunks
    tag1 = 'DT|EX|FW|IN|JJ|JJR|JJS|LS|MD|NN|NNS|NNP|NNPS|PDT|POS|PRP|PRP$|'
    tag2 = 'RB|RBR|RBS|RP|SYM|TO|UH|VB|VBD|VBG|VBN|VBP|VBZ|,'
    pos_tags = tag1 + tag2
    # create chuck pattern and pass it to chunk parser
    grammar = "NP: {<XYZ><XYZ>?<" + pos_tags + ">}"
    chunkParser = RegexpParser(grammar)
    tree = chunkParser.parse(custom_postag.tag(input_text.split()))

    # Get the chunks
    verb_list, verb_posi = [], []
    for subtree in tree.subtrees(filter=lambda t: t.label() == 'NP'):
        word = " ".join([a for (a, b) in subtree.leaves()])
        # get the starting position of words
        position = input_text.find(word)
        if position < 0:
            position = len(input_text)
        verb_posi.append(position)
        # append the chunks in list
        verb_list.append(" ".join([wrd for wrd in word.split()]))

    return verb_list, verb_posi


def addcols_startwith_endwith(input_text, col_list, start_loc, cols_loc_list, verb_list, verb_posi):
    """
    This function helps to append corresponding columns to the chunks (starts with, ends with)

    :param input_text: input text asked by user
    :param col_list: column names in list
    :param start_loc: locations of each column from the input text
    :param cols_loc_list: list of column names and its locations
    :param verb_list: identified chunks list (starts with ca)
    :param verb_posi: positions of chunks
    :return: filter (category starts with ca), input_text, column list
    """

    string_cond = []
    # loop the chunks and its positions (reverse order)
    for chk, pos in zip(verb_list[::-1], verb_posi[::-1]):
        # loop the column names and it's starting locations
        for st, col in zip(start_loc[::-1], col_list[::-1]):

            if st < pos:
                # check if not present in text before chunk
                if input_text[:pos].split()[-1] == 'not':
                    chk = 'not '+ chk
                # append the col name with condition (category starts with ca)
                string_cond.append(col + ' ' + chk)
                input_text = input_text.replace(chk, '')
                # remove the column names and its locations from list
                n1 = cols_loc_list[1].index(st)
                cols_loc_list[0].pop(n1), cols_loc_list[1].pop(n1), cols_loc_list[2].pop(n1)
                n2 = start_loc.index(st)
                start_loc.pop(n2), col_list.pop(n2)
                break

    input_text = input_text.replace('*', '')

    return string_cond, input_text, col_list


# find, is there any attribute's levels in input text and match them with corresponding column.

def get_levels(input_text, level_dict, col_list, cols_loc_list):
    """
    Function to get levels of attributes (iphone from mobiles column) which will be used as filter

    :param input_text: input text asked by user
    :param level_dict: Dictionary contains all the levels or values of each categorical column
    :param col_list: column list
    :param cols_loc_list: list of column names and its locations
    :return: filters ( mobiles in iphone), list of column names and its locations
    """

    # remove unwanted words
    input_text = input_text.replace('*', '').replace("'", '')
    prep = ['for', 'is', 'was', 'in', 'on', 'with', 'what', 'and', 'but', 'to', 'which', 'how', 'who', ',', 'show',
            'me', 'tell', 'when', 'where', 'the', 'an', 'date', 'over', 'are', 'there', 'under', 'has']
    text = ' '.join([wrd for wrd in input_text.split() if wrd not in prep]).lower()

    # empty df for add all the levels and its attribute names
    df_filter = pd.DataFrame(columns=['Col_name', 'Level'])
    cols_rm = set()
    notin_fltr_cols_list = []
    # if there is any column names, first look for their levels in the text
    if len(col_list) > 0:
        # loop the columns
        for col in col_list:
            # loop the levels of columns
            for lvl in level_dict[col]:
                lvl = str(lvl).lower()
                n = len(lvl.split())
                # when level is 1 word
                if n <= 1:
                    # cut of value for word distance
                    cut = 80 if len(lvl) <= 6 else 86
                    for wrd in text.split():
                        # generate fuzzywuzzy ratio and check with cut of value
                        if fzr(lvl, wrd) >= cut:
                            pos = text.find(wrd)
                            # append column and level in data frame
                            df_filter.loc[len(df_filter)] = [col, lvl]
                            # check if "not" presented before the level
                            if set(text[:pos].split()[-3:]) & {'not'}:
                                notin_fltr_cols_list.append(col)
                            # remove identified word from text
                            text = text[:pos] + text[pos + len(wrd) + 1:]
                            cols_rm.add(col)
                            break
                # when level is more than one word
                else:
                    # make n-grams based on the number of word in level and loop the n-grams
                    grams = ngrams(text.split(), n=n)
                    for wrd in grams:
                        wrd = ' '.join(wrd)
                        # generate fuzzywuzzy ratio and check with cut of value
                        if fzt(lvl, wrd) > 90:
                            pos = text.find(wrd)
                            df_filter.loc[len(df_filter)] = [col, lvl]
                            # check if "not" presented before the level
                            if set(text[:pos].split()[-3:]) & {'not'}:
                                notin_fltr_cols_list.append(col)
                            # remove identified word from text
                            text = text[:pos] + text[pos + len(wrd) + 1:]
                            cols_rm.add(col)
                            break

    # when there is no column in lest
    if len(text) > 0:
        # get all the categorical columns from dictionary
        col_names = [col for col in level_dict.keys() if col not in col_list]
        for col in col_names:
            # loop the levels
            for lvl in level_dict[col]:
                lvl = str(lvl).lower()
                n = len(lvl.split())
                # when level is 1 word
                if n == 1:
                    # generate fuzzywuzzy ratio and check with cut of value
                    cut = 80 if len(lvl) <= 2 else 87
                    for wrd in text.split():
                        if fzr(lvl, wrd) >= cut:
                            pos = text.find(wrd)
                            # append to the df
                            df_filter.loc[len(df_filter)] = [col, lvl]
                            # check if "not" presented before the level
                            if set(text[:pos].split()[-3:]) & {'not'}:
                                notin_fltr_cols_list.append(col)
                            # remove identified word from text
                            text = text[:pos] + text[pos + len(wrd) + 1:]
                            break
                # when level is more than one word
                else:
                    # make n-grams based on the number of word in level and loop the n-grams
                    grams = ngrams(text.split(), n=n)
                    for wrd in grams:
                        wrd = ' '.join(wrd)
                        # generate fuzzywuzzy ratio and check with cut of value
                        if fzt(lvl, wrd) > 90:
                            pos = text.find(wrd)
                            df_filter.loc[len(df_filter)] = [col, lvl]
                            # check if "not" presented before the level
                            if set(text[:pos].split()[-3:]) & {'not'}:
                                notin_fltr_cols_list.append(col)
                            # remove identified word from text
                            text = text[:pos] + text[pos + len(wrd) + 1:]
                            break
                # Check for next iteration
                if len(text) > 0:
                    continue
                else:
                    break
            # Check for next iteration
            if len(text) > 0:
                continue
            else:
                break
    # Remove all the column which are used in this phase
    for rm_col in cols_rm:
        idx = cols_loc_list[0].index(rm_col)
        cols_loc_list[0].pop(idx)
        cols_loc_list[2].pop(idx)

    # Generate common pharse for filters
    filter_level = []
    if len(df_filter) > 0:
        for col in df_filter['Col_name'].unique():
            fil_list = df_filter[df_filter['Col_name'] == col]['Level'].to_list()
            if col in notin_fltr_cols_list:
                filter_level.append('filter ' + col + ' not in ' + ','.join(fil_list))
            else:
                filter_level.append('filter ' + col + ' in ' + ','.join(fil_list))

    col_name_list = cols_loc_list[0]
    end_loc_list = cols_loc_list[2]

    return filter_level, col_name_list, end_loc_list


def find_string_filter(input_text, tagger, cols_loc_list, level_dict, des_df):
    """
    Main calling function for string filters

    :param input_text: input text asked by user
    :param tagger: customized par of speech tagger
    :param cols_loc_list: list of column names and its locations
    :param level_dict: Dictionary contains all the levels or values of each categorical column
    :param des_df: df contains descriptive stat about all the columns
    :return: filters, column list, end location of columns
    """

    # get start with ends with chunks if any
    verb_list, verb_posi = get_startwith_endwith(input_text, tagger)

    # Get categorical columns and its locations alone
    cols_list, start_loc = [], []
    for col_name, st, _ in zip(*cols_loc_list):
        d_type = des_df[des_df['column_names'] == col_name]['data_type'].iloc[0]
        if d_type == 'object':
            cols_list.append(col_name), start_loc.append(st)

    filter_cond = []
    # Get starts with ends with filters, if any
    if len(verb_list) > 0:
        startwith_endwith_filters, input_text, cols_list = addcols_startwith_endwith(input_text, cols_list, start_loc, cols_loc_list, verb_list, verb_posi)
        filter_cond = filter_cond + startwith_endwith_filters
    # Get level based filters, if any
    if len(input_text) > 1:
        level_filters, cols_list, end_loc_list = get_levels(input_text, level_dict, cols_list, cols_loc_list)
        filter_cond = filter_cond + level_filters
    else:
        end_loc_list = []

    return filter_cond, cols_list, end_loc_list