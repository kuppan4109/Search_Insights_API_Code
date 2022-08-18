
# load the libraries

from nltk import RegexpParser
from datetime import datetime, timedelta
from datequarter import DateQuarter as DQ
from dateutil.relativedelta import relativedelta as rd


def growth_cal_1(term_pre, growth_col, grby_col_1, dfault_dt):
    """
    Function to calculate growth percentage (MOM & YOY)

    :param term_pre: Term prefix (mom or yoy)
    :param growth_col: Column name specified for calculate growth
    :param grby_col_1: Column names which will be used to partition
    :param dfault_dt: default date column
    :return: SQL query, NLU and group by query
    """

    growth_nlu = []
    # check if it month over month or year over year
    if term_pre == 'y':
        growth_nlu.append('year over year ' + str(growth_col))
        grp_qry = 'year(' + dfault_dt + ') as years'
        grps = 'year(' + dfault_dt + ')'
        partionby_cols = grby_col_1
    else:
        growth_nlu.append('month over month ' + str(growth_col))
        grp_qry = 'year('+dfault_dt+') as years, month(' + dfault_dt + ') as months'
        grps = 'year('+dfault_dt+'), month(' + dfault_dt + ')'
        partionby_cols = ['year('+dfault_dt+')'] + grby_col_1

    groupby_cols = [grps] + grby_col_1

    if len(partionby_cols)>0:
        growth_qry= "format(((sum(" + growth_col + ") / convert(float, lag(sum(" + growth_col + ")) over( partition by " + ', '.join(partionby_cols) + " order by " + ','.join(groupby_cols) + ")))-1), 'p') as growth"
    else:
        growth_qry = "format(((sum(" + growth_col + ") / convert(float, lag(sum(" + growth_col + ")) over(order by " + ','.join(groupby_cols) + ")))-1), 'p') as growth"

    return growth_qry, grp_qry, growth_nlu


def growth_cal_2(term_pre, growth_col, grby_col_1, dfault_dt):
    """
    Function to calculate growth percentage (QOQ & WOW & DOD)

    :param term_pre: Term prefix
    :param growth_col: Column name specified for calculate growth
    :param grby_col_1: Column names which will be used to partition
    :param dfault_dt: default date column
    :return: SQL query, NLU and group by query
    """

    growth_nlu = []
    if term_pre == 'q':
        growth_nlu.append('quarter over quarter ' + str(growth_col))
        grp_qry = 'year('+dfault_dt+') as years, datepart(quarter,' + dfault_dt + ') as quarters'
        grps = 'year('+dfault_dt+'), datepart(quarter,' + dfault_dt + ')'

    elif term_pre == 'w':
        growth_nlu.append('week over week ' + str(growth_col))
        grp_qry = 'year('+dfault_dt+') as years, datepart(week,' + dfault_dt + ') as weeks'
        grps = 'year('+dfault_dt+'), datepart(week,' + dfault_dt + ')'

    else:
        growth_nlu.append('day over day ' + str(growth_col))
        grp_qry = 'year('+dfault_dt+') as years, month('+dfault_dt+') as months, datepart(day,' + dfault_dt + ') as days'
        grps = 'year('+dfault_dt+'), month('+dfault_dt+'), datepart(day,' + dfault_dt + ')'

    groupby_cols = [grps] + grby_col_1
    partionby_cols = ['year('+dfault_dt+')']+grby_col_1
    # Make growth qry using above
    growth_qry = "format(((sum(" + growth_col + ") / convert(float, lag(sum(" + growth_col + ")) over( partition by " + ', '.join(partionby_cols) + " order by " + ','.join(groupby_cols) + ")))-1), 'p') as growth"

    return growth_qry, grp_qry, growth_nlu


