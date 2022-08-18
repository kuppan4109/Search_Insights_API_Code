# Load the libraries

import nltk
import spacy
import joblib
import pyodbc
import configparser
import pandas as pd
from spacy.tokens import Span
from nltk.corpus import wordnet
from inflect import engine as en
from nltk.stem import WordNetLemmatizer
from spacy.matcher import PhraseMatcher


def get_alias_for_attributes(df, out_path):
    """
    This functions used to generate multiple alias for each attribute.

    :param df: Data
    :param out_path: output path for saving alias df
    """

    # Get the column names from the df
    col_list = df.columns.to_list()
    alias_df = pd.DataFrame(columns=["alias", "columns"])

    lemma = WordNetLemmatizer()
    # loop the columns
    for col in col_list:
        col = col.lower()
        # add same column names as alias name for all the column
        alias_df.loc[len(alias_df)] = [col, col]
        # split column name with "_"
        col_split = col.split("_")
        if len(col_split) == 1:
            # Add more synonyms for attributes
            syn = list()
            for synset in wordnet.synsets(str(col)):
                for lem in synset.lemmas():
                    syn.append(lem.name())
            # check if there any synonyms for the column name, if any get first 5 from the list
            if len(syn) > 0:
                syn = list(set(syn))
                for alias in syn[:6]:
                    alias_df.loc[len(alias_df)] = [alias, col]
            # add the root word of attribute
            lem_wrd = lemma.lemmatize(col)
            if lem_wrd != col:
                alias_df.loc[len(alias_df)] = [lem_wrd, col]
            # add plural of the word
            pos = nltk.pos_tag([col])[0][1]
            if (en().singular_noun(col) is False) & (pos != 'VBG'):
                alias_df.loc[len(alias_df)] = [en().plural(col), col]
        # when the attribute name has 2 words
        elif len(col_split) == 2:
            alias_df.loc[len(alias_df)] = [" ".join(col_split), col]
            alias_df.loc[len(alias_df)] = [" ".join([col_split[1], col_split[0]]), col]
            alias_df.loc[len(alias_df)] = [" of ".join([col_split[1], col_split[0]]), col]
        # when the attribute name has 3 words
        elif len(col_split) == 3:
            alias_df.loc[len(alias_df)] = [" ".join(col_split), col]
            alias_df.loc[len(alias_df)] = [" ".join([col_split[1], col_split[0], col_split[2]]), col]
            alias_df.loc[len(alias_df)] = [" ".join([col_split[2], col_split[1], col_split[0]]), col]
            alias_df.loc[len(alias_df)] = [" ".join(col_split[:2]), col]
        # when the attribute name has more than 3 words
        else:
            alias_df.loc[len(alias_df)] = [" ".join(col_split), col]
            alias_df.loc[len(alias_df)] = [" ".join(col_split[:2]), col]

    # calculate the count of words and save it as column (will be used for sorting)
    alias_df['len'] = alias_df['alias'].apply(lambda x: len(x.split()))
    alias_df.sort_values(by='len', ascending=False, inplace=True)
    alias_df.drop_duplicates(subset=['alias'], keep="first", inplace=True)
    # save the alias data frame in local
    alias_df.drop(['len'], axis=1).to_csv(out_path + 'alias_df.csv', index=False)


def get_col_level(df, out_path):
    """
    Function used to take out the unique levels from each categorical columns

    :param df: Data
    :param out_path: output path to save the dictionary
    """
    # create level dictionary only for categorical columns
    df_2 = pd.DataFrame(columns=['attributes', 'unique_cnt'])
    for col_name in df.columns:
        # choose only categorical columns
        if df[col_name].dtype not in ['int64', 'int32', 'float', '<M8[ns]']:
            n = len(df[col_name].unique())
            df_2.loc[len(df_2)] = [col_name, n]
    df_2.sort_values(by='unique_cnt', inplace=True)
    # save all the levels in dictionary
    my_dict = {}
    for col in df_2.attributes:
        lev_list = list(df[col].unique())
        if len(lev_list) < len(df):
            my_dict[col] = lev_list
    # dump the dictionary to local as pkl file
    joblib.dump(my_dict, out_path + 'level_dict.pkl')


