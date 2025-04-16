# Little Logger

Meant to be the absolute simpliest logging backend possible. Send a log message with a simple POST request and retrieve logs with a GET request specifying the application you're interested in. 

DB backend is a simple SQLite3 file for each application.

Your first request for a given application sets the schema that all subsequent requests musts exactly follow in order to successfully add new logs.

It fully supports etags so you can minimize traffic by only getting the logs if needed.