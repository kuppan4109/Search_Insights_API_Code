# Libraries

import nltk
import pandas as pd
import Levenshtein as lv
from nltk.util import ngrams
from string_filters import find_string_filter
from numerical_filters import find_number_filter
from new_functionalities import rm_add_required_groups


def txt_clean(text, skip_keys):
    """
    function to remove unwanted words and punctuations
    :param text: input text
    :param skip_keys: keywords that needs to removed from text (df)
    :return: Text after removing unwanted words and symbols
    """

    # Get the keywords from the df
    key_words = skip_keys.keywords.to_list()
    # Get the keywords from the df
    punctuation = skip_keys.punctuation.to_list()
    for i in punctuation:
        text = text.replace(str(i),'')
    new_text = ' '.join([txt for txt in text.split() if txt not in key_words])
    return new_text


def get_attributes(txt, df_cols_as):
    """
    This function helps to find the attributes in the given text and it is also returns the attributes locations.

    :param txt: input text
    :param df_cols_as: attributes alias def
    :return: Attributes name list, and its stating and ending locations and input text.
    """

    # Initialize the string matching alg.
    match = lv.jaro
    # Get the aliases
    as_list = df_cols_as['alias'].to_list()

    cols, start_pos, end_pos = [], [], []
    # loop the aliases
    for txt_1 in as_list:
        n_grams = ngrams(txt.split(), len(txt_1.split()))
        # loop the N-Grams
        for wrd in n_grams:
            g_wrd = ' '.join(wrd)
            # Check the matching score and if it is only greater than cut of then consider that as attribute
            if match(txt_1.lower(), g_wrd) >= 0.92:
                col = df_cols_as[df_cols_as['alias'] == txt_1]['columns'].iloc[0]
                cols.append(col)
                # find the positions
                pos_1 = txt.find(g_wrd)
                pos_2 = pos_1 + len(g_wrd)
                # Mask the attribute name in the text
                txt = txt[:pos_1] + ('*' * len(g_wrd)) + txt[pos_2:]  # masking the column names
                start_pos.append(pos_1), end_pos.append(pos_2)
    # sort the column names based on the location in input text
    df = pd.DataFrame(zip(cols, start_pos, end_pos), columns=['a', 'b', 'c'])
    df.sort_values(by='b', inplace=True)
    cols, start_pos, end_pos = df.a.to_list(), df.b.to_list(), df.c.to_list()

    return cols, start_pos, end_pos, txt


