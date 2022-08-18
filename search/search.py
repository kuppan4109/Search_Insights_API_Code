# -*- coding: utf-8 -*-
"""
Created on Sun Jan 31 15:10:56 2021

@author: DUCEN
"""



from flask import Flask,request,jsonify
import pyodbc
import pandas as pd
from flask_talisman import Talisman
from werkzeug import serving
import ssl

app=Flask(__name__)
con = pyodbc.connect(r'Driver={ODBC Driver 13 for SQL Server};''Server=10.0.2.12;'
                                'Database=Usecases;'
                             'uid=Analytics;pwd=Duc3n#@!') 

@app.route('/savediteminsert',methods=['POST'])
def savediteminsert():
    req_Json=request.json
    input_text=req_Json['name']
    dataset=req_Json['dataset']
    cursor = con.cursor()    
    query="INSERT INTO saved_item(saved_item_name, date_input,dataset)  VALUES (?,GETDATE(),?)"
    Values =[input_text,dataset]
    cursor.execute(query,Values) 
    con.commit()	
    return jsonify({'data':"Inserted"})					 


@app.route('/select',methods=['POST'])
def select():
    req_Json=request.json
    dataset=req_Json['dataset']
    query="SELECT saved_item_id, saved_item_name FROM saved_item WHERE dataset='" + dataset + "' ORDER BY date_input DESC"
    df = pd.read_sql_query(query, con)
    json = df.to_json(date_format='iso') 
    return jsonify({'data':json})

	
@app.route('/selectit',methods=['POST'])
def selectit():
    req_Json=request.json
    input_text=req_Json['name']
    dataset=req_Json['dataset']
    query="SELECT saved_item_id FROM saved_item WHERE saved_item_name ='"+input_text+"' and dataset='"+dataset+"' "
    df = pd.read_sql_query(query, con)
    json = df.to_json(date_format='iso') 
    return jsonify({'data':json})

	

  
@app.route('/keyinsert',methods=['POST'])
def keyinsert():
    req_Json=request.json
    ids = req_Json['id']
    word=req_Json['word']
    arr =req_Json['arr']
    #print(arrangement)
    cursor = con.cursor()    
    query="INSERT INTO saved_item_keywords(saved_item_id, keyword, arrangement) VALUES (?,?,?)"
    Values =[ids,word,arr]
    cursor.execute(query,Values)    
    con.commit()	
    return jsonify({'data':"Inserted"})

@app.route('/saveditemidselect',methods=['POST'])
def saveditemidselect():
    req_Json=request.json
    input_text=req_Json['itemid']
    dataset=req_Json['dataset']
    query="SELECT keyword FROM saved_item_keywords WHERE saved_item_id ='"+input_text +"' and dataset='"+dataset+"' ORDER BY arrangement "
    df = pd.read_sql_query(query, con)
    json = df.to_json() 
    return jsonify({'data':json})
	
	
@app.route('/keydelete',methods=['POST'])
def keydelete():
    req_Json=request.json
    ids = req_Json['itemid']
    cursor = con.cursor()    
    query="DELETE FROM saved_item_keywords WHERE saved_item_id = ?   "
    Values =[ids]
    cursor.execute(query,Values)  
    con.commit()	
    return jsonify({'data':"deleted"})
 
@app.route('/saveditemdelete',methods=['POST'])
def saveditemdelete():
    req_Json=request.json
    ids = req_Json['itemid']
    cursor = con.cursor()    
    query="DELETE FROM saved_item WHERE saved_item_id = ?"
    Values =[ids]
    cursor.execute(query,Values)  
    con.commit()	
    return jsonify({'data':"deleted"}) 

@app.route('/historyinsert',methods=['POST'])
def historyinsert():
    req_Json=request.json
    input = req_Json['keyword']
    dataset=req_Json['dataset']
    cursor = con.cursor()    
    query="INSERT INTO search_history (keyword,dataset) VALUES (?,?)"
    Values =[input,dataset]
    cursor.execute(query,Values)  
    con.commit()	
    return jsonify({'data':"Inserted"})


@app.route('/historyselect',methods=['POST'])
def historyselect():
    req_Json=request.json
    dataset=req_Json['dataset']
    query="SELECT keyword FROM search_history WHERE dataset='" + dataset + "' ORDER BY search_history_id DESC "
    df = pd.read_sql_query(query, con)
    json = df.to_json(date_format='iso') 
    return jsonify({'data':json})	


	
	
if __name__ =='__main__':
    app.run(debug=True,host="0.0.0.0",port=8091,ssl_context='adhoc')
    #serve(app, port=6060)  