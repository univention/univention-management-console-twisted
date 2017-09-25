Univention Management Console Server Rewrite with Twisted
=========================================================

This project is a prototype implementation of a rewrite of the Univention Management Console Framework.
It merges the UMC-Server (UMCP daemon uding python notifier) and UMC-Webserver (HTTP Webserver using python cherrypy) component into one component.

The goal is to replace the proprietrary protocol UMCP with HTTP.
It used the twisted.web Framework as HTTP Webserver implementation for all the socket, event and protocol handling.
The dependency to python-notifier is removed and reduced.

It builds the basis to implement a RESTful implementation of UMC but currently conforms to all current API's and therefor keeps the RPC like architecture.

This project is the apprentice ship final project of Florian Best and is based on the Code of UCS 3.2.