def find_aggregation(nlu_ents, cols, start_loc, end_loc, des_df, term_df):
    """
    Function to match aggregation terms to corresponding columns and generating NLU

    :param nlu_ents: Entity list
    :param cols: column names in a list
    :param start_loc: starting locations of columns in text
    :param end_loc: ending locations of columns in text
    :param des_df: descriptive data frame
    :param term_df: keyword data frame
    :return: Aggregation query list, attribute list which contains column names and locations, and ending location
    """

    # Get aggregation entities
    agg_ents = [ent for ent in nlu_ents if ent.label_ in ['aggregation', 'aggregation_2']]
    # list the numerical columns
    numeric_cols = list(set(des_df[des_df['data_type'] == 'numeric']['column_names'].to_list()) & set(cols))

    aggregation, loc_2 = [], []
    # Copy the columns and locations for looping
    x, y, z = cols.copy(), start_loc.copy(), end_loc.copy()

    for col, st, end, n in zip(x, y, z, range(len(x))):
        # number for breaking for loop
        number = 0
        # loop the aggregation entities in reverse
        for ent in agg_ents[::-1]:
            if (ent.end_char < st) & ((st - ent.end_char) <= 5):
                # get the aggregation function from term df
                aggre_func = term_df[term_df['terms'] == ent.text]['functions'].iloc[0]
                # When it is categorical column
                if (aggre_func in ['distinct count', 'count distinct', 'count', 'sum']) & (col not in numeric_cols):
                    if aggre_func == 'count distinct':
                        aggregation.append("count of " + col)
                        # remove identified entities
                        agg_ents.remove(ent),loc_2.append(end)
                        number = 1
                        break
                    else:
                        if aggre_func == 'distinct count':
                            aggregation.append("distinct count of " + col)
                            n = start_loc.index(st)
                            # remove identified entities and column names and its locations
                            cols.pop(n), agg_ents.remove(ent), start_loc.pop(n), end_loc.pop(n), loc_2.append(end)
                        else:
                            aggregation.append("count of " + col)
                            n = start_loc.index(st)
                            # remove identified entities and column names and its locations
                            cols.pop(n), agg_ents.remove(ent), start_loc.pop(n), end_loc.pop(n), loc_2.append(end)
                        number = 1
                        break
                else:
                    # When it is categorical column
                    aggregation.append(aggre_func + " of " + col)
                    n = start_loc.index(st)
                    # remove identified entities and column names and its locations
                    cols.pop(n), agg_ents.remove(ent), start_loc.pop(n), end_loc.pop(n), loc_2.append(end)
                    number = 1
                    break

        if number == 0:
            if (len(agg_ents) > 0) & (len(cols) > 0):
                # loop the aggregation entities from the beginning
                for ent in agg_ents:
                    if (ent.start_char > st) & ((ent.start_char - end) <= 4) & (col in numeric_cols):
                        aggre_func = term_df[term_df['terms'] == ent.text]['functions'].iloc[0]
                        n = start_loc.index(st)
                        aggregation.append(aggre_func + " of " + col)
                        # remove identified entities and column names and its locations
                        cols.pop(n), agg_ents.remove(ent), start_loc.pop(n), end_loc.pop(n), loc_2.append(end)
                        break
    # combine column names and its locations
    attributes = [cols, start_loc, end_loc]

    return aggregation, attributes, loc_2


def find_grouby(nlu_ents, attri_ents):
    """
    This function is used to get the group by columns

    :param nlu_ents: Entites
    :param attri_ents: list contains column and its locations
    :return: list of column which will be used for grouping and attributes
    """

    # Get the relevan entities
    grp_ents = [ent for ent in nlu_ents if ent.label_ == 'group']

    grpby_cols_list = []
    for grp in grp_ents:
        # loop of column names
        for col, st, end, n in zip(*attri_ents, range(len(attri_ents[0]))):
            if (st > grp.start_char) & ((st - grp.start_char) <= 4):
                grpby_cols_list.append('by ' + col)
                # remove identified entities and column names and its locations
                attri_ents[0].pop(n), attri_ents[1].pop(n), attri_ents[2].pop(n)  # remove identified columns
                break

    return grpby_cols_list, attri_ents


def get_deflt_agg(cols_list, des_df):
    """
     function for creating default aggregation for the columns which are not included in any of the functions.
    """

    nlu_user, nlu_query = [], []
    for col_name in cols_list:
        d_type = des_df[des_df['column_names'] == col_name]['data_type'].iloc[0]
        # Average is default aggregation for quantitative attributes
        if d_type == 'numeric':
            nlu_query.append('average of ' + col_name)
            nlu_user.append('average of ' + col_name)
        else:
            nlu_query.append('by ' + col_name)
            nlu_user.append('by ' + col_name)
    return nlu_user, nlu_query


