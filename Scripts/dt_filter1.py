
# load the libraries

import re
from datetime import datetime, timedelta
from datequarter import DateQuarter as DQ
from nltk import RegexpParser, RegexpTagger
from dateutil.relativedelta import relativedelta as rd


def get_hour(time_now, x, y):
    """
    Function to create time range for hours (next 5 hrs or past 5 hrs)

    :param time_now: current time
    :param x: parameter to decide current time or past time or future time
    :param y: parameter which tells the range (5 hrs or 9 hrs)
    :return: time range (start time and end time)
    """

    y = 1 if y < 2 else y

    # when it is current time
    if x == 0:
        st_t = end_t = time_now.strftime('%Y-%m-%d %H:00:00')
    # when it is future time
    elif x == 1:
        st_t = (time_now + timedelta(hours=1)).strftime('%Y-%m-%d %H:00:00')
        end_t = (time_now + timedelta(hours=y)).strftime('%Y-%m-%d %H:00:00')
    # when it is past time
    else:
        end_t = (time_now - timedelta(hours=1)).strftime('%Y-%m-%d %H:00:00')
        st_t = (time_now - timedelta(hours=y)).strftime('%Y-%m-%d %H:00:00')
    return st_t, end_t


def get_min(time_now, x, y):
    """
    Function to create time range for minutes (next 5 min or past 5 min)

    :param time_now: current time
    :param x: parameter to decide current time or past time or future time
    :param y: parameter which tells the range (5 min or 9 min)
    :return: time range (start time and end time)
    """

    y = 1 if y < 2 else y
    # when it is current time
    if x == 0:
        st_t = end_t = time_now.strftime('%Y-%m-%d %H:%M:00')
    # when it is future time
    elif x == 1:
        st_t = (time_now + timedelta(minutes=1)).strftime('%Y-%m-%d %H:%M:00')
        end_t = (time_now + timedelta(minutes=y)).strftime('%Y-%m-%d %H:%M:00')
    # when it is past time
    else:
        end_t = (time_now - timedelta(minutes=1)).strftime('%Y-%m-%d %H:%M:00')
        st_t = (time_now - timedelta(minutes=y)).strftime('%Y-%m-%d %H:%M:00')
    return st_t, end_t


def get_week(time_now, x):
    """
    Function to create time range for week (next 5 week or past 5 week)

    :param time_now: current time
    :param x: parameter to decide current time or past time or future time
    :return: time range (start time and end time)
    """

    # the values -1, 0 and 1 represents last, this and next
    if x == -1:
        n = -1 * (time_now.weekday()) + (-2)
        end_dt = time_now + timedelta(days=n)
        st_dt = (end_dt + timedelta(days=-6))
    elif x == 0:
        if time_now.weekday() == 6:
            st_dt, end_dt = time_now, (time_now + timedelta(days=6))
        else:
            # get the number of days to add (n)
            n = -1 * (time_now.weekday()) + (-1)
            st_dt = time_now + timedelta(days=n)
            end_dt = (st_dt + timedelta(days=6))
    else:
        # get the number of days to add (n)
        n = 7 - (time_now.weekday() + 1)
        st_dt = time_now + timedelta(days=n)
        end_dt = (st_dt + timedelta(days=6))
    return st_dt, end_dt


def get_quarter(now, x, y):
    """
    Function to create time range for quarters (next 5 quarter or past 5 quarter)

    :param time_now: current time
    :param x: parameter to decide current time or past time or future time
    :param y: parameter which tells the range (5 quarter or 9 quarter)
    :return: time range (start time and end time)
    """

    y = 1 if y == 0 else y
    if x == -1:  # last
        end_dt = (DQ.from_date(now) + x).end_date().strftime("%Y-%m-%d")
        st_dt = (DQ.from_date(now) + (x * y)).start_date().strftime("%Y-%m-%d")
    elif x == 1:  # next
        end_dt = (DQ.from_date(now) + (x * y)).end_date().strftime("%Y-%m-%d")
        st_dt = (DQ.from_date(now) + x).start_date().strftime("%Y-%m-%d")
    else:
        end_dt = (DQ.from_date(now) + x).end_date().strftime("%Y-%m-%d")
        st_dt = (DQ.from_date(now) + x).start_date().strftime("%Y-%m-%d")

    return st_dt, end_dt


