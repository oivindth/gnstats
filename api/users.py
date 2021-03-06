#!/usr/bin/env python
# -*- coding: utf-8 -*-

import webapp2
import json
import logging
from models import *
from google.appengine.api import users
from utils import *
from config_hidden import SitePassword


class MyUserHandler(webapp2.RequestHandler):
    def get(self):
        self.response.headers['Content-Type'] = 'application/json'
        user = users.get_current_user()
        if user:
            person = Person.query(Person.userid == user.user_id()).get()
            verified = True if person else False
            name = person.name if person else None
            set_json_response(self.response, {'name': name, 'nickname': user.nickname(), 'verified': verified, 'is_admin': users.is_current_user_admin()})
        else:
            set_json_response(self.response, {})


class LoginHandler(webapp2.RequestHandler):
    def get(self):
        redirect = self.request.get('redirect', "/")
        return webapp2.redirect(users.create_login_url(redirect))


class LogoutHandler(webapp2.RequestHandler):
    def get(self):
        redirect = self.request.get('redirect', "/")
        return webapp2.redirect(users.create_logout_url(redirect))


class VerifyHandler(webapp2.RequestHandler):
    def post(self):
        request_data = json.loads(self.request.body)

        if not validate_request_data(self.response, request_data, ['name', 'password']):
            return
        if not request_data['password'] == SitePassword:
            error_400(self.response, "error_bad_password", "Bad password")
            return

        user = users.get_current_user()
        Person(
            name=request_data['name'],
            userid=user.user_id(),
            nickname=user.nickname()
        ).put()

        set_json_response(self.response, {'response': "OK"})


class AvailableNamesHandler(webapp2.RequestHandler):
    def get(self):
        person_names_taken = [person.name for person in Person.query()]
        available_names = [name for name in person_names_allowed if name not in person_names_taken]
        set_json_response(self.response, available_names)


class ActivateUserHandler(webapp2.RequestHandler):
    def post(self):
        if not users.is_current_user_admin():
            unauthorized_401(self.response, "HACKERALARM", "NSA, FBI and NWA has been warned about you!")

        request_data = json.loads(self.request.body)
        _updateActivated(request_data['name'], True)
        set_json_response(self.response, {'response': "OK"})


class DeactivateUserHandler(webapp2.RequestHandler):
    def post(self):
        if not users.is_current_user_admin():
            unauthorized_401(self.response, "HACKERALARM", "NSA, FBI and NWA has been warned about you!")

        request_data = json.loads(self.request.body)
        _updateActivated(request_data['name'], False)
        set_json_response(self.response, {'response': "OK"})


def _updateActivated(name, activatedValue):
    person = Person.query(Person.name == name).get()
    person.activated = activatedValue
    person.put()


class UsersHandler(webapp2.RequestHandler):
    def get(self):
        set_json_response(self.response, [person.get_data() for person in Person.query()])


app = webapp2.WSGIApplication([
    (r'/api/users/my/', MyUserHandler),
    (r'/api/users/login/', LoginHandler),
    (r'/api/users/logout/', LogoutHandler),
    (r'/api/users/verify/', VerifyHandler),
    (r'/api/users/available-names/', AvailableNamesHandler),
    (r'/api/users/activate/', ActivateUserHandler),
    (r'/api/users/deactivate/', DeactivateUserHandler),
    (r'/api/users/', UsersHandler),
], debug=True)