def top_botom_sort(input_text, tagger, attri_ents, nlu_ents, des_df, agg_nlu_list):
    """
    Function to indentify ordering keywords in text and decides ordering column and order type

    :param input_text: Input from user
    :param tagger: customized pos tagger
    :param attri_ents: attributes and its locations
    :param nlu_ents: entities
    :param des_df: descriptive data frame
    :param agg_nlu_list: aggregation nlu list
    :return: top or bottom type, ordering Query and text
    """

    global top_bot
    # split the text by coma and rejoin
    text = " ".join(input_text.replace(",", " ").split()).lower()
    # Define customized grammer and get the chunks
    grammar = "NP: {<XYZ><CD>}"
    chunkParser = nltk.RegexpParser(grammar)
    tree = chunkParser.parse(tagger.tag(text.split()))

    top_bot = []
    for subtree in tree.subtrees(filter=lambda t: t.label() == 'NP'):
        word = " ".join([a for (a, b) in subtree.leaves()])
        top_bot.append(" ".join([num for num in word.split() if num not in ['and', 'to']]))

    if len(top_bot) > 0:
        for i in top_bot:
            k = "*" * len(i)
            # Replace the word with *
            text = text.replace(i, k)

    # Get the relevant entities
    sort_ents1 = [i for i in nlu_ents if i.label_ in ['sort_1', 'sort_2']]
    sort_ents2 = [i for i in nlu_ents if i.text == 'descending']

    order = []
    if len(sort_ents1) > 0:
        ent = sort_ents1[0]
        # loop the columns and its locations
        for col, st, ed in zip(*attri_ents):
            if (ent.end_char < st) & ((st - ent.end_char) <= 4):
                n = attri_ents[1].index(st)
                # remove the identified column and its locations
                attri_ents[0].pop(n), attri_ents[1].pop(n), attri_ents[2].pop(n)

                d_type = des_df[des_df['column_names'] == col]['data_type'].iloc[0]

                if d_type == 'numeric':
                    agg_nlu_list_split = ' '.join(agg_nlu_list).split()
                    if col in agg_nlu_list_split:
                        for agg in agg_nlu_list:
                            if col in agg:
                                col = '_'.join(agg.split())
                                break
                    else:
                        dflt_agg = des_df[des_df['column_names'] == col]['default_agg'].iloc[0]
                        col = dflt_agg + '_of_' + col
                else:
                    col = col
                # decide whether it is ascending order or descending order
                if len(sort_ents2) > 0:
                    order.append('order by ' + col + ' desc')
                    break
                else:
                    order.append('order by ' + col)
                    break

    return top_bot, order, text


def chse_sort_top(sort, top_bot_chunks, aggwrd, grp_wrd):
    """
    function to make decision on sorting (when both sorting and top words are exist in input text)
    """

    sort = sort[0] if len(sort) > 0 else ''

    try:
        # get first element from top bottom chunk list
        top_bot = top_bot_chunks[0]
        # When bottom was asked
        if top_bot.split()[0] == 'bottom':
            # Get the number and append to "top" string
            top_bot = 'top ' + top_bot.split()[1]
            # Decide which column need to sorted in descending
            if (len(aggwrd) > 1) & (len(sort) < 2):
                sort = 'order by ' + aggwrd.split(',')[0].split()[-1]
            elif (len(grp_wrd) > 1) & (len(sort) < 2):
                sort = 'order by ' + grp_wrd.split(',')[0] + ' desc'
        else:
            # when top was asked
            if (len(aggwrd) > 1) & (len(sort) < 2):
                # Get only one numerical attribute and sort based on that
                sort = 'order by ' + aggwrd.split(',')[0].split()[-1] + ' desc'
            elif (len(grp_wrd) > 1) & (len(sort) < 2):
                sort = 'order by ' + grp_wrd.split(',')[0]
    except:
        # When there is no aggregation
        if len(top_bot_chunks) > 0:
            top_bot = top_bot_chunks[0]
        else:
            top_bot = ''

    return sort, top_bot, aggwrd, grp_wrd


def custom_pos():
    """ Customize nltk's part of speech tag """

    # Load the tagger
    default_tagger = nltk.data.load('taggers/maxent_treebank_pos_tagger/english.pickle')
    # Create the dictionary of words and its tags
    wrd_list1 = ['starts', 'start', 'starting', 'ends', 'end', 'ending', 'contains', 'top', 'bottom', 'with']
    wrd_list2 = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec', 'january',
                 'february', 'march', 'april', 'may', 'june', 'july', 'august', 'september', 'october', 'november',
                 'december']
    wrd_list3 = ['sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sun', 'mon', 'tue',
                 'wed', 'thu', 'fri', 'sat', '-', '--']

    my_dict = dict.fromkeys(wrd_list1, "XYZ")
    my_dic2 = dict.fromkeys(wrd_list2, "DT")
    my_dic3 = dict.fromkeys(wrd_list3, "DAY")
    my_dict.update(my_dic2)
    my_dict.update(my_dic3)
    # Pass the dictionary to the tagger
    tagger = nltk.tag.UnigramTagger(model=my_dict, backoff=default_tagger)
    return tagger