def get_growth(nlu_ents, agg_nlu, group_by, des_df):
    """
    Function to make growth calculation queries
    :param nlu_ents: Entity list
    :param agg_nlu: NLUs list for aggregation (eg:sum of sales)
    :param group_by: NLUs list for group by (eg: by category)
    :param des_df: descriptive data frame
    :return: SQL query, Growth NLU and group by qry
    """
    # Get growth terms
    growth_terms = [ent for ent in nlu_ents if ent.label_ == 'dt_filter_4']

    if len(growth_terms) > 0:
        # Get default date column for time related filters
        try:
            default_dt = des_df[des_df['data_type'] == 'date']['column_names'].iloc[0]
        except Exception as e:
            default_dt = ''
        # Get only one growth term
        growth_type = growth_terms[0]
        # Get only one numerical column for growth calculations
        growth_col = [col.split()[-1] for col in agg_nlu][0]
        # Get all the dimensions for for growth calculations
        groupby_cols = [col.split()[-1] for col in group_by]
        # Get prefix of growth term
        term_pre = str(growth_type)[0]

        if term_pre in ['y', 'm']:
            growth, dt_grpby, growth_nlu = growth_cal_1(term_pre, growth_col, groupby_cols, default_dt)
        else:
            growth, dt_grpby, growth_nlu = growth_cal_2(term_pre, growth_col, groupby_cols, default_dt)

        return growth, dt_grpby, [], growth_nlu
    else:
        return '', '', agg_nlu, []


def get_ago_filter(ent, num, default_dt):
    """
    Function find the time range and make sql query for filter like 5 month ago, 2 days ago

    :param ent: Entity
    :param num: number which will be used to calculate time range (5 days, 8 months)
    :param default_dt: default date column
    :return: SQL query
    """

    # Get the text (month or day or year, etc..)
    txt = ent.text[:2]
    # Get current date and time
    now = datetime.now()
    if txt == 'mi': # minutes
        time = now - timedelta(minutes=num)
        mini = time.strftime('%Y-%m-%d %H:%M:00')
        maxi = time.strftime('%Y-%m-%d %H:%M:59')
        filter = default_dt + " between '" + mini + "' and '" + maxi + "'"

    elif txt == 'ho':# hour
        time = now - timedelta(hours=num)
        mini = time.strftime('%Y-%m-%d %H:00:00')
        maxi = time.strftime('%Y-%m-%d %H:59:59')
        filter = default_dt + " between '" + mini + "' and '" + maxi + "'"

    elif txt == 'da':
        time = now - timedelta(hours=num)
        mini = time.strftime('%Y-%m-%d 00:00:00')
        maxi = time.strftime('%Y-%m-%d 23:59:59')
        filter = default_dt + " between '" + mini + "' and '" + maxi + "'"

    elif txt == 'mo':
        time = now - rd(months=num)
        month, year = time.month, time.year
        filter = "month(" + default_dt + ") = " + str(month) + ' and ' + "year(" + default_dt + ") = " + str(year)

    elif txt == 'we':
        time = (now - timedelta(weeks=num)).date()
        weekday = time.isoweekday()
        start = time - timedelta(days=weekday)
        dates = ', '.join(["'" + str(start + timedelta(days=d)) + "'" for d in range(7)])
        filter = default_dt + " in (" + dates + ")"

    elif txt == 'qu':
        mini = (DQ.from_date(now) - num).start_date().strftime("%Y-%m-%d")
        maxi = (DQ.from_date(now) - num).end_date().strftime("%Y-%m-%d")
        filter = default_dt + " between '" + mini + "' and '" + maxi + "'"

    elif txt == 'ye':
        year = (now.year - num)
        filter = "year(" + default_dt + ") = " + str(year)

    else:
        filter = ''

    return filter