def get_add_num(text, time_ents):
    """
    Function to appending numbers along with time based nlu ( last -> last 10)
    :param text: input text from user
    :param time_ents: entities of time related words (last, past, current, etc..)
    :return:
    """

    time_range = []
    for ent in time_ents:
        # get the end position of entities
        pos = ent.end_char
        # get the next string after the entity
        num = ','.join(text[pos:].split()).split(',')[0]
        # Mask the numbers
        text = ' '.join([len(num) * '*' if x == num else x for x in text.split(' ')])
        if num.isdigit():
            time_range.append(ent.text + ' ' + num)
        else:
            time_range.append(ent.text)
    return time_range, text


def make_time_qry_last_next(txt, default_dt, x, y=0):
    """
    Generate SQL query from using time phrases (last 10 days, this week, etc)

    :param txt: time text (can be day or week or month, etc)
    :param default_dt: (default date column name)
    :param x: parameter to decide current time or past time or future time
    :param y: parameter which tells the range (5 days, 10 months, etc)
    :return: SQL query
    """

    # Get current time
    now = datetime.now()

    # the parameter "txt" will vary (can be day or month or year, etc)
    # the values x can be 0 (current) or 1 (next) or -1 (past)
    result = ''
    if txt in ['day', 'days']:
        # decide the how many days to add or subtract from today
        y = x * y if y != 0 else x
        dt1 = (now + timedelta(days=x)).strftime("%Y-%m-%d")
        dt2 = (now + timedelta(days=y)).strftime("%Y-%m-%d")
        if x > 0: # x > 0 means next
            st_dt, end_dt = dt1, dt2
        else:
            st_dt, end_dt = dt2, dt1

        days = default_dt + ' between ' + "'" + st_dt + "' and '" + end_dt + "'"
        result = days

    elif txt in ['week', 'weeks']:
        st_dt, end_dt = get_week(now, x)
        if (y > 1) & (x > 0):
            dt_add = (y * 7) - 1
            end_dt = st_dt + timedelta(days=dt_add)
        elif x < 0:
            y = 1 if y == 0 else y
            dt_sub = (y * 7 * -1) + 1
            st_dt = end_dt + timedelta(days=dt_sub)
        st_dt, end_dt = st_dt.strftime("%Y-%m-%d"), end_dt.strftime("%Y-%m-%d")

        week = default_dt + ' between ' + "'" + st_dt + "' and '" + end_dt + "'"
        result = week

    elif txt in ['month', 'months']:
        y = y - 1 if y != 0 else y
        now_2 = now + rd(months=x)
        if x > 0:
            end_dt = ((now_2 + rd(months=y)) + rd(day=31)).strftime("%Y-%m-%d")
            st_dt = (now_2.replace(day=1)).strftime("%Y-%m-%d")
        elif x < 0:
            end_dt = (now_2 + rd(day=31)).strftime("%Y-%m-%d")
            st_dt = ((now_2 + rd(months=(y * -1))).replace(day=1)).strftime("%Y-%m-%d")
        else:
            st_dt, end_dt = (now_2.replace(day=1)).strftime("%Y-%m-%d"), (now_2 + rd(day=31)).strftime("%Y-%m-%d")

        month = default_dt + ' between ' + "'" + st_dt + "' and '" + end_dt + "'"
        result = month

    elif txt in ['quarter', 'quarters']:
        st_dt, end_dt = get_quarter(now, x, y)
        quarter = default_dt + ' between ' + "'" + st_dt + "' and '" + end_dt + "'"
        result = quarter

    elif txt in ['year', 'years']:
        y = 1 if y == 0 else y
        dt1, dt2 = str(now.year + (x * y)), str(now.year + x)
        if x > 0:
            st_dt, end_dt = dt2, dt1
        else:
            st_dt, end_dt = dt1, dt2

        year = 'year(' + default_dt + ') between ' + "'" + st_dt + "' and '" + end_dt + "'"
        result = year

    elif txt in ['decade', 'decades']:
        y = 1 if y < 2 else y
        if x == 0:
            current_year = 9-int(str(now.year)[-1])
            end_dt = now.year+current_year
            st_dt = end_dt-9
        elif x == 1:
            current_year = 9-int(str(now.year)[-1])
            end_dt = now.year+current_year+(y*10)
            st_dt = end_dt-((y*10)-1)
        else:
            current_year = 9-int(str(now.year)[-1])
            end_dt = (now.year+current_year)-10
            st_dt = end_dt-((y*10)-1)
        decade = 'year(' + default_dt + ') between ' + "'" + str(st_dt) + "' and '" + str(end_dt) + "'"
        result = decade

    elif txt in ['hour', 'hours']:
        st_dt, end_dt = get_hour(now,x,y)
        hour = default_dt + ' between ' + "'" + str(st_dt) + "' and '" + str(end_dt) + "'"
        result = hour

    elif txt in ['minute', 'minutes']:
        st_dt, end_dt = get_min(now,x,y)
        minute = default_dt + ' between ' + "'" + str(st_dt) + "' and '" + str(end_dt) + "'"
        result = minute

    return result


