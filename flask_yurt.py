from pymongo import MongoClient
from flask.sessions import SessionInterface, SessionMixin
from werkzeug.datastructures import CallbackDict
import os
import collections

# a dictionary that fires events before the first read or after updates
class LazyDictionary(dict, collections.MutableMapping):
    on_read = None
    on_update = None
    read = False

    def __init__(self, dictionary=None, on_update=None, on_read=None):
        dict.__init__(self, dictionary or ())
        self.on_update = on_update
        self.on_read = on_read

    def __repr__(self):
        return '<%s %s>' % (
            self.__class__.__name__,
            dict.__repr__(self)
        )

    def calls_read(name, skip=False):
        def oncall(self, *args, **kargs):
            if self.on_read is not None and not skip and not self.read:
                self.read = True
                self.on_read(self)
            rv = getattr(super(LazyDictionary, self), name)(*args, **kargs)
            return rv
        oncall.__name__ = name
        return oncall

    def calls_update(name, skip=False):
        def oncall(self, *args, **kargs):
            rv = getattr(super(LazyDictionary, self), name)(*args, **kargs)              
            if self.on_update is not None and not skip:
                self.on_update(self)      
            return rv
        oncall.__name__ = name
        return oncall

    # these methods fire on_read
    __getitem__ = calls_read('__getitem__')
    __len__ = calls_read('__len__')
    __iter__ = calls_read('__iter__')
    items = calls_read('items')
    get = calls_read('get')

    # these methods fire on_update
    __setitem__ = calls_update('__setitem__')
    __delitem__ = calls_update('__delitem__')
    clear = calls_update('clear')
    pop = calls_update('pop')
    popitem = calls_update('popitem')
    setdefault = calls_update('setdefault')
    update = calls_update('update')

    # this private update method skips the callback so we can update the 
    # lazy dictionary during initialization
    __update__ = calls_update('update', skip=True)

    del calls_update

class YurtSession(LazyDictionary, SessionMixin):
    store = dict()
    session_id = None
    new = False
    modified = False
    read = False
    session_interface = None

    # defer loading of session variables until the first read
    def on_read(self):
        if not self.read or not self.new:
            session_store = self.session_interface.find_session(self.session_id)
            if(session_store):
                self.__update__(session_store["variables"])
            self.read = True

    def on_update(self):
        if not self.modified:
            self.modified = True

    # delete the session, never to be used again
    def delete(self):
        self.clear()
        self.session_interface.clear_session(self.session_id)
        self.session_interface.delete_session = True

    # invalidate the current session and generate a new one
    def invalidate(self):
        self.clear()
        self.session_interface.clear_session(self.session_id)
        self.session_id = self.session_interface.generate_session_id()
        self.new = True

    def __init__(
            self, 
            dictionary=None, 
            session_id=None, 
            new=False, 
            on_update=on_update, 
            on_read=on_read, 
            session_interface=None
        ):

        self.session_interface = session_interface
        self.session_id = session_id
        self.new = new
        LazyDictionary.__init__(self, dictionary, on_update, on_read)


class YurtSessionInterface(SessionInterface):
    session_class = YurtSession
    client = MongoClient('localhost', 27017)
    mongo_database = client["projects"]
    session_collection = mongo_database["sessions"]
    delete_session = False

    def open_session(self, app, request):
        session_id = request.cookies.get(app.session_cookie_name)
        if not session_id:
            session_id = self.generate_session_id()
            app.logger.debug("Opening a new session: " + session_id)
            return self.session_class(session_id=session_id, new=True, 
                session_interface=self)
        app.logger.debug("Opening the existing session: " + session_id)
        return self.session_class(session_id=session_id, session_interface=self)

    def save_session(self, app, session, response):
        if self.delete_session:
            self.delete_session_cookie(app, session, response)
            self.delete_session = False
            return

        session_store = self.find_session(session.session_id)
        if session.modified:
            if session_store:
                app.logger.debug("Updating the session with id: " + 
                    session.session_id)
                session_store["variables"] = session
                self.session_collection.save(session_store)
            else:
                app.logger.debug("Starting a new session with id: " + 
                    session.session_id)
                self.insert_session(session)
                self.set_session_cookie(app, session, response)
            session.modified = False

    def clear_session(self, session_id):
        self.session_collection.remove({"session_id":session_id})

    def delete_session_cookie(self, app, session, response):
        app.logger.debug("Deleting the session cookie: " + 
            app.session_cookie_name)
        domain = self.get_cookie_domain(app)
        path = self.get_cookie_path(app)

        response.delete_cookie(app.session_cookie_name, path=path, 
            domain=domain)
        self.delete_session = True

    def set_session_cookie(self, app, session, response):
        # get cookie options
        expiration_date = self.get_expiration_time(app, session)
        domain = self.get_cookie_domain(app)
        path = self.get_cookie_path(app)
        httponly = self.get_cookie_httponly(app)
        secure = self.get_cookie_secure(app)

        app.logger.debug("Setting the session cookie: " +
            app.session_cookie_name + " to :" + session.session_id)
        response.set_cookie(app.session_cookie_name, session.session_id, 
            path=path, 
            expires=expiration_date, 
            httponly=False, 
            secure=secure, 
            domain=domain)

    def find_session(self, session_id):
        return self.session_collection.find_one(
            {"session_id": session_id,}
        )

    def insert_session(self, session):
        if session:
            new_session = {
                "session_id": session.session_id, 
                "variables": session
            }
            print self.session_collection.insert(new_session)

    def generate_session_id(self):
        return os.urandom(16).encode('hex')