

# Libraries
import joblib
import pyodbc
import configparser
import pandas as pd
from functions import custom_pos
from train_table import EntityMatch
from sql_gnerations import text_to_sql, convert_dates_to_text


# Read configuration file
config = configparser.RawConfigParser()
try:
    config.read('D:\R&D\Text to SQL - II\Phase-3\Scripts\config.txt')
except Exception as e:
    print(str(e))
# get the paths and files
try:
    db = config.get('database', 'DB')
    un = config.get('database', 'UN')
    pwd = config.get('database', 'PWD')
    server = config.get('database', 'IP')
    data_path = config.get('paths', 'data_path')
    table_name = config.get('table', 'table_name')
    model_path = config.get('paths', 'model_path')
except Exception as e:
    print(e)
    print('Not able to load configuration file..')

# load nlu model and required tables
tagger = custom_pos()
des_df = pd.read_csv(data_path+'des_df.csv')
term_df = pd.read_csv(data_path+'terms.csv')
nlu_mod = joblib.load(model_path + 'nlu_mod.pkl')
skip_keys = pd.read_csv(data_path+'skip_keys.csv')
df_cols_as = pd.read_csv(data_path+'alias_df.csv')
level_dict = joblib.load(model_path + 'level_dict.pkl')

# While loop for testing multiple questions
input_text = 'Hello'
while input_text!='stop':
    input_text = str(input('Ask Me: ')).strip().lower()
    if input_text != 'stop':

        try:
            query, NLU, title = text_to_sql(input_text, nlu_mod, des_df, term_df, tagger, level_dict, df_cols_as, skip_keys, table_name)
            print(query, end='\n\n')
            con = pyodbc.connect(r'Driver={SQL Server};Server=' + str(server) + ';Database=' + str(db) + ';uid=' + un +
                                 ';pwd=' + pwd)
            df = pd.read_sql_query(query, con)
            df = convert_dates_to_text(df)
            print(df.head(15))
        except Exception as e:
            print(e)
            print('Please try with another sentence...\n')
