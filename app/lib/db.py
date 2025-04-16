import sqlite3
import os
import json
import time

def tableExists(dbname, tableName, verbose=False):
    tableExistsInDB = False
    con = sqlite3.connect(dbname)
    con.execute("PRAGMA journal_mode=WAL")
    cur = con.cursor()
    #dupcheck
    dq = "SELECT * FROM sqlite_master WHERE name = '{}'".format(tableName)
    dr = cur.execute(dq)
    if len(dr.fetchall()) > 0:
        tableExistsInDB = True
        if verbose:
            print("{} already exists".format(tableName))
    con.commit()
    con.close()
    return tableExistsInDB

def create(dbname, useExisting=False, verbose=False):
    if useExisting == False:
        alreadyExists = os.path.isfile(dbname)
        if alreadyExists:
            if verbose:
                print("{} already exists. Deleting it to create from scratch.".format(dbname))
            os.remove(dbname)
    con = sqlite3.connect(dbname)
    cur = con.cursor()
    r = cur.execute("SELECT * FROM sqlite_master")
    if verbose:
        print("DB created with {} tables.".format(len(r.fetchall())))
    con.close()
    return dbname

def table(dbname, tableName, tableColumns, verbose=False):
    con = sqlite3.connect(dbname)
    con.execute("PRAGMA journal_mode=WAL")
    cur = con.cursor()
    #dupcheck
    if tableExists(dbname=dbname, tableName=tableName, verbose=verbose) == False:
        query = "CREATE TABLE {}({})".format(tableName, ",".join(tableColumns))
        if verbose:
            print("db query: {}".format(query))
        cur.execute(query)
    con.commit()
    con.close()
    
def delete(dbname, query, datatuple, tableName, verbose):
    con = sqlite3.connect(dbname)
    con.execute("PRAGMA journal_mode=WAL")
    cur = con.cursor()
    keepTrying = True
    count = 0
    # Writes should be re-tried if they fail at first. Only one thread can write to an SQLite DB at a time, and so multi-threaded scripts could run into problems.
    while keepTrying:
        count = count + 1
        try:
            cur.execute(query, datatuple)
            if verbose:
                print("attempt {}: {} | {}".format(count, query, datatuple))
                tableSize = cur.execute("SELECT * FROM {}".format(tableName))
                print("{} already has {} entries".format(tableName, len(tableSize.fetchall())))
            #if there's an error it'll happen above so reaching this line is a sign that things worked.
            keepTrying = False
        except Exception as e:
            time.sleep(count)
            if count > 5:
                keepTrying = False
            if verbose:
                print("Error: {} on attempt {}. '{}'".format(e, count, query))
    con.commit()
    con.close()

def insert(dbname, query, datatuple, tableName, verbose):
    con = sqlite3.connect(dbname)
    con.execute("PRAGMA journal_mode=WAL")
    cur = con.cursor()
    if tableExists(dbname=dbname, tableName=tableName, verbose=verbose) == False:
        if verbose:
            print("table {} dosen't exist in {}.".format(tableName, dbname))
        return
    else:
        keepTrying = True
        count = 0
        # Writes should be re-tried if they fail at first. Only one thread can write to an SQLite DB at a time, and so multi-threaded scripts could run into problems.
        while keepTrying:
            count = count + 1
            try:
                cur.execute(query, datatuple)
                if verbose:
                    print("attempt {}: db: {} | {} | {}".format(count, dbname, query, datatuple))
                    tableSize = cur.execute("SELECT * FROM {}".format(tableName))
                    print("{} already has {} entries".format(tableName, len(tableSize.fetchall())))
                #if there's an error it'll happen above so reaching this line is a sign that things worked.
                keepTrying = False
            except Exception as e:
                time.sleep(count)
                if count > 5:
                    keepTrying = False
                if verbose:
                    print("Error: {} on attempt {}. '{}'".format(e, count, query))
    con.commit()
    con.close()

def select(dbname, query, datatuple, tableName, selectColumns=[], verbose=False):
    results = []
    con = sqlite3.connect(dbname)
    con.execute("PRAGMA journal_mode=WAL")
    cur = con.cursor()
    if verbose:
        print("db: {} | q: {} | {}".format(dbname, query, datatuple))
    if tableExists(dbname=dbname, tableName=tableName, verbose=verbose) == False:
        if verbose:
            print("table {} dosen't exist in {}.".format(tableName, dbname))
    else:
        # If you're selecting all columns then the table can be queried
        # for ther names. In other cases either the columns need to be 
        # specified or else the script will just use the index values as names
        customColumnNames = False
        indexColumnNames = False
        if "select * " not in query.lower():
            if verbose:
                print("This select statement doesn't appear to select all columns.")
            if len(selectColumns) == 0:
                indexColumnNames = True
                if verbose:
                    print("Column names will be derived from index values")
            else:
                customColumnNames = True
                if verbose:
                    print("Column names will be derived from this list: {}".format(selectColumns))
        r = cur.execute(query, datatuple)
        try:
            resultsList = r.fetchall()
            tableSchema = {}
            if customColumnNames == False and indexColumnNames == False:
                if verbose:
                    print("Building table scheme by getting all column names")
                try:
                    tableSchemaR = cur.execute("PRAGMA table_info({})".format(tableName))
                    tableSchemaTup = tableSchemaR.fetchall()
                    # maps the column index to its name
                    for i in tableSchemaTup:
                        tableSchema[int(i[0])] = i[1]
                    if verbose:
                        print("{} schema: {}".format(tableName, json.dumps(tableSchema)))
                except Exception as e:
                    print("Couldn't build schema for {}".format(tableName))
                    if verbose:
                        print("{}".format(e))
            elif customColumnNames and indexColumnNames == False:
                if verbose:
                    print("Building table schema from list: {}".format(selectColumns))
                i = 0
                for columnName in selectColumns:
                    tableSchema[i] = columnName
                    i = i + 1
            elif indexColumnNames and customColumnNames == False:
                tableSchema[0] = "index on request"
            else:
                if "select * " in query.lower():
                    print("query {} doesn't seem to be a 'select *' query where column names can be infered, yet argument selectColumns was empty ({}).\nIn order to avoid an error, the column index values will be used as column names".format(query, selectColumns))
                    indexColumnNames = True
                    tableSchema[0] = "defaulted to index"
            try:
                if verbose:
                    print("{} schema: {}".format(tableName, json.dumps(tableSchema)))
                for result in resultsList:
                    if verbose:
                        print("{}".format('|'.join(map(str, result))))
                    # uses the mapping from above to build a dictionary out of tuple results
                    rd = {}
                    i = 0
                    for column in result:
                        if indexColumnNames:
                            rd[i] = column
                        else:
                            rd[tableSchema[i]] = column
                        i = i + 1
                    results.append(rd)
            except Exception as e:
                print("Couldn't build results dictionary for {}".format(query))
                if verbose:
                    print("{}".format(e))
                    
        except Exception as e:
            if verbose:
                print("tried to run {}".format(query))
            print("{}".format(e))
    con.commit()
    con.close()
    return results