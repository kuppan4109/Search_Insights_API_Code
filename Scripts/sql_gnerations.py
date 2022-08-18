
# load the required modules

from functions import *
from dt_filter1 import *
from dt_filter2 import *
# from date_filters import *
from new_functionalities import *
from having_functions import get_having


def text_to_sql(input_text, nlu_mod, des_df, term_df, tagger, level_dict, df_cols_as, skip_keys, table_name):
    """
    This is the main function which will call all the sub functions to create NLU and generate proper SQL query based
    on the information available in Input text (given by user)

    :param input_text: Text or Question give by user
    :param nlu_mod: NLP model which will identify all the trained keywords from the input text
    :param des_df: Descriptive statistics of table
    :param term_df: Data frame which contains all the keywords
    :param tagger: Customized Part of speech tagger
    :param level_dict: Dictionary which contains all the levels or values of each categorical attributes
    :param df_cols_as: Data frame which contains alias names for all the attributes
    :param skip_keys: List contains all the unwanted words and symbols which will be removed from the input text
    :param table_name: Name of the table in SQL DB
    :return: SQL query
    """

    # Text cleaning
    input_quest = input_text
    input_text = txt_clean(input_text, skip_keys)

    # Get all the attributes and its location in text
    cols_list, start_loc, end_loc, input_text = get_attributes(input_text, df_cols_as)

    col_list_title = cols_list.copy()
    columns, end_locations = cols_list.copy(), end_loc.copy()

    # Get the entities from the text
    nlu_ents = list(nlu_mod(input_text).ents)
    nlu_ents_copy = nlu_ents.copy()

    # Get the aggregations and remove the columns used for aggregation
    agg_nlu, attri_ents, agg_end_loc = find_aggregation(nlu_ents, cols_list, start_loc, end_loc, des_df, term_df)

    # Get the grouping phrases
    grpby_cols, attri_ents = find_grouby(nlu_ents, attri_ents)

    # Get sorting
    top_bot, sort, input_text = top_botom_sort(input_text, tagger, attri_ents, nlu_ents, des_df, agg_nlu)

    # Get having filters
    input_text, nlu_ents, h_cond, h_con_nlu, agg_nlu = get_having(agg_nlu, agg_end_loc, nlu_ents, term_df, input_text)

    # Get ago filters
    ago_filter, nlu_ents, input_text = func_ago(nlu_ents, input_text, des_df)

    # Get the date filters
    time_filter_nlu, time_query, input_text, dt_nlu, time_grp_qry1, default_dt = get_date_cond(input_text, nlu_ents, cols_list,
                                                                                     start_loc, end_loc, des_df,term_df)
    input_text, wk_day_filter = get_weekday_interval(input_text, tagger, default_dt)

    # Get new Entities from the rest of input text and use it for rest of functionalities
    nlu_ents = list(nlu_mod(input_text).ents)

    # Get group by query for time related phrases if any
    group_section, select_section, keys_2 = make_dt_grps(nlu_ents, default_dt)

    # Get single key date filters (jan sales or profit in sundays)
    key_dt_filter = get_single_key_dt_filter(nlu_ents, default_dt)

    # Get the number and string filters (sales in "new york" or sales by region where profit is above 100)
    filter_nlu, cols_list, end_locations = find_filters(input_text, nlu_ents, nlu_ents_copy, attri_ents, des_df,
                                                        term_df, level_dict, tagger)
    # Get the null or empty filters
    null_queries, cols_list = get_null(nlu_ents, cols_list, end_locations, default_dt)

    # Assign default aggregation to attributes which is not part of any above functions
    if len(cols_list) > 0:
        nlu_user, nlu_query = get_deflt_agg(cols_list, des_df)
    else:
        nlu_user, nlu_query = [], []

    NLUs = agg_nlu + nlu_query + grpby_cols
    group_by = [i for i in NLUs if str(i)[:2] == 'by']

    # Get cumulative aggregation functions
    groups = group_by.copy()
    groups = [i.replace('by ', '') for i in groups] + group_section

    # Get the cumulative aggregation functions (eg: running total for sales)
    cum_agg_list, cols_list, keys = get_cumulative_agg(nlu_ents, groups, cols_list, start_loc, des_df)

    if len(cols_list) > 0:
        nlu_user, nlu_query = get_deflt_agg(cols_list, des_df)
    else:
        nlu_user, nlu_query = [], []

    # Get growths
    NLUs = agg_nlu + nlu_query + grpby_cols
    aggregations = [i for i in NLUs if str(i)[:2] != 'by']
    group_by = [i for i in NLUs if str(i)[:2] == 'by']

    growth, dt_grpby, aggregations, growth_nlu = get_growth(nlu_ents, aggregations, group_by, des_df)

    # Get To date functionalities (month to date)
    to_date_condtion, title_key = get_to_date(nlu_ents, aggregations, group_by, default_dt)
    keys = keys + title_key

    nlu_query = aggregations + group_by + filter_nlu
    nlu_user = top_bot + aggregations + group_by + filter_nlu + sort + time_filter_nlu + dt_nlu + h_con_nlu + growth_nlu

    # Get the default title for output from NLUs and Keys
    title = create_title(aggregations + keys, group_by, col_list_title, keys_2, growth_nlu)

    # Remove underscore from the colum names for showing NLUs to user
    nlu_user = [i.replace('_', ' ') for i in nlu_user]

    # Convert NL phrases into sql functions (averae of sales -> avg(sales) as average_of_sales)
    agg_sql_qry, filter_qry, grp_sql_qry = nlg(nlu_query)

    # Get share & percentage Query
    agg_sql_qry, grp_sql_qry = get_share(columns, start_loc, agg_sql_qry, grp_sql_qry, filter_nlu, nlu_ents, des_df)

    # Get first day of month or last day of month aggregations query
    agg_sql_qry, grp_sql_qry, orderby1 = get_dt_filter_day_to_month(agg_sql_qry, grp_sql_qry, nlu_ents, default_dt)

    # Get query for functions like monthly sales yearly profit
    grp_sql_qry_2, orderby2 = get_dt_intervals(nlu_ents_copy, default_dt)

    if (len(orderby2) > 3) & (len(orderby1) > 3):
        order_by = orderby2 + ', ' + orderby1
    elif len(orderby1) > 3:
        order_by = orderby1
    else:
        order_by = orderby1

    if (len(grp_sql_qry) < 1) & (len(time_grp_qry1) > 1):
        grp_sql_qry = time_grp_qry1

    # check all the time related filters, if there are more than one similar filters then take proper decision
    loop_list = [filter_qry] + time_query + ago_filter + wk_day_filter + null_queries
    if len(loop_list) > 0:
        wrd = ' and '.join([i for i in loop_list if len(i) > 8])
        if 'year' in wrd:
            loop_list = loop_list + key_dt_filter[:1]
        else:
            loop_list = loop_list + key_dt_filter

        filter_qry = ' and '.join([i for i in loop_list if len(i) > 8])
    else:
        filter_qry = ''

    # Choose final sorting column
    sort, top_bot, agg_sql_qry, grp_sql_qry = chse_sort_top(sort, top_bot, agg_sql_qry, grp_sql_qry)

    # When growth related function and aggregation function both are present combine both of them for select section
    if len(growth) > 1:
        agg_sql_qry = ', '.join([agg_sql_qry] + [growth]) if len(agg_sql_qry) > 1 else growth
        grp_sql_qry = ', '.join([dt_grpby] + [grp_sql_qry]) if len(grp_sql_qry) > 1 else dt_grpby

    # When cumulative function and aggregation function both are present combine both of them for select section
    if len(cum_agg_list) > 0:
        if len(agg_sql_qry) > 1:
            agg_sql_qry = agg_sql_qry + ', ' + ', '.join(cum_agg_list)
        else:
            agg_sql_qry = ', '.join(cum_agg_list)

    # make proper select section queries
    if len(select_section) > 0:
        if len(grp_sql_qry) > 1:
            grp_sql_qry = ', '.join(select_section) + ', ' + grp_sql_qry
        else:
            grp_sql_qry = ', '.join(select_section)

    # parameter to make proper group by order by when cumulative functions is presetn
    cumulate = 1 if len(cum_agg_list) > 0 else 0
    cumulate = 2 if len(select_section) > 0 else cumulate

    # Decide final order by section
    if (len(sort) > 2) & (len(order_by) > 2):
        sort = sort + ', ' + order_by
    elif len(sort) > 2:
        sort = sort
    else:
        sort = order_by

    # Decide final group by section
    if len(grp_sql_qry) > 2:
        if len(grp_sql_qry_2) > 2:
            grp_sql_qry = grp_sql_qry + ', ' + grp_sql_qry_2
    else:
        if len(grp_sql_qry_2) > 2:
            grp_sql_qry = grp_sql_qry_2

    # When to date functions (month to date or year to date) present change all the section again to get proper output
    if len(to_date_condtion) > 10:
        agg_sql_qry = to_date_condtion
        cumulate = grp_sql_qry = top_bot = sort = ''
        title = 'To date functions'

    # remove repeating aggregations
    agg_sql_qry, grp_sql_qry = remove_duplicate(agg_sql_qry, grp_sql_qry)
    # Generate query
    query = query_generate(table_name, top_bot, agg_sql_qry, filter_qry, grp_sql_qry, sort, h_cond, cumulate, input_quest, des_df)

    return query, nlu_user, title