def get_descriptive(df, out_path):
    """
    This function used for generating partial descriptive statistics of data.
    :param df:
    :param out_path:
    """

    d_type, default_agg = [], []
    for col_name in df.columns:
        # set average as default aggregation for numeric attributes
        if df[col_name].dtype in ['int64', 'int32', 'float']:
            d_type.append('numeric')
            default_agg.append('average')
        elif df[col_name].dtype == '<M8[ns]':
            d_type.append('date')
            default_agg.append('by')
        else:
            # set by as default aggregation for categorical attributes
            d_type.append('object')
            default_agg.append('by')
    # get descriptive statistics of df
    des_df = df.describe(include='all').T[['unique', 'min', 'mean', 'max']].fillna(0)
    des_df.insert(loc=0, column='column_names', value=des_df.index.to_list())
    # add default agg column and data type column
    des_df['data_type'] = d_type
    des_df['default_agg'] = default_agg
    des_df.to_csv(out_path + 'des_df.csv', index=False)


class EntityMatch(object):
    """
    Class for creating custom Name Entity Recognition
    """

    name = "custom_ner"

    def __init__(self, nlp, terms, label):
        patterns = [nlp.make_doc(text) for text in terms]
        self.matcher = PhraseMatcher(nlp.vocab)
        self.matcher.add(label, None, *patterns)

    def __call__(self, doc):
        matches = self.matcher(doc)
        seen_tokens = set()
        new_entities = []
        entities = doc.ents
        for match_id, start, end in matches:
            if start not in seen_tokens and end - 1 not in seen_tokens:
                new_entities.append(Span(doc, start, end, label=match_id))
                entities = [e for e in entities if not (e.start < end and e.end > start)]
                seen_tokens.update(range(start, end))

        doc.ents = tuple(entities) + tuple(new_entities)
        return doc


def train_agg_and_grp(model_path, data_path):
    """
    Function to train NLU model (which will identify filter and aggregation phrases in the input text)

    :param model_path: model path to save the model
    :param data_path: data path to fetch data
    """
    # Load the key words df
    df = pd.read_csv(data_path + 'train_ner.csv')
    # load the spacy's nlp model
    nlu_mod = spacy.load("en_core_web_sm", disable=["tagger", "parser", "ner"])
    # train the nlp model with our custom keywords
    for n, i in enumerate(df.label.unique()):
        key_words_list, label = df[df['label'] == i]['key_words'].to_list(), i
        entity = EntityMatch(nlu_mod, key_words_list, label)
        entity.name = entity.name + '_' + str(n + 1)
        if n == 0:
            nlu_mod.add_pipe(entity)
        else:
            nlu_mod.add_pipe(entity, after='custom_ner_' + str(n))
    joblib.dump(nlu_mod, model_path + 'nlu_mod.pkl')  # save the trained model in local


def dtype_convert(df, cols):
    """ This function used to convert mentioned numerical column's data type into object type """

    dict1 = dict()
    for col in cols:
        dict1[str(col).strip()] = 'object'
    df = df.astype(dict1)
    return df


def main():
    """
    Main function to perform all the actions
    """

    # Read configuration file
    config = configparser.RawConfigParser()
    try:
        config.read('config.txt')
    except Exception as e:
        print(str(e))
    try:
        data_path = config.get('paths', 'data_path')
        model_path = config.get('paths', 'model_path')
        file = config.get('file', 'data_name')
        d_type = config.get('file', 'data_type')
        cols_convert = config.get('file', 'cols_convert')
        server = config.get('database', 'IP')
        db = config.get('database', 'DB')
        un = config.get('database', 'UN')
        pwd = config.get('database', 'PWD')
        table = config.get('table', 'table_name')
    except Exception as e:
        print(e)
        print('Not able to load configuration file..')

    # load the data
    try:
        df = pd.read_excel(data_path + file + '.' + d_type, encoding='latin-1')
    except:
        try:
            df = pd.read_csv(data_path + file + '.' + d_type, encoding='latin-1')
        except:
            con = pyodbc.connect(r'Driver={SQL Server};Server=' + str(server) + ';Database=' + str(db) + ';uid=' + un +
                                 ';pwd=' + pwd)
            query = 'select * from ' + str(table)
            df = pd.read_sql_query(query, con)

    # make all the column names in lower case
    df.columns = [str(i).lower() for i in df.columns]

    if len(cols_convert) > 2:
        cols = cols_convert.lower().replace('[','').replace(']','').split(',')
    else:
        cols = []
    if len(cols) > 0:
        df = dtype_convert(df, cols)

    # Function calling
    get_alias_for_attributes(df, data_path)
    # get_col_level(df, model_path)
    # get_descriptive(df, data_path)
    # train_agg_and_grp(model_path, data_path)


if __name__ == "__main__":
    main()