def find_filters(input_text, nlu_ents, nlu_ents_copy, attri_ents, des_df, term_df, level_dict, tagger):
    """
    Main function for indentify string and numeric filters
    :return: filters list, remaining column list and its ending locations
    """

    # Get the number filters,if any
    filter_1, text = find_number_filter(input_text, attri_ents, des_df, term_df, nlu_ents, nlu_ents_copy)
    if len(text) > 1:
        # Get the string filter, if any
        filter_2, cols_list, end_loc = find_string_filter(text, tagger, attri_ents, level_dict, des_df)
        filters_list = filter_1 + filter_2

    return filters_list, cols_list, end_loc


def remove_duplicate(aggregators, groupby_cols):
    """
    This function used to remove repeated aggregation queries from the SELECT section

    :param aggregators: Aggregation query [sum(sales)]
    :param groupby_cols: Group by columns [category]
    :return: Queries without duplicate
    """

    temp_lis1 = []
    for element in [aggregators.lower(), groupby_cols.lower()]:
        temp_lis2 = []
        # split the queries by comma and remove the duplicates
        word_list = element.split(', ')
        for i in word_list:
            if i not in temp_lis2:
                temp_lis2.append(i)
        # Join the splits queries after removing duplicates
        words = ', '.join(temp_lis2)
        temp_lis1.append(words)
    aggregators, groupby_cols = temp_lis1[0], temp_lis1[1]

    return aggregators, groupby_cols


def get_cumulative_agg(nlu_ents, group_by, cols, start_loc, des_df):
    """
    This function helps to create cumulative aggregation SQL queries
    """

    # filter the relevent entities and columns
    groups = ', '.join(group_by)
    # Get the relevant entities
    agg_ents = [ent for ent in nlu_ents if ent.label_ == 'aggregation_3']
    # Get the numerical columns
    numeric_cols = list(set(des_df[des_df['data_type'] == 'numeric']['column_names'].to_list()) & set(cols))
    cum_agg_list, keys = [], []
    # make loop of entities
    for ent in agg_ents:
        for col, st_loc in zip(cols, start_loc):
            # get the first word of entities
            text = ent.text.split()[1]
            cols_2 = cols if text in ['count', 'counts'] else numeric_cols
            if (st_loc > ent.end_char) & (col in cols_2):
                # match the first word and create sql query according to it
                if text in ['sum', 'total']:
                    cum_agg = 'sum(' + col + ') over(order by ' + groups + ') as cum_sum_' + str(col)
                    keys.append('cumulative total ' + str(col))
                    cum_agg_list.append(cum_agg)
                elif text in ['min', 'minimum']:
                    cum_agg = 'min(' + col + ') over(order by ' + groups + ') as cum_min_' + str(col)
                    keys.append('cumulative minimum ' + str(col))
                    cum_agg_list.append(cum_agg)
                elif text in ['max', 'maximum']:
                    cum_agg = 'max(' + col + ') over(order by ' + groups + ') as cum_max_' + str(col)
                    keys.append('cumulative maximum ' + str(col))
                    cum_agg_list.append(cum_agg)
                elif text in ['count', 'counts']:
                    group_by = [col_name for col_name in group_by if col_name != col]
                    groups = ', '.join(group_by)
                    cum_agg = 'count(' + col + ') over(order by ' + groups + ') as cum_count_' + str(col)
                    keys.append('cumulative count ' + str(col))
                    cum_agg_list.append(cum_agg)
                elif text in ['avg', 'mean', 'average']:
                    cum_agg = 'avg(' + col + ') over(order by ' + groups + ') as cum_avg_' + str(col)
                    keys.append('cumulative average ' + str(col))
                    cum_agg_list.append(cum_agg)
                # remove the column from the list and its location
                cols.remove(col), start_loc.remove(st_loc)
                break

    return cum_agg_list, cols, keys