def func_ago(nlu_ents, text, des_df):
    """
    Main function for ago filter

    :param nlu_ents: list of entities
    :param text: input text
    :param des_df: descriptive data frame
    :return: SQL query for filter, text and entities
    """

    try:
        default_dt = des_df[des_df['data_type'] == 'date']['column_names'].iloc[0]
    except Exception as e:
        default_dt = ''
    # Get required entities
    time_ent1 = [ent for ent in nlu_ents if ent.label_ == 'dt_filter_7']
    # Get the entities like mont, year, day
    time_ent2 = [ent for ent in nlu_ents if (ent.label_ == 'dt_filter_3') & (ent.text not in ['yesterday', 'today', 'tomorrow'])]

    filter = ''
    if len(time_ent1) > 0:
        # ago entity
        ent1 = time_ent1[0]
        for ent2 in time_ent2:
            if abs(ent1.start_char - ent2.end_char) < 3:
                # Get the position
                pos = ent2.start_char - 1
                # Get the preview word from the text and check whether it is number
                text1 = text[:pos].split()[-1]
                if text1.isdigit():
                    pos2 = pos - len(text1)
                    text = text[:pos2] + '*' * len(text1) + text[pos:]
                    num = int(text1)
                else:
                    num = 1
                # remove identified entities from entity list
                nlu_ents.remove(ent1), nlu_ents.remove(ent2)
                # Get the filter
                filter = get_ago_filter(ent2, num, default_dt)

    return [filter], nlu_ents, text


def get_single_key_dt_filter(nlu_ents, default_dt):
    """
    Function which used to filter like jan sales or sundays revenue

    :param nlu_ents: entity list
    :param default_dt: default date column
    :return: SQL query list for filter
    """

    # Get the entities
    ent_list = [ent for ent in nlu_ents if ent.label_ in ['month', 'day', 'quarter']]

    if len(ent_list) > 0:
        key = ent_list[0]
        label = key.label_
        text = key.text

        if label == 'month':
            txt = text[:3]
            month_dict = {'jan': 'january', 'feb': 'february', 'mar': 'march', 'may': 'may', 'jun': 'june',
                          'jul': 'july', 'aug': 'august', 'sep': 'september', 'oct': 'october', 'nov': 'november',
                          'dec': 'december'}
            condtion1 = "datename(month, " + default_dt + ") = '" + month_dict[txt] + "'"

        elif label == 'day':
            txt = text[:3]
            day_dict = {'sun': 'sunday', 'mon': 'monday', 'tue': 'tuesday', 'wed': 'wednesday', 'thu': 'thursday',
                        'fri': 'friday', 'sat': 'saturday'}
            condtion1 = "datename(weekday, " + default_dt + ") = '" + day_dict[txt] + "'"

        else:
            txt = text[-1]
            if txt.isdigit():
                condtion1 = "datename(quarter, " + default_dt + ") = " + txt
            else:
                txt = text.split()[-1]
                quarter_dict = {'one': '1', 'two': '2', 'three': '3', 'four': '4'}
                condtion1 = "datename(quarter, " + default_dt + ") = " + str(quarter_dict[txt])

        condtion2 = "year(" + default_dt + ") = year(getdate())"
        contion = [condtion1, condtion2]

        return contion
    else:
        return []


