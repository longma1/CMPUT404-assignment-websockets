#!/usr/bin/env python
# coding: utf-8
# Copyright (c) 2013-2014 Abram Hindle
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import flask
from flask import Flask, request
from flask_sockets import Sockets
import gevent
from gevent import queue
import time
import json
import os

app = Flask(__name__)
sockets = Sockets(app)
app.debug = True

queues=[]

class World:
    def __init__(self):
        self.clear()
        # we've got listeners now!
        self.listeners = list()
        
    def add_set_listener(self, listener):
        self.listeners.append( listener )

    def update(self, entity, key, value):
        entry = self.space.get(entity,dict())
        entry[key] = value
        self.space[entity] = entry
        self.update_listeners( entity )

    def set(self, entity, data):
        self.space[entity] = data
        print('adding:',entity)
        self.update_listeners( entity )

    def update_listeners(self, entity):
        '''update the set listeners'''
        for listener in self.listeners:
            listener(entity, self.get(entity))

    def clear(self):
        self.space = dict()

    def get(self, entity):
        return self.space.get(entity,dict())
    
    def world(self):
        return self.space

myWorld = World()        

def set_listener( entity, data ):
    ''' do something with the update ! '''
    package={entity:data}
    load=json.dumps(package)
    for queue in queues:
        queue.put(load)
        
    
    

myWorld.add_set_listener( set_listener )
        
@app.route('/')
def hello():
    '''Return something coherent here.. perhaps redirect to /static/index.html '''
    return flask.redirect('/static/index.html')

def read_ws(ws,client):
    '''A greenlet function that reads from the websocket and updates the world'''
    # XXX: TODO IMPLEMENT ME
    try:
        while True:
            msg=ws.receive()
            if (msg is not None):
                load_json=json.loads(msg)
                entity=list(load_json.keys())[0]
                value=load_json[entity]
                myWorld.set(entity,value)
            else:
                break
    except Exception as e:
        print(e)
    return None

@sockets.route('/subscribe')
def subscribe_socket(ws):
    '''Fufill the websocket URL of /subscribe, every update notify the
       websocket and read updates from the websocket '''
    # XXX: TODO IMPLEMENT ME
    usr_queue=queue.Queue()
    queues.append(usr_queue)
    g=gevent.spawn(read_ws, ws, usr_queue)
    try:
        while True:
            msg=usr_queue.get()
            ws.send(msg)
            
    except Exception as e:
        print(e)
    myWorld.listeners.remove(usr_queue)
    gevent.kill(g)


# I give this to you, this is how you get the raw body/data portion of a post in flask
# this should come with flask but whatever, it's not my project.
def flask_post_json():
    '''Ah the joys of frameworks! They do so much work for you
       that they get in the way of sane operation!'''
    if (request.json != None):
        return request.json
    elif (request.data != None and request.data.decode("utf8") != u''):
        return json.loads(request.data.decode("utf8"))
    else:
        return json.loads(request.form.keys()[0])


#I think these are the same as assignment #4 so I'll try and just
#get copy and paste what I wrote last time?
# I dont think they will be used but might as well

@app.route("/entity/<entity>", methods=['POST','PUT'])
def update(entity):
    '''update the entities via this interface'''
    parcel=flask_post_json()
    return_dict={}
    
    myWorld.set(entity,parcel)
    return_json=json.dumps(parcel)
    response= app.response_class(response=return_json,mimetype='application/json')
    return response

@app.route("/world", methods=['POST','GET'])    
def world():
    '''you should probably return the world here'''
    entire_world=json.dumps(myWorld.world())
    encoded_world=entire_world.encode('utf-8')
	
    response= app.response_class(response=entire_world,mimetype='application/json')

    return response

@app.route("/entity/<entity>")    
def get_entity(entity):
    '''This is the GET version of the entity interface, return a representation of the entity'''
    desired_entity=json.dumps(myWorld.get(entity))
    if len(desired_entity)>0:
        encoded_entity=desired_entity.encode('utf-8')
        response=app.response_class(response=desired_entity, mimetype='application/json')
        return response
    #i guess return a 404 if entity does not exist?
    return flask.abort(404)


@app.route("/clear", methods=['POST','GET'])
def clear():
    myWorld.clear()
    '''Clear the world out!'''
    return "Ok"


if __name__ == "__main__":
    ''' This doesn't work well anymore:
        pip install gunicorn
        and run
        gunicorn -k flask_sockets.worker sockets:app
    '''
    app.run()
