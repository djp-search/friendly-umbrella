from datetime import datetime
from elasticsearch import Elasticsearch
from json import loads		

######
# file:    recall_precision_method_01.py
# date:    20170808 
# status:  draft
# version: 0.1
# authors: djptek
# purpose: calculate recall/precision for classification method 01
######
 
# set to your elastic host (in this case VM)
es = Elasticsearch([
    {'host': '192.168.56.101'}
])

training_index = 'training'
training_type = 'example'
test_datafile = '../scenarios/test_01-03.json'

es = Elasticsearch([
    {'host': '192.168.56.101'}
])

tests = open(test_datafile, 'r')

for test in tests:
   res = es.search(index=training_index, body=loads(test))
   print("Got %d Hits:" % res['hits']['total'])
   #print(str(res))
   for hit in res['hits']['hits']:
      print('{} {}'.format(hit['_score'], hit['_source']['doc']['class']))

tests.close()

# {u'_score': 1.0, u'_type': u'example', u'_id': u'AV3CvYAR4eqTA1KdM0d8', u'_source': {u'doc': {u'class': u'mineral', u'description': u'A bicycle, also called a cycle or bike, is a human-powered, pedal-driven, single-track vehicle, having two wheels attached to a frame, one behind the other. A bicycle rider is called a cyclist, or bicyclist.', u'name': u'bicycle'}}, u'_index': u'training'}