def get_to_date(nlu_ents, aggregations, group_by, deflt_dt):
    """
    This function is to calculate function like Month to date, year to date etc.
    """

    # filter the relevant entities
    global groups_col, td_col
    todate_terms = [ent.text for ent in nlu_ents if ent.label_ == 'dt_filter_6']

    # loop the entities and make the query
    if len(todate_terms) > 0:
        todate_list, keys = [], []
        for ent in todate_terms:
            td = ent
            td_col = aggregations[0].split()[-1]
            groups_col = ' ,'.join([i.split()[-1].strip() for i in group_by])
            # Month to date
            if td[0] == 'm':
                if len(groups_col) > 2:
                    filter = "SUM(" + td_col + ") OVER (PARTITION BY year(" + deflt_dt + ") , month(" + deflt_dt + "), " + groups_col + " order by " + deflt_dt + " rows between unbounded preceding and current row) as MTD"
                else:
                    filter = "SUM(" + td_col + ") OVER (PARTITION BY year(" + deflt_dt + ") , month(" + deflt_dt + ") order by " + deflt_dt + " rows between unbounded preceding and current row) as MTD"
                keys.append('MTD')
            # Quarter to date
            elif td[0] == 'q':
                if len(groups_col) > 2:
                    filter = "SUM(" + td_col + ") OVER (PARTITION BY year(" + deflt_dt + ") , datepart(quarter, " + deflt_dt + "), " + groups_col + " order by " + deflt_dt + " rows between unbounded preceding and current row) as QTD"
                else:
                    filter = "SUM(" + td_col + ") OVER (PARTITION BY year(" + deflt_dt + ") , datepart(quarter, " + deflt_dt + ") order by " + deflt_dt + " rows between unbounded preceding and current row) as QTD"
                keys.append('QTD')
            # year to date
            else:
                if len(groups_col) > 2:
                    filter = "SUM(" + td_col + ") OVER (PARTITION BY year(" + deflt_dt + "), " + groups_col + " order by " + deflt_dt + " rows between unbounded preceding and current row) as YTD"
                else:
                    filter = "SUM(" + td_col + ") OVER (PARTITION BY year(" + deflt_dt + ") order by " + deflt_dt + " rows between unbounded preceding and current row) as YTD"
                keys.append('YTD')

            todate_list.append(filter)

        to_date = ', '.join(todate_list)
        # Make select section based on available info
        if len(groups_col) > 2:
            to_date = deflt_dt + ', ' + groups_col + ', ' + td_col + ', ' + to_date
        else:
            to_date = deflt_dt + ', ' + td_col + ', ' + to_date

        return to_date, keys

    else:
        return '', []


def get_dt_intervals(nlu_ents, deflt_dt):
    """ Function which helps to group the aggregates using date column for the functions like
    day of week, day of year, quarter of year, etc.."""

    # Get the specified label's terms from NER model
    dt_intervals = [ent.text for ent in nlu_ents if ent.label_ == 'dt_filter_9']

    if len(dt_intervals) > 0:
        grp_list = []
        # take one functionality alone ex: day of week or month of year
        dt_intervals = dt_intervals[0]
        terms_list = dt_intervals.split()
        # Remove of from the list
        terms_list.remove('of')
        for term in terms_list:
            if (term == 'day') & (terms_list[1] == 'week'):
                grp_list.append("datename(weekday," + deflt_dt + ") as weekdays")
            elif term == 'hour':
                grp_list.append("datepart(hour," + deflt_dt + ") as hours")
            elif term == 'day':
                grp_list.append("datepart(day," + deflt_dt + ") as days")
            elif term == 'week':
                grp_list.append("datepart(week," + deflt_dt + ") as weeks")
            elif term == 'month':
                grp_list.append("datepart(month," + deflt_dt + ") as months")
            elif term == 'quarter':
                grp_list.append("datepart(quarter," + deflt_dt + ") as quarters")
            else:
                grp_list.append("datepart(year," + deflt_dt + ") as years")
        # Join the list in reverse order
        grps = ', '.join(grp_list[::-1])
        # split the grouping queries by "as" and then add in order by clause
        orders = ', '.join([i.split(' as ')[0] for i in grp_list[::-1]])
    else:
        grps, orders = '', ''
    return grps, orders


