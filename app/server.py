import re
import hashlib
import json
import os
from lib import db
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from typing import Annotated
from fastapi import FastAPI, Response, Header, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

def dateTimeOffset(dt, offset):
    offsetnum = re.sub(r"\D", "", offset)
    offsetint = int(offsetnum)
    if "m" in offset:
        nt = dt - timedelta(minutes=offsetint)
        thenTimeStamp = int(nt.timestamp())
        return thenTimeStamp
    elif "h" in offset:
        nt = dt - timedelta(hours=offsetint)
        thenTimeStamp = int(nt.timestamp())
        return thenTimeStamp
    elif "d" in offset:
        nt = dt - timedelta(days=offsetint)
        thenTimeStamp = int(nt.timestamp())
        return thenTimeStamp
    else:
        print("{} didn't seem to be minutes, hours, or days.\nI'll take it as a timestamp".format(offset))
        return offsetint

app = FastAPI()

class LogEntry(BaseModel):
    message: dict = {}

@app.get("/health-check")
def read_healthcheck(response: Response):
    response.headers["Cache-Control"] = "no-cache, no-store"
    healthJSON = {"online": True}
    return healthJSON

@app.post("/{application}", status_code=201)
def root(log: LogEntry, application: str):
    #log = jsonable_encoder(logRaw)
    now = datetime.now(ZoneInfo(os.environ["TZ"]))
    nowString = now.strftime("%Y-%m-%d %H:%m:%S")
    print("{}: new log: {}".format(nowString, log.message))
    nowTimeStamp = int(now.timestamp())
    log.message["timestamp"] = nowTimeStamp
    dblocation = "/db/logs-{}.db".format(application)
    verboseDB = True
    db.create(dbname=dblocation, useExisting=True, verbose=verboseDB)
    tableName = "logs"
    columns = log.message.keys()
    db.table(dbname=dblocation, tableName=tableName, tableColumns=columns, verbose=verboseDB)
    queryQuestionMarksList = ['?'] * len(log.message.values())
    queryQuestionMarks = ",".join(queryQuestionMarksList)
    query = "INSERT INTO {} VALUES({})".format(tableName, queryQuestionMarks)
    queryd = tuple(log.message.values())
    db.insert(dbname=dblocation, query=query, datatuple=queryd, tableName=tableName, verbose=verboseDB)
    respdict = {}
    respdict["log-time"] = nowTimeStamp
    respdict["status"] = "done"
    now = datetime.now(ZoneInfo(os.environ["TZ"]))
    nowString = now.strftime("%Y-%m-%d %H:%m:%S")
    print("{}: log saved".format(nowString))
    return respdict

@app.get("/{application}", status_code=200)
def read_root(application: str, time: str = "", filter: bool | None = False, key: str | None = None, value: str | None = None, limit: int | None = None, etag: Annotated[str, Header()] = "", if_none_match: Annotated[str, Header()] = ""):
    dblocation = "/db/logs-{}.db".format(application)
    verboseDB = False
    db.create(dbname=dblocation, useExisting=True, verbose=verboseDB)
    now = datetime.now(ZoneInfo(os.environ["TZ"]))
    nowString = now.strftime("%Y-%m-%d %H:%m:%S")
    print("{}: getting logs for {}".format(nowString, application))
    filterQuery = ""
    queryData = ()
    if time != "":
        then = dateTimeOffset(now, time)
        filterQuery = " WHERE timestamp > ? "
        queryData = queryData + (then,)
    if filter:
        print("I will filter the results")
        if filterQuery == "":
            filterQuery = " WHERE {} LIKE '%{}%' COLLATE NOCASE ".format(key, value)
        else:
            filterQuery = "{}WHERE {} LIKE '%{}%' COLLATE NOCASE ".format(filterQuery, key, value)
    query = "SELECT * FROM logs{} ORDER BY timestamp desc".format(filterQuery)
    if limit != None:
        query = "{} LIMIT {}".format(query, limit)
    now = datetime.now(ZoneInfo(os.environ["TZ"]))
    nowString = now.strftime("%Y-%m-%d %H:%m:%S")
    print("{}: search query: {}".format(nowString, query))
    r = db.select(dbname=dblocation, query=query, datatuple=queryData, tableName="logs", verbose=verboseDB)
    respd = {}
    respd["count"] = len(r)
    respd["logs"] = r
    respd["application"] = application
    now = datetime.now(ZoneInfo(os.environ["TZ"]))
    nowString = now.strftime("%Y-%m-%d %H:%m:%S")
    print("{}: {} logs found".format(nowString, len(r)))
    newEtag = hashlib.md5(str(json.dumps(respd)).encode('utf-8')).hexdigest()
    if etag == newEtag or if_none_match == newEtag:
        headers = {"Content-Type": "application/json", "ETag": "{}".format(newEtag)}
        return JSONResponse(content=b'', headers=headers, status_code=status.HTTP_304_NOT_MODIFIED)
    else:
        headers = {"Content-Type": "application/json", "ETag": "{}".format(newEtag)}
        return JSONResponse(content=respd, headers=headers)