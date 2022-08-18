
""" This module includes many functionalities which all are developed after the Demo happened with product team """

# libraries

from nltk.stem import WordNetLemmatizer

lemtz = WordNetLemmatizer()


def get_null(nlu_ents, columns, end_locations, default_dt):
    """
    This function will be used to generate SQL queries for removing or including null or blanks of attributes.

    :param nlu_ents: Trained NER
    :param columns: Identified column from the input text
    :param end_locations: ending locations of each column in text
    :param default_dt: Default date column
    :return: List of SQL query which will be either including null values or excluding null values & not used attributes
    """

    # Extract relevant entities from the NER model
    empty_no = [i for i in nlu_ents if i.label_ in ['empty', 'empty_0']]
    empty_yes = [i for i in nlu_ents if i.label_ in ['empty_1', 'empty_2']]
    dt_related_ents = [i for i in nlu_ents if i.label_ == 'empty_today']

    # Taking copy of attributes
    cols = columns.copy()
    # Loop to match the column names and entities to generate SQL query
    sql_query_list = []
    for col_name, end_loc in zip(columns[::-1], end_locations[::-1]):
        # first loop to generate SQL queries which will exclude NULL or Empty cells
        for ent in empty_no:
            if (end_loc < ent.start_char) & ((ent.start_char - end_loc) <= 5):
                list_com_words = list(set(ent.text.split()) & {'blanks', 'blank', 'null', 'empty'})
                if len(list_com_words) > 1:
                    query = col_name + " not in ('NULL', 'null', '')"
                else:
                    if list_com_words[-1] in ['blanks', 'blank', 'empty']:
                        query = col_name + " not in ('')"
                    else:
                        query = col_name + " not in ('NULL', 'null')"
                sql_query_list.append(query)
                cols.remove(col_name)
        # second loop to generate SQL queries which will include only NULL or Empty cells
        for ent in empty_yes:
            if (end_loc < ent.start_char) & ((ent.start_char - end_loc) <= 5):
                list_com_words = list(set(ent.text.split()) & {'blanks', 'blank', 'null', 'empty'})
                if len(list_com_words) > 1:
                    query = col_name + " in ('NULL', 'null', '')"
                else:
                    if list_com_words[-1] in ['blanks', 'blank', 'empty']:
                        query = col_name + " in ('')"
                    else:
                        query = col_name + " in ('NULL', 'null')"
                sql_query_list.append(query)
                cols.remove(col_name)
    # this will exclude today date from output table
    if len(dt_related_ents) > 0:
        sql_query_list.append(default_dt + " < getdate()")

    return sql_query_list, cols


def get_dt_filter_day_to_month(agg_query, grp_wrd, nlu_ents, default_date):
    """
    This function helps to aggregate table like first/last day of month

    :param agg_query: sql query which is in select phase
    :param grp_wrd: sql query which is used for groupby
    :param nlu_ents: nlp model
    :param default_date: default colum for date
    :return: will return appended sql query with data functions if any
    """

    # select required nlp entities and make the query based on the keyword
    dt_ents = [i.text for i in nlu_ents if i.label_ == 'dt_filter_10']
    if len(dt_ents) > 0:
        dt_query = []
        for ent in dt_ents:
            pos = 1 if ent.split()[0] == 'first' else 0
            if pos == 1:
                query = "dateadd(day, 1, eomonth(" + default_date + ", -1)) as start_of_month"
            else:
                query = "eomonth(" + default_date + ") as end_of_month"
            dt_query.append(query)
        # join the queries
        query = ', '.join(dt_query)
        orderby = ', '.join([q.split(' as ')[0] for q in dt_query])
        # check the length of previous query to append new query in appropriate place
        if len(agg_query) > 5:
            agg_query = agg_query + ', ' + query
        else:
            agg_query = query
        if len(grp_wrd) > 5:
            grp_wrd = grp_wrd + ', ' + query
        else:
            grp_wrd = query
    else:
        orderby = ''
    return agg_query, grp_wrd, orderby