def get_dt_sqlquery(entity_list, text, default_dt):
    """
    Main function to generate SQL query for time phrases like today, yesterday, past 10 days, etc

    :param entity_list: entities identified from text
    :param text: input text
    :param default_dt: default date column
    :return: SQL query list, input text and time phrases list (last 10 days)
    """

    # Get the entities
    time_ents = [ent for ent in entity_list if (ent.label_ == 'dt_filter_3')]

    time_filter_qry_list, time_phrase_list = [], []
    # loop the time entities and generate the SQL query according to the key words
    for ent1 in time_ents:
        txt = ent1.text
        # generating sql query for today, tomorrow and yesterday
        if txt in ['yesterday', 'today', 'tomorrow']:
            time_phrase_list.append(txt)
            current_time = datetime.now()
            if txt == 'yesterday':
                ystrdy = (current_time + timedelta(days=-1)).strftime("%Y-%m-%d")
                time_filter_qry_list.append(default_dt + " = '" + ystrdy + "'")
            elif txt == 'today':
                tdy = current_time.strftime("%Y-%m-%d")
                time_filter_qry_list.append(default_dt + " = '" + tdy + "'")
            else:
                tmrw = (current_time + timedelta(days=1)).strftime("%Y-%m-%d")
                time_filter_qry_list.append(default_dt + " = '" + tmrw + "'")
        # generating sql query for last, current and next related times
        else:
            # Get the relevant time entities
            time_type = [ent for ent in entity_list if (ent.label_ == 'dt_filter_2')]
            # Add the number(range) near to time type if any
            new_time_nlu, text = get_add_num(text, time_type)
            # Loop both list in reverse order
            for ent2, tex in zip(time_type[::-1], new_time_nlu[::-1]):
                text_list = tex.split()
                try:
                    # Get the number and fix the cut of value
                    num, cut = int(text_list[1]), len(text_list[1]) + 3
                    time_phrase_list.append(ent2.text + ' ' + str(num) + ' ' + txt)
                except:
                    num, cut = 0, 3
                    time_phrase_list.append(ent2.text + ' ' + txt)

                if (ent2.end_char < ent1.start_char) & ((ent1.start_char - ent2.end_char) <= cut):
                    # Make the query based on the time word
                    if text_list[0] in ['last', 'past', 'previous']:
                        query = make_time_qry_last_next(txt, default_dt, -1 , num)
                        time_filter_qry_list.append(query)
                        break
                    elif text_list[0] in ['next', 'coming']:
                        query = make_time_qry_last_next(txt, default_dt, 1, num)
                        time_filter_qry_list.append(query)
                        break
                    elif text_list[0] in ['this', 'current']:
                        query = make_time_qry_last_next(txt, default_dt, 0, num)
                        time_filter_qry_list.append(query)
                        break

    if len(time_filter_qry_list) > 1:
        cond_1 = ' '.join(time_filter_qry_list[0].split()[:-1])
        cond_2 = time_filter_qry_list[1].split()[-1]
        time_filter_qry_list = [cond_1 + ' ' + str(cond_2)]
        time_phrase_list = time_phrase_list[:1]
    return time_filter_qry_list, text, time_phrase_list


