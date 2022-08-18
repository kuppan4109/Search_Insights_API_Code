# -*- coding: utf-8 -*-
"""
Created on Wed Dec 16 16:19:41 2020

@author: DUCEN
"""

# Libraries

import joblib
import pandas as pd
import configparser
from train_table import EntityMatch
from functions import custom_pos
from sql_gnerations import text_to_sql,convert_dates_to_text
import pyodbc
from flask_talisman import Talisman
from werkzeug import serving
import ssl


# Read configuration file
config = configparser.RawConfigParser()
try:
    config.read('config.txt')
except Exception as e:
    print(str(e))
# get the paths and files
try:
    data_path = "C:\solution\V2\Data\\"
    model_path = "C:\solution\V2\Models\\"
    server = 'DUCENSRV005'
    db = 'Usecases'
    data_name = 'sales'
    data_type = "xlsx"
    table_name = "sales_tab"
    
except Exception as e:
    print(e)
    print('Not able to load configuration file..')

# load nlu model and required tables


from flask import Flask,request,jsonify

app=Flask(__name__)

@app.route('/test',methods=['POST'])
def test():
    req_Json=request.json
    input_text=req_Json['NL']
    Datasource=req_Json['Datasource']
    table_name = Datasource 
    data_path = "C:\solution\V2\Data\\"+table_name+"\\"
    model_path = "C:\solution\V2\Models\\"+table_name+"\\"
    df_cols_as = pd.read_csv(data_path+'df_col_info.csv')
    des_df = pd.read_csv(data_path+'des_df.csv')
    term_df = pd.read_csv(r'C:\solution\V2\Data\terms.csv')
    skip_keys = pd.read_csv(r'C:\solution\V2\Data\skip_keys.csv')
    nlu_mod = joblib.load(r'C:\solution\V2\Models\nlu_mod.pkl')
    level_dict = joblib.load(model_path + 'level_dict.pkl')
    tagger = custom_pos()
    query, NLU,title = text_to_sql(input_text, nlu_mod, des_df, term_df, tagger, level_dict, df_cols_as, skip_keys, table_name)
    con = pyodbc.connect(r'Driver={ODBC Driver 13 for SQL Server};''Server=10.0.2.12;'
                                'Database=Usecases;'
                             'uid=Analytics;pwd=Duc3n#@!') 
    #con = pyodbc.connect(driver='{SQL Server}', host=server, database=db,
#                  trusted_connection='yes', user='productservices', password='Duc3n#@!')
    #title=print(query)
    df = pd.read_sql_query(query, con)
    df = convert_dates_to_text(df)
    json = df.to_json(date_format='iso') 
    return jsonify({"query":query,'data':json,"title":title})
   
            
if __name__ =='__main__':
    app.run(debug=True,host="0.0.0.0",port=9090,ssl_context='adhoc')
    #serve(app, port=6060)