def get_share(columns, start_loccation, agg_query, grp_wrd, filters, nlu_ents, des_df):
    """
    This function help to calculate percentage / share

    :param columns: All the columns identified in input question
    :param start_loccation: starting location of each columns in input question
    :param agg_query: generated sql query in select section
    :param grp_wrd: generated sql query for group by section
    :param filters: generated sql query for where section
    :param nlu_ents: Entities indentified by NLP model
    :param des_df: Descriptive df of table
    :return: updated sql query in select section and group by section
    """

    # Select the required column and entities
    cat_clos_list = list(des_df[des_df['data_type'] == 'object']['column_names'].unique())
    num_col_list = list(des_df[des_df['data_type'] == 'numeric']['column_names'].unique())
    share_ents = [i for i in nlu_ents if i.label_ == 'share']

    if len(share_ents) > 0:
        text1 = agg_query
        text2 = ' '.join(filters)
        # split the query by following symbols to indentify common columns
        for splt_txt in [',', ', ', '(', ')']:
            agg_query_splitted = text1.split(splt_txt)
            filter_query_splitted = text2.split(splt_txt)
            text1 = ' '.join(agg_query_splitted)
            text2 = ' '.join(filter_query_splitted)
        com_num_cols = list(set(num_col_list) & set(text1.split()))
        com_cat_cols = list(set(cat_clos_list) & set(text2.split()))

        if (len(com_num_cols) > 0) | (len(com_cat_cols) > 0):
            query = ''
            ent = share_ents[0]
            check_val = 0
            # loop the attributes and its locations
            for col, loc in zip(columns, start_loccation):
                if (ent.end_char < loc) & ((loc - ent.end_char) < 7) & (col in com_num_cols):
                    splited_agg_query = agg_query.split(',')
                    # remove the previous query (avg(sales) as avg_sales to '')
                    for previous_query in splited_agg_query:
                        if col in previous_query:
                            if len(splited_agg_query) > 1:
                                agg_query = agg_query.replace(previous_query + ',', '')
                            else:
                                agg_query = agg_query.replace(previous_query, '')
                    # make the query
                    query = "round(sum(" + col + ") * 100 / sum(sum(" + col + ")) over (),0) as share_pct"
                    check_val = 1
                    break
            if check_val == 0:
                for col, loc in zip(columns, start_loccation):
                    if (ent.end_char < loc) & (col in com_cat_cols):
                        # make the query
                        query = "round(count(*) * 100 / sum(count(*)) over (),0) as share_pct"
                        break
            # Append the query in proper format
            if len(query) > 5:
                if len(agg_query) > 5:
                    agg_query = agg_query + ', ' + query
                else:
                    agg_query = agg_query + query

    return agg_query, grp_wrd


def rm_add_required_groups(input_quest, agg, whr, grp, ord, des_df):
    """
    This function used to add attribute name used for comparison filter and remove time group used for ago filter
    """

    # check if ago word present in input text
    if ' ago' in input_quest:
        n = input_quest.find("ago")
        # find the time word befor the ago word
        time = input_quest[:n].split()[-1]
        time_list = ['day', 'days', 'week', 'weeks', 'month', 'months', 'quarter', 'quarters',
                     'year', 'years', 'hour', 'hours', 'minute', 'minutes']

        if time in time_list:
            time = lemtz.lemmatize(time)
            agg_q_list = []
            # split aggregation query and remove the appropriate query from selection, group by & order by section
            for ag_query in agg.split(', '):
                if time not in ag_query:
                    agg_q_list.append(ag_query)
            grp_q_list = []
            for grp_query in grp.split(', '):
                if time not in grp_query:
                    grp_q_list.append(grp_query)
            ord_q_list = []
            for ord_query in ord.split(', '):
                if time not in ord_query:
                    ord_q_list.append(ord_query)
            # join the splitted list arfer removing indentified query
            agg = ', '.join(agg_q_list)
            grp = ', '.join(grp_q_list)
            ord = ', '.join(ord_q_list)

    comparison = {'versus', 'vr', 'vs'}
    com_wrd = list(set(input_quest.split()) & comparison)
    # check if vs word present in input text
    if len(com_wrd) > 0:
        n = input_quest.find(com_wrd[0])
        text = input_quest[:n].split()[-1]
        # get all the categorical columns
        cat_cols = des_df[des_df['data_type'] == 'object']['column_names'].to_list()
        test = 0
        for col in cat_cols:
            # find the column used for comparison filter
            filter_list = whr.split(' and ')
            for fltr in filter_list:
                if (col in fltr.split()) & (text in fltr) & (col not in agg):
                    agg_list = agg.split(', ')
                    grp_list = grp.split(', ')
                    # add the corresponding column to aggregation query
                    for i, j in enumerate(agg_list):
                        if j not in cat_cols:
                            agg_list.insert(i, col)
                            grp_list.append(col)
                            break
                    agg = ', '.join(agg_list)
                    if len(grp_list[0]) > 1:
                        grp = ', '.join(grp_list)
                    else:
                        grp = ', '.join(grp_list[1:])
                    test = 1
                    break
            if test > 0:
                break
    # check for making proper query format
    if ('group by ' not in grp) & (len(grp) > 2):
        grp = 'group by ' + grp

    if ('order by ' not in ord) & (len(ord) > 2):
        ord = 'order by ' + ord

    return agg, grp, ord