def str_dt_convert(dt_chunk_list):
    """
    Function for converting string months(jan 10 2020 or 10 March 2020) into numbered month (2020-01-10 or 2020-03-10)

    :param dt_list: list contains chunks (jan 10 2020 or 10 March 2020)
    :return: Date list  (2020-01-10 or 2020-03-10)
    """

    dt_lis2 = []
    for dt_str in dt_chunk_list:
        split_dt = dt_str.split()
        elmnt_len = len(split_dt)
        dt_lis1 = []
        while elmnt_len > 2:
            split_dt_2 = split_dt[:3]
            split_dt = split_dt[3:]
            # when second element is alphabetical (10 jan 2020)
            if split_dt_2[1].isalpha():
                split_dt_2[1] = split_dt_2[1][:3]
                dt_string = ' '.join(split_dt_2)
                date_obj = datetime.strptime(dt_string, '%d %b %Y').strftime('%Y-%m-%d')
                dt_lis1.append(date_obj)
            # when first element is alphabetical (10 jan 2020)
            else:
                split_dt_2[0] = split_dt_2[0][:3]
                dt_string = ' '.join(split_dt_2)
                date_obj = datetime.strptime(dt_string, '%b %d %Y').strftime('%Y-%m-%d')
                dt_lis1.append(date_obj)
            elmnt_len = len(split_dt)
        # join all the converted dates and append to the list
        dt_lis2.append(' '.join(dt_lis1))

    return dt_lis2