def create_title(aggregations, group_by, col_list_title, keys, growth_nlu):
    """
    generate default title for chart using keywords generated from the input text
    """

    title1, title2 = [], []
    # NLU -> Natural language understanding eg: average of month or by category
    title_nlus = aggregations + group_by

    # loop the column
    for column_1 in col_list_title:
        for column_2 in title_nlus:
            col_words = column_2.split()

            if str(col_words[0]) == 'by':
                # join the splitted words except by (for categorical column)
                attribute1 = ' '.join(col_words[1:])
                if column_1 == attribute1:
                    title_nlus.remove(column_2)
                    title2.append(attribute1)
                    break
            else:
                # join the splitted words except first 2 words (numerical column)
                attribute1 = ' '.join(col_words[2:])
                if column_1 == attribute1:
                    attribute2 = ' '.join(column_2.split(' of '))
                    attribute2 = attribute2.replace("sum ", 'total ')
                    title1.append(attribute2)
                    title_nlus.remove(column_2)
                    break
    # join the first title list (numerical aggregations eg: total sales and average profit)
    title1 = ' and '.join(title1)
    if len(title2) > 0:
        # Append the title 2 with title 1 (title 2 will contains categorical column names)
        title2 = ' and '.join(title2)
        title = title1 + ' by ' + title2
        title = title.replace('_', ' ')
    else:
        title = title1.replace('_', ' ')

    # keys list will contains time phrases like days months
    if len(keys) > 0:
        title_list = title.split()
        # If "by" already present in title we need not add one more "by" otherewise we have to
        if 'by' in title_list:
            if len(keys) == 1:
                title = title + ' ' + 'and ' + keys[0]
            else:
                title = title + ' ' + ' and '.join(keys)
        else:
            if len(keys) == 1:
                title = title + ' ' + ' by ' + keys[0]
            else:
                title = title + ' by ' + ' and '.join(keys)
    # growth nlu list contains terms like MTD YTD if anything present in the list we need to append them in beginning
    if len(growth_nlu) > 0:
        title = 'and '.join(growth_nlu) + ' ' + title

    return title


def agg_nlg(splited_agg_nlu, agg_nlu):
    """
    Function which convert the aggregation related entities into sql statements. (average of sales to avg(sales))
    """

    aggregation_text = ''
    if splited_agg_nlu[0] in ['minimum', 'maximum', 'sum']:
        aggregation_text = splited_agg_nlu[0][:3] + "(" + splited_agg_nlu[-1] + ") as " + '_'.join(agg_nlu.split())
    elif 'distinct count' in agg_nlu:
        aggregation_text = 'count (distinct ' + splited_agg_nlu[-1] + ") as " + '_'.join(agg_nlu.split())
    elif splited_agg_nlu[0] in ['count', 'distinct']:
        aggregation_text = splited_agg_nlu[0] + "(" + splited_agg_nlu[-1] + ") as " + '_'.join(agg_nlu.split())
    elif 'average' in agg_nlu:
        aggregation_text = 'avg' + "(" + splited_agg_nlu[-1] + ") as " + '_'.join(agg_nlu.split())

    return aggregation_text


def nlg(nlu_list):
    """
    This is the main function which helps to convert all the NLUs into the SQL statements.
    """

    aggregation, condition, groupby, top_bot, bot = [], [], [], '', ''
    agg = ['minimum', 'maximum', 'average', 'sum', 'count', 'distinct']

    for nlu in nlu_list:
        str_split = nlu.replace(',', ' ').split()

        # AGGREGATION
        if str_split[0] in agg:
            y = agg_nlg(str_split, nlu)
            aggregation.append(y)

        # CONDITIONS
        elif str_split[0] == 'filter':
            if str_split[2] == 'not':
                txt = ' '.join([k for k in nlu.split()[4:]])
                a = str_split[1] + " not in (" + ','.join(["'" + j + "'" for j in txt.split(',')]) + ")"
                condition.append(a)
            else:
                txt = ' '.join([k for k in nlu.split()[3:]])
                a = str_split[1] + " in (" + ','.join(["'" + j + "'" for j in txt.split(',')]) + ")"
                condition.append(a)

        elif str_split[1] == 'between':
            b = str_split[0] + " between " + ' and '.join(str_split[2:])
            condition.append(b)

        elif (str_split[1] == 'at') | (str_split[1] == 'not'):
            if str_split[2] == 'most':
                d = str_split[0] + '<=' + str_split[-1]
                condition.append(d)
            elif str_split[2] == 'least':
                d = str_split[0] + '>=' + str_split[-1]
                condition.append(d)
            else:
                d = str_split[0] + ' not in (' + ','.join(["'" + dt + "'" for dt in str_split[3:]]) + ')'
                condition.append(d)

        elif str_split[1] in ['start', 'starts', 'starting']:
            f = str_split[0] + ' like ' + "'" + str_split[-1] + "%'"
            condition.append(f)

        elif str_split[1] in ['end', 'ends', 'ending']:
            g = str_split[0] + ' like ' + "'%" + str_split[-1] + "'"
            condition.append(g)

        elif str_split[1] == 'contains':
            h = str_split[0] + ' like ' + "'%" + str_split[-1] + "%'"
            condition.append(h)

        # GROUP BY
        elif str_split[0] == 'by':
            e = str_split[1]
            groupby.append(e)

    aggwrd = ', '.join(aggregation)
    cond_wrd = ' and '.join(condition)
    grp_wrd = ', '.join(groupby)

    return aggwrd, cond_wrd, grp_wrd


def query_generate(table_name, top_bot, aggwrd, cond_wrd, grp_wrd, sort, having, cumulate, input_quest, des_df):
    """
    This function will help to generate the SQL query from the converted SQL statements

    :param table_name: table name in SQL-DB
    :param top_bot: query for top or bottom selection
    :param aggwrd: aggregation query (avg(sales) as average_of_sales)
    :param cond_wrd: filter queries (where section)
    :param grp_wrd: grouping section query
    :param sort: order by section query
    :param having: having section query
    :param cumulate: parameter for cumulative aggregation check
    :param input_quest: Input question from the user
    :param des_df: descriptive satistics data frame
    :return: Proper executable SQL query.
    """

    # Assign initial empty sections
    select, table, fltr_sec, grp_sec, ordr_sec = 'select ', table_name, '', '', ''

    # logical check for creating proper select section query
    if (len(grp_wrd) > 0) & (len(aggwrd) > 0):
        agre_sec = grp_wrd + ', ' + aggwrd
        agre_sec = ', '.join([i for i in agre_sec.split(', ')])
    elif len(grp_wrd) > 0:
        agre_sec = grp_wrd
        agre_sec = ', '.join([i for i in agre_sec.split(',')])
    else:
        agre_sec = aggwrd
    agre_sec, _ = remove_duplicate(agre_sec, '')

    # logical check for creating proper filter section query
    if len(cond_wrd) > 0:
        fltr_sec = 'where ' + cond_wrd

    # logical check for creating proper group by section query
    if len(grp_wrd) > 0:
        grp_wrd = ', '.join([i.split(' as ')[0] for i in grp_wrd.split(', ')])
        grp_sec = 'group by ' + grp_wrd

    # logical check for creating proper having section query
    if len(having) > 1:
        having_sec = 'having ' + having
    else:
        having_sec = ''

    # logical check for creating proper order by section query
    if len(sort) > 0:
        ordr_sec = sort
    if cumulate == 1:
        ordr_sec = 'order by ' + grp_wrd.split(', ')[0]
        agre_sec = 'distinct ' + agre_sec
        grp_sec = ''
    elif cumulate == 2:
        ordr_sec = 'order by ' + grp_wrd.split(', ')[0]
    if (len(ordr_sec) > 2) & (ordr_sec[:9] != 'order by '):
        ordr_sec = 'order by ' + ordr_sec

    # remove unwanted gropby segments from the group section
    agre_sec, grp_sec, ordr_sec = rm_add_required_groups(input_quest, agre_sec, fltr_sec, grp_sec, ordr_sec, des_df)

    query = select + top_bot + ' ' + agre_sec + ' from ' + table + ' ' + fltr_sec + ' ' + grp_sec + ' ' + having_sec + ' ' + ordr_sec

    # remove unwanted spaces from final query
    query = ' '.join(query.strip().split())

    return query