def get_weekday_interval(text, tagger, default_dt):
    """
    Function which helps to filter "like sunday to wednesday sales" and we use custom pos-tag to achieve this
    :param text: input text
    :param tagger: customized tagger
    :param default_dt: default date column name
    :return: input text and filter query
    """

    # Replace the coma and split the text and rejoin
    text = " ".join(text.replace(",", " ").split()).lower()
    # Define the pattern to split the chunks
    grammar = "NP: {<DAY><:|TO|DAY><DAY>}"
    chunkParser = RegexpParser(grammar)
    # Get the POS tags from each words
    tree = chunkParser.parse(tagger.tag(text.split()))
    dt_fill_chunk = []

    # Split the chunks from tags and mask the identified chunks
    for subtree in tree.subtrees(filter=lambda t: t.label() == 'NP'):
        word = " ".join([a for (a, b) in subtree.leaves()])
        dt_fill_chunk.append(" ".join([num for num in word.split()]))
    if len(dt_fill_chunk) > 0:
        for i in dt_fill_chunk:
            k = "*" * len(i)
            text = text.replace(i, k)

        # find the start day and end day and get the date of those days
        filter_wrd = dt_fill_chunk[0]
        filter_wrd_lst = filter_wrd.split()
        start_day = filter_wrd_lst[0][:3]
        end_day = filter_wrd_lst[-1][:3]

        # Find the correct day and get the corresponding intervals
        today = datetime.today()
        week_day = today.strftime("%A").lower()[:3]
        # Loop for getting start date
        while week_day != start_day:
            today = today - timedelta(days=1)
            week_day = today.strftime("%A").lower()[:3]

        start_date = today.strftime("%Y-%m-%d")
        day = today.strftime("%A").lower()
        days = ["'" + day + "'"]

        # Loop to get end date
        for n in range(7):
            today = today + timedelta(days=1)
            week_day = today.strftime("%A").lower()[:3]
            day = today.strftime("%A").lower()
            days.append("'" + day + "'")
            if week_day == end_day:
                end_date = today.strftime("%Y-%m-%d")
                break
        # Make SQL query from using dates
        condition = ["datename(weekday,"+default_dt + ") in (" + ", ".join(days) + ")"]
    else:
        condition = []
    return text, condition


def make_dt_grps(nlu_ents, default_dt):
    """
    This function helps to create time interval queries (monthly sales, weekly profit)
    """

    # filter the relevant entities
    time_grps = [ent.text.replace('by ', '') for ent in nlu_ents if ent.label_ in ['dt_filter_5', 'dt_filter_3']]
    select_section, group_section, keys = [], [], []

    # loop the entities and generate query according to the time type
    for time in time_grps:
        if time in ['day', 'days', 'daily']:
            select_query = 'datepart(DAY,' + default_dt + ') as days'
            grp_query = 'datepart(DAY,' + default_dt + ')'
            keys.append('days')

        elif time in ['week', 'weeks', 'weekly']:
            select_query = 'datepart(WEEK,' + default_dt + ') as weeks'
            grp_query = 'datepart(WEEK,' + default_dt + ')'
            keys.append('weeks')

        elif time in ['month', 'months', 'monthly']:
            select_query = 'datepart(MONTH,' + default_dt + ') as months'
            grp_query = 'datepart(MONTH,' + default_dt + ')'
            keys.append('months')

        elif time in ['quarter', 'quarters', 'quarterly']:
            select_query = 'datepart(QUARTER,' + default_dt + ') as quarters'
            grp_query = 'datepart(QUARTER,' + default_dt + ')'
            keys.append('quarters')

        elif time in ['year', 'years', 'yearly']:
            select_query = 'datepart(YEAR,' + default_dt + ') as years'
            grp_query = 'datepart(YEAR,' + default_dt + ')'
            keys.append('years')

        else:
            select_query = ''
            grp_query = ''
        # check if there any time interval created, if any append to select section
        if len(select_query) > 1:
            select_section.append(select_query)
            group_section.append(grp_query)

    return group_section, select_section, keys


def convert_dates_to_text(df):
    """
    Function to convert numerical representation of time intervals into textual representation
    """

    # Get all the columns from the df
    col_list = list(df.columns)
    for col in col_list:
        if col in ['months', 'weeks', 'days', 'quarters']:
            if col == 'weeks':
                df[col] = df[col].apply(lambda x: 'Week ' + str(x))
            elif col == 'days':
                df[col] = df[col].apply(lambda x: 'Day ' + str(x))
            elif col == 'quarters':
                df[col] = df[col].apply(lambda x: 'Q' + str(x))
            else:
                month_dict = {'1': 'Jan', '2': 'Feb', '3': 'Mar', '4': 'Apr', '5': 'May', '6': 'Jun', '7': 'Jul',
                              '8': 'Aug', '9': 'Sep', '10': 'Oct', '11': 'Nov', '12': 'Dec'}
                df[col] = df[col].apply(lambda x: month_dict[str(x)])
    return df