def find_date(text):
    """
    Function to find out all the date formats from the input text and convert the identified date into common format
    :param text: Input text
    :return:
    """

    # Customize the Regex patterns to tag the string in the sentence
    wrd_list2 = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec', 'january',
                 'february', 'march', 'april', 'may', 'june', 'july', 'august', 'september', 'october', 'november',
                 'december']
    pattern_1 = [(i, 'MON') for i in wrd_list2]
    pattern_2 = [
        (r'[0-9]{2}/[0-9]{2}/[0-9]{4}', 'DT'),
        (r'[0-9]{4}/[0-9]{2}/[0-9]{2}', 'DT'),
        (r'[0-9]{2}-[0-9]{2}-[0-9]{4}', 'DT'),
        (r'[0-9]{4}-[0-9]{2}-[0-9]{2}', 'DT'),
        (r'[0-9]{4}', 'DT'),
        (r'[0-9]{2}', 'DT2'),
        (r'[0-9]{1}', 'DT2'),
        (r'and', 'CC'),
        (r'to', 'CC'),
        (r'[^0-9]', 'TXT'),
        (r'[0-9]', 'NUM')
    ]
    # Parse the patterns in regextagger
    patterns = pattern_1 + pattern_2
    regtg = RegexpTagger(patterns)

    # Regex pattern for filter out the specified consecutive words from the text
    grammar = r"""NP1: {(<MON><DT2><DT>)+<CC|TO>?(<MON><DT2><DT>)}
                      {(<MON><DT2><DT>)+<CC|TO>?(<DT2><MON><DT>)}
                      {(<DT2><MON><DT>)+<CC|TO>?(<MON><DT2><DT>)}
                      {(<DT2><MON><DT>)+<CC|TO>?(<DT2><MON><DT>)}
                      {(<MON><DT2><DT>)+<CC|TO>?(<MON><DT2><DT>)?}
                      {(<MON><DT2><DT>)+<CC|TO>?(<DT2><MON><DT>)?}
                      {(<DT2><MON><DT>)+<CC|TO>?(<MON><DT2><DT>)?}
                      {(<DT2><MON><DT>)+<CC|TO>?(<DT2><MON><DT>)?}
                  NP2: {(<MON><DT2>)+<CC|TO>?(<MON><DT2>)}
                      {(<MON><DT2>)+<CC|TO>?(<DT2><MON>)}
                      {(<DT2><MON>)+<CC|TO>?(<DT2><MON>)}
                      {(<DT2><MON>)+<CC|TO>?(<MON><DT2>)}
                      {(<MON><DT2>)+<CC|TO>?(<MON><DT2>)?}
                      {(<MON><DT2>)+<CC|TO>?(<DT2><MON>)?}
                      {(<DT2><MON>)+<CC|TO>?(<DT2><MON>)?}
                      {(<DT2><MON>)+<CC|TO>?(<MON><DT2>)?}
                  NP3: {<DT>+<CC|TO>?<DT>?}"""
    chunkParser = RegexpParser(grammar)
    # Get the chunks from the list
    tree = chunkParser.parse(regtg.tag(text.split()))

    # separating requires tags from the chunks and also finding their position in the text
    dt_chunk_list1, dt_chunk_list2, position_list1, position_list2 = [], [], [], []

    for subtree in tree.subtrees(filter=lambda t: t.label() in ['NP3', 'NP1']):
        word = " ".join([a for (a, b) in subtree.leaves()])
        pos = text.find(word)
        if pos < 1:
            pos = len(text)
        wrd_list = word.split()
        if (wrd_list[0].isalpha() == False) & (wrd_list[0].isdigit() == False):
            # Make the the chunk once it identified
            text = text[:pos] + ("*" * len(word)) + text[pos + len(word):]
            position_list1.append(pos)
            dt_chunk_list1.append(" ".join([num for num in word.split() if num not in ['and', 'to']]))

        elif (wrd_list[0].isdigit()) & (len(wrd_list[0]) == 4):
            # Check the word before the number
            previous_wrd = text[:pos].split()[-1]
            if previous_wrd in ['from', 'year', 'years', 'before', 'after']:
                # Make the the chunk once it is identified
                text = text[:pos] + ("*" * len(word)) + text[pos + len(word):]
                position_list1.append(pos)
                dt_chunk_list1.append(" ".join([num for num in word.split() if num not in ['and', 'to']]))
        else:
            text = text[:pos] + ("*" * len(word)) + text[pos + len(word):]
            position_list1.append(pos)
            dt_chunk_list2.append(" ".join([num for num in word.split() if num not in ['and', 'to']]))

    position_list3 = position_list1 + position_list2

    if len(dt_chunk_list2):
        dt_chunk_list2 = str_dt_convert(dt_chunk_list2)
    dt_chunk_list3 = dt_chunk_list1 + dt_chunk_list2

    # Converting them into one common date format
    dt_chunk_list4 = []
    if len(dt_chunk_list3) > 0:

        for dt_chunk in dt_chunk_list3:
            dt_list = []
            for dt in dt_chunk.split():
                if re.compile("[0-9]{2}/[0-9]{2}/[0-9]{4}").match(dt):
                    date = (datetime.strptime(dt, "%d/%m/%Y")).strftime("%Y-%m-%d")
                    dt_list.append(date)
                elif re.compile("[0-9]{4}/[0-9]{2}/[0-9]{2}").match(dt):
                    date = (datetime.strptime(dt, "%Y/%m/%d")).strftime("%Y-%m-%d")
                    dt_list.append(date)
                elif re.compile("[0-9]{2}-[0-9]{2}-[0-9]{4}").match(dt):
                    date = (datetime.strptime(dt, "%d-%m-%Y")).strftime("%Y-%m-%d")
                    dt_list.append(date)
                elif re.compile("[0-9]{4}-[0-9]{2}-[0-9]{2}").match(dt):
                    date = (datetime.strptime(dt, "%Y-%m-%d")).strftime("%Y-%m-%d")
                    dt_list.append(date)
                else:
                    # if there is no match in the above we can check whether it is year alone
                    dt_list.append(dt)
            dt_chunk_list4.append(' '.join(dt_list))

    return dt_chunk_list4, position_list3, text


