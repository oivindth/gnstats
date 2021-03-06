#!/usr/bin/env python
# -*- coding: utf-8 -*-

import webapp2
import json
import logging
from datetime import datetime
from models import *
from google.appengine.api import users
from utils import *


class GameNightsHandler(webapp2.RequestHandler):
    def get(self):
        data = [game_night.get_data(current_user_person_name()) for game_night in GameNight.query()]
        set_json_response(self.response, data)


class GameNightHandler(webapp2.RequestHandler):
    def delete(self, gn_id):
        if not validate_logged_in_admin(self.response):
            return

        gn_key = GameNight.get_by_id(int(gn_id)).key
        ndb.delete_multi(Vote.query(Vote.game_night == gn_key).fetch(keys_only=True))
        gn_key.delete()

        set_json_response(self.response, {'response': "OK"})


class SyncHandler(webapp2.RequestHandler):
    def put(self):
        if not validate_authenticated(self.response):
            return

        request_data = json.loads(self.request.body)
        logging.info(request_data)

        return_data = []
        for updated_game_night in request_data:

            if not validate_request_data(self.response, updated_game_night, ['host', 'date', 'description']):
                return

            gn_id = updated_game_night.get('id')
            if gn_id:
                gn = GameNight.get_by_id(int(gn_id))
            else:
                gn = GameNight()

            gn.date = datetime.strptime(updated_game_night['date'], '%Y-%m-%dT%H:%M:%S.%fZ')
            gn.host = updated_game_night['host']
            gn.description = updated_game_night['description']
            gn.sum = 0

            if not gn_id:
                gn.put()

            # Update votes which was supplied to sync call, should only be the logged in players vote. But keeping code to support multiple update.
            vote_ids = []
            for vote_data in updated_game_night['votes']:
                if vote_data['voter'] == updated_game_night['host']:
                    continue

                if not Person.query(Person.name == vote_data['voter']).get().activated:
                    error_400(self.response, "ERROR_INACTIVE_CANT_VOTE", "Deactivated person is not allowed to vote!")
                    return

                if vote_data.has_key('id'):
                    vote_id = int(vote_data['id'])
                    vote = Vote.get_by_id(vote_id)
                    vote_ids.append(vote_id)
                else:
                    vote = Vote()

                vote.game_night = gn.key
                vote.voter = vote_data['voter']
                vote.appetizer = vote_data.get('appetizer')
                vote.main_course = vote_data.get('main_course')
                vote.dessert = vote_data.get('dessert')
                vote.game = vote_data.get('game')
                vote.put()

                gn.sum += vote.weighed_sum()

            # The game night sum also has to have the sum added from the other votes
            for vote in Vote.query(Vote.game_night == gn.key):
                if vote.key.id() not in vote_ids:
                    gn.sum += vote.weighed_sum()

            gn.put()

        set_json_response(self.response, {'response': "OK"})

    @staticmethod
    def _get_or_create_game_night_object(id):
        if id:
            return GameNight.get_by_id(int(id))
        else:
            return GameNight()


app = webapp2.WSGIApplication([
    (r'/api/game_night/', GameNightsHandler),
    (r'/api/game_night/(\d+)/', GameNightHandler),
    (r'/api/game_night/sync/', SyncHandler)
], debug=True)
