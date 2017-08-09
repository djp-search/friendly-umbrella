from datetime import datetime
from elasticsearch import Elasticsearch
from json import loads		
from math import log

######
# file:    recall_precision_comparison.py
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
no_tag = "unclassified"

es = Elasticsearch([
    {'host': '192.168.56.101'}
])

####
import abc

####
# Factory modes for candidate classification methods
#
class AbstractClassifier(object):
    __metaclass__ = abc.ABCMeta

    #@abc.abstractmethod
    #def __init__(self, *args, **kwargs):
        #pass

    @abc.abstractmethod
    def tag(self, *args, **kwargs):
        pass


# Classify by Tag of highest weighted hit
class FirstMatchClassifier(AbstractClassifier):

    @staticmethod
    def tag(search_body):
       res = es.search(index=training_index, body=search_body)
       if int(res['hits']['total']) > 0:
          return res['hits']['hits'][0]['_source']['doc']['tag']
       else:
          return no_tag

# Sum weights on per tag basis and return highest 
class AggregateWeightClassifier(AbstractClassifier):

    @staticmethod
    def tag(search_body):
       res = es.search(index=training_index, body=search_body)
       if int(res['hits']['total']) > 0:
          tag_scores = dict()
          for hit in res['hits']['hits']:
             if hit['_source']['doc']['tag'] not in tag_scores.keys():
                 tag_scores[hit['_source']['doc']['tag']] = hit['_score']
             else:
                 tag_scores[hit['_source']['doc']['tag']] += hit['_score']
          return sorted(tag_scores, key=tag_scores.__getitem__,reverse=True)[0]
       else:
          return no_tag

# Sum squares of weights on per tag basis and return highest 
class AggregateWeightSquaresClassifier(AbstractClassifier):

    @staticmethod
    def tag(search_body):
       res = es.search(index=training_index, body=search_body)
       if int(res['hits']['total']) > 0:
          tag_scores = dict()
          for hit in res['hits']['hits']:
             if hit['_source']['doc']['tag'] not in tag_scores.keys():
                 tag_scores[hit['_source']['doc']['tag']] = hit['_score'] ** 2
             else:
                 tag_scores[hit['_source']['doc']['tag']] += hit['_score'] ** 2
          return sorted(tag_scores, key=tag_scores.__getitem__,reverse=True)[0]
       else:
          return no_tag

# factory object 
class ClassifierFactory(object):
    classifier_modes = {
        'firstmatch': FirstMatchClassifier,
        'aggregateweight': AggregateWeightClassifier,
        'aggregateweightsquares': AggregateWeightSquaresClassifier
    }

    @staticmethod
    def get_tag_obj(name, search_body):
       classifier_mode = ClassifierFactory.classifier_modes.get(name.lower(), None)
       if classifier_mode:
          return classifier_mode.tag(search_body)
       raise NotImplementedError('The requested classifier has not been '\
          'implemented')

####
# functions

####
def get_tag(classifier_mode,search_body):
   return classifier_obj.get_tag_obj(classifier_mode, search_body)

####
def update_metrics(test_result,expected_result):
   print "foo"

####
def display_summary(test_id,
   classifier_mode,
   short_description,
   test_result,
   expected_tag):
   print "Test {} {} {}... Result [{}] Expected [{}]".format(
      test_id,
      classifier_mode,
      short_description,
      test_result,
      expected_tag)

####
def test_run(test_id,
   classifier_mode,
   search_body,
   expected_tag):

   test_result = get_tag(classifier_mode,search_body)
   update_metrics(test_result,expected_tag)
   display_summary(test_id,
      classifier_mode,
      search_body['query']['match']['doc.description'][:12],
      test_result,
      expected_tag)

####
# main starts here


# test results
summary = {'true': {'positive': 0, 'negative': 0},
    'false': {'positive': 0, 'negative': 0}}

tests = open(test_datafile, 'r')
for test in tests:
   classifier_obj = ClassifierFactory()
   for classifier_mode in classifier_obj.classifier_modes.keys():
      tl = loads(test)
      test_run(tl['test']['id'],
         classifier_mode,
         tl['test']['search_body'],
         tl['expected_result']['tag'])

tests.close()
   