def get_dt_filters(time_ents_list, pos, dt, cols_list1, cols_list2, st_loc_list, end_loc_list, default_dt, wrd,
                   term_df, t2_lis=[]):
    """
    Function to Generating NLUs for date filters

    :param time_ents_list: List contains entities
    :param pos: Position of particular chunk
    :param dt: date chunk list
    :param cols_list1: all date column name list
    :param cols_list2: Column name list which are present in input text
    :param st_loc_list: list contains starting location of each columns
    :param end_loc_list: list contains ending location of each columns
    :param default_dt: default column name
    :param wrd: default filter function when there is no filter function in time ents
    :param term_df: keyword data frame
    :param t2_lis: time phrase list
    :return: NLU
    """

    # Get the relevant time entities
    if len(t2_lis) > 0:
        time_ents_list_2 = [i for i in time_ents_list if i.text in t2_lis]
    else:
        time_ents_list_2 = time_ents_list.copy()

    time_nlu = []
    # making list in reverse order
    a, b, c = cols_list1[::-1], st_loc_list[::-1], end_loc_list[::-1]
    # number used for breaking loops when condition satisfied
    number = 0

    # if there is any time entities before the date, this loop will generate the NLU.
    for t_ent in time_ents_list_2[::-1]: # loop the time entities in reverse order

        if (t_ent.end_char < pos) & ((pos - t_ent.end_char) <= 10):
            t_func_1 = term_df[term_df['terms'] == t_ent.text]['functions'].iloc[0]
        else:
            t_func_1 = 'in'
        # loop the column and locations in reverse order and match with entities
        for col, st, ed in zip(a, b, c):
            # decide the cut value for the check
            cut = len(col) + 5 if t_ent.text == 'following' else 5
            if (t_ent.end_char < pos) & ((pos - t_ent.end_char) <= cut):
                # get the relevant function from the terms df
                t_func_2 = term_df[term_df['terms'] == t_ent.text]['functions'].iloc[0]
                cut_2 = 4 if t_ent.text == 'following' else len(t_ent.text)+4

                if (ed < pos) & (col in cols_list2) & ((pos - ed) <= cut_2):
                    time_nlu.append(col + ' ' + t_func_2 + " " + dt)
                    number, n = 1, end_loc_list.index(ed)
                    cols_list1.pop(n), st_loc_list.pop(n), end_loc_list.pop(n)
                    break

        if number != 0:
            break
        else:
            time_nlu.append(default_dt + ' ' + t_func_1 + " " + dt)
            number = 1
            break

    # This will loop will generate the NLU, when there is no entities before the date.
    if number == 0:
        for col, st, ed in zip(a, b, c): # Loop the columns
            if (ed < pos) & (col in cols_list2) & ((pos - ed) <= 10):
                time_nlu.append(col + wrd + dt)
                number, n = 1, end_loc_list.index(ed)
                cols_list1.pop(n), st_loc_list.pop(n), end_loc_list.pop(n)
                break
        if number == 0:
            time_nlu.append(default_dt + wrd + dt)

    return time_nlu


def get_dt_query_1(time_filter_list):
    """
    Function to generate SQl query from NLU phrases

    :param time_filter_list: List contains time NLUs (order from 2020)
    :return: Query list, Time NLU list 1 and 2
    """

    time_cond = time_filter_list.copy()
    time_query = []

    for nlu in time_filter_list:
        nl_list = nlu.split()
        # check if last element in list is digit
        if nl_list[-1].isdigit():
            if nl_list[1] == 'from':
                qry = 'year(' + nl_list[0] + ') >= ' + nl_list[-1]
                time_query.append(qry), time_cond.remove(nlu)
            elif nl_list[1] == 'till':
                qry = 'year(' + nl_list[0] + ') <= ' + nl_list[-1]
                time_query.append(qry), time_cond.remove(nlu)
            elif nl_list[1] == 'between':
                qry = 'year(' + nl_list[0] + ') between ' + nl_list[-2] + ' and ' + nl_list[-1]
                time_query.append(qry), time_cond.remove(nlu)
            else:
                qry = 'year(' + nl_list[0] + ') = ' + nl_list[-1]
                time_query.append(qry), time_cond.remove(nlu)

    return time_query, time_cond, time_filter_list


def get_dt_query_2(time_filter_list):
    """
    Function to generate SQl query from NLU phrases

    :param time_filter_list: List contains time NLUs (order from 12-12-2020)
    :return: Query list
    """

    time_query = []
    for nlu in time_filter_list:
        nl_list = nlu.split()

        if nl_list[1] == 'from':
            qry = nl_list[0] + " >= '" + nl_list[-1] + "'"
            time_query.append(qry)

        elif nl_list[1] == 'till':
            qry = nl_list[0] + " <= '" + nl_list[-1] + "'"
            time_query.append(qry)

        elif nl_list[1] == 'in':
            nl_2 = [k for k in nl_list if k not in ['not', 'in']]
            qry = nl_2[0] + ' in (' + ','.join(["'" + l + "'" for l in nl_2[1:]]) + ')'
            time_query.append(qry)

        elif nl_list[1] == 'not':
            nl_2 = [k for k in nl_list if k not in ['not', 'in']]
            qry = nl_2[0] + ' not in (' + ','.join(["'" + l + "'" for l in nl_2[1:]]) + ')'
            time_query.append(qry)

        elif nl_list[1] == 'between':
            x = nl_list[0] + ' between ' + ' and '.join(["'" + l + "'" for l in nl_list[2:]])
            time_query.append(x)

    return time_query


def get_dt_grpby(dt_nlu_list, default_dt):
    """
    Function to generate SQL query for groupby section

    :param dt_nlu_list: List contains time NLUs
    :return: SQL query
    """

    time_word_list = ['year', 'month', 'day', 'decade', 'years', 'months', 'days', 'decades', 'hour', 'hours',
                      'minutes', 'minute', 'quarter', 'quarters']

    # get the last word of first element in list
    first_nlu_wrd = dt_nlu_list[0].split()[-1]

    if first_nlu_wrd in time_word_list:
        if first_nlu_wrd in ['month', 'months']:
            grp_qry = 'datepart(MONTH,'+default_dt+') as months'

        elif first_nlu_wrd in ['hour', 'hours']:
            grp_qry = 'datepart(HOUR,' + default_dt + ') as hours'

        elif first_nlu_wrd in ['minute', 'minutes']:
            grp_qry = 'datepart(MINUTE,' + default_dt + ') as minutes'

        elif first_nlu_wrd in ['year', 'decade', 'years', 'decades']:
            grp_qry = 'datepart(YEAR,' + default_dt + ') as years'

        elif first_nlu_wrd in ['quarter', 'quarters']:
            grp_qry = 'datepart(QUARTER,' + default_dt + ') as quarters'

        else:
            grp_qry = 'datepart(DAY,' + default_dt + ') as days'
    else:
        if first_nlu_wrd.isdigit():
            grp_qry = 'datepart(YEAR,' + default_dt + ') as years'
        else:
            grp_qry = ''

    return grp_qry


def get_date_cond(text, nlu_ents_list, cols_list, st_loc_list, end_loc_list, des_df, term_df):
    """
    Main function to call all the above functions to make NLUs and SQL queries

    :param text:  Input text given by user
    :param nlu_ents_list: List contains entities
    :param cols_list: Column name list
    :param st_loc_list: List contains starting location of columns
    :param end_loc_list: List contains ending location of columns
    :param des_df: Descriptive data frame
    :param term_df: keyword data frame
    :return: filters list, SQL query list, input text, time NLUs, default date column name, and SQL query for group by
    """

    # Get default date column for time related filters
    try:
        default_dt = des_df[des_df['data_type'] == 'date']['column_names'].iloc[0]
    except Exception as e:
        default_dt = ''
    # get the dates and its positions from the text
    dt_chunk_list, dt_position, text = find_date(text)

    # take required entities from total entity list
    time_ents_1 = [ent for ent in nlu_ents_list if ent.label_ == 'dt_filter_1']
    time_ents_2 = [ent for ent in nlu_ents_list if ent.text in ['in', 'not', 'not in', 'is not', 'not equal']]
    time_ents = time_ents_1 + time_ents_2

    # Fetch all the date columns from the describe_df
    dt_cols = []
    for col_name in cols_list:
        d_type = des_df[des_df['column_names'] == col_name]['data_type'].iloc[0]
        if d_type == 'date':
            dt_cols.append(col_name)

    # loop for generating NLUs for all dates.
    time_filter_list1 = []
    for dt_chunk, pos in zip(dt_chunk_list, dt_position):
        cnt = len(dt_chunk.split())
        if cnt == 1:
            wrd = ' in '
            t_cond = get_dt_filters(time_ents, pos, dt_chunk, dt_cols, cols_list, st_loc_list, end_loc_list, default_dt, wrd,
                                    term_df, t2_lis=[])
            time_filter_list1 += t_cond
        elif cnt == 2:
            wrd = ' between '
            t2_lis = ['in', 'not', 'not in', 'following']
            t_cond = get_dt_filters(time_ents, pos, dt_chunk, dt_cols, cols_list, st_loc_list, end_loc_list, default_dt, wrd,
                                    term_df, t2_lis)
            time_filter_list1 += t_cond
        else:
            wrd = ' in '
            t2_lis = ['in', 'not', 'not in', 'following']
            t_cond = get_dt_filters(time_ents, pos, dt_chunk, dt_cols, cols_list, st_loc_list, end_loc_list, default_dt, wrd,
                                    term_df, t2_lis)
            time_filter_list1 += t_cond

    if len(time_filter_list1) > 0:
        # Function for generating SQL query from NLUs (when there is year alone)
        query_1, time_filter_list2, time_filter_list1 = get_dt_query_1(time_filter_list1)

        if len(time_filter_list2) > 0:
            # Function for generating SQL query from NLUs (When date specified)
            query_2 = get_dt_query_2(time_filter_list2)
            time_query_1 = query_1 + query_2
        else:
            time_query_1 = query_1
    else:
        time_query_1 = []

    # Function for generating SQL query (eg:last 5 days)
    time_query_2, text, dt_filter = get_dt_sqlquery(nlu_ents_list, text, default_dt)
    date_nlu = dt_filter + time_filter_list1

    if len(date_nlu)>0:
        date_nlu = [nlu for nlu in date_nlu if nlu not in ['yesterday', 'today', 'tomorrow']]
        if len(date_nlu) > 0:
            # Get group by query for the filter
            grp_qry = get_dt_grpby(date_nlu, default_dt)
        else:
            grp_qry = ''
    else:
        grp_qry = ''

    time_query = time_query_1 + time_query_2

    return time_filter_list1, time_query, text, dt_filter, grp_qry, default_dt