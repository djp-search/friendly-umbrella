from datetime import datetime
from elasticsearch import Elasticsearch
from json import loads		
from math import log
import random

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
test_datafile = '../scenarios/test_01-06.json'
no_tag = 'unclassified'
all_tags = 'all_tags'
random.seed(123)

es = Elasticsearch([
    {'host': '192.168.56.101'}
])

####
# adapt to specific use case: assuming a CRM application
# false positive => misunderstand the client issue
# false negative => take longer to understand the client issue
# true positive => correctly identify the client issue
# true negative => correctly discard non relevant issues
value = {'false': {'positive': -15, 'negative': -5},
   'true': {'positive': 15, 'negative': 5}}

####
import abc

####
# Factory classes for candidate classification modes
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
          # slice top 3 (so that results deviate from firstmatch)
          for hit in res['hits']['hits'][0:3]:
             if hit['_source']['doc']['tag'] not in tag_scores.keys():
                 tag_scores[hit['_source']['doc']['tag']] = hit['_score']
             else:
                 tag_scores[hit['_source']['doc']['tag']] += hit['_score']
          return sorted(tag_scores, key=tag_scores.__getitem__,reverse=True)[0]
       else:
          return no_tag

# Purely Random Classification
class RandomClassifier(AbstractClassifier):

    @staticmethod
    def tag(search_body):
       return tags[random.randint(0,2)]

# Fixed Tag Classification
class FixedClassifier(AbstractClassifier):

    @staticmethod
    def tag(search_body):
       return tags[0]

# factory object 
class ClassifierFactory(object):
    classifier_modes = {
        'firstmatch': FirstMatchClassifier,
        'aggregateweight': AggregateWeightClassifier,
        'random': RandomClassifier,
        'fixed': FixedClassifier
    }

    @staticmethod
    def get_tag_obj(name, search_body):
       classifier_mode = ClassifierFactory.classifier_modes.get(name.lower(), None)
       if classifier_mode:
          return classifier_mode.tag(search_body)
       raise NotImplementedError('The requested classifier has not been '\
          'implemented')

####
# Dictionary to encapsulate metrics
tags = []
metrics = dict()

####
# functions

####
### Calculate precision, divide by zero safe
def precision (tp, fp, fn):
    if tp + fp > 0:
        return str(tp/float(tp+fp))
    elif fn > 0:
        return '0.0'
    else:
            return '1.0'
####
### Calculate recall, divide by zero safe
def recall (tp, fp, fn):
    if tp + fn > 0:
        return str(tp/float(tp+fn))
    elif fp > 0:
        return '0.0'
    else:
            return '1.0'

####
def get_tag(classifier_mode,search_body):
   return classifier_obj.get_tag_obj(classifier_mode, search_body)

####
def initialize_metrics():
   res = es.search(index=training_index,body='{ "query": { "match_all": {} } }')
   for hit in res['hits']['hits']:
      if hit['_source']['doc']['tag'] not in tags:
         tags.append(hit['_source']['doc']['tag'])
   for classifier_mode in classifier_obj.classifier_modes.keys():
      metrics[classifier_mode] = dict()
      for tag in tags:
         metrics[classifier_mode][tag] = {
            'false': {'positive': 0, 'negative': 0}, 
            'true': {'positive': 0, 'negative': 0}}

####
def update_metrics(classifier_mode,test_result,expected_result):
   if test_result == expected_result:
      metrics[classifier_mode][test_result]['true']['positive'] += 1
      for tag in tags:
         if tag != test_result:
            metrics[classifier_mode][tag]['true']['negative'] += 1
   else:
      metrics[classifier_mode][expected_result]['false']['negative'] += 1
      metrics[classifier_mode][test_result]['false']['positive'] += 1
      for tag in tags:
         if tag not in [test_result,expected_result]:
            metrics[classifier_mode][tag]['true']['negative'] += 1

####
def display_summary(test_id,
   classifier_mode,
   short_description,
   test_result,
   expected_tag):
   print "\tTest {:2} {:16} {}... Result {:12} Expected {}".format(
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
   update_metrics(classifier_mode,test_result,expected_tag)
   display_summary(test_id,
      classifier_mode,
      search_body['query']['match']['doc.description'][:12],
      test_result,
      expected_tag)

####
def display_recall_precision():
   print "Calculate/Collate recall + precision"
   for mode in metrics:
      metrics[mode][all_tags] = {
            'false': {'positive': 0, 'negative': 0},
            'true': {'positive': 0, 'negative': 0}}
      for tag in tags:
         metrics[mode][tag].update({'precision':
            float(precision(metrics[mode][tag]['true']['positive'],
               metrics[mode][tag]['false']['positive'],
               metrics[mode][tag]['false']['negative'])),
            'recall':
            float(recall(metrics[mode][tag]['true']['positive'],
               metrics[mode][tag]['false']['positive'],
               metrics[mode][tag]['false']['negative']))})
         for tf in ['true','false']:
            for pn in ['positive','negative']:
               metrics[mode][all_tags][tf][pn] += metrics[mode][tag][tf][pn]
         print "\tMode {:19} Tag {:12} Precision {:5.2f} Recall {:5.2f}".format(
            mode,
            tag,
            metrics[mode][tag]['precision'],
            metrics[mode][tag]['recall'])
      print "\tMode {:19} Tag {:12} Precision {:5.2f} Recall {:5.2f}".format(
         mode,
         all_tags,
         float(precision(metrics[mode][all_tags]['true']['positive'],
            metrics[mode][all_tags]['false']['positive'],
            metrics[mode][all_tags]['false']['negative'])),
         float(recall(metrics[mode][all_tags]['true']['positive'],
            metrics[mode][all_tags]['false']['positive'],
            metrics[mode][all_tags]['false']['negative'])))

####
def display_value():
   print "Estimating Value by mode"
   for mode in metrics:
       print "\tMode {:19} estimated Value {:6} minutes/operator/day".format(
          mode,
          metrics[mode]['true']['positive'] * value['true']['positive'] +
          metrics[mode]['true']['negative'] * value['true']['negative'] +
          metrics[mode]['false']['positive'] * value['false']['positive'] +
          metrics[mode]['false']['negative'] * value['false']['negative'] )

####
# main starts here


# test results
classifier_obj = ClassifierFactory()
initialize_metrics()

print "Running tests from {}".format(test_datafile)
tests = open(test_datafile, 'r')
for test in tests:
   for classifier_mode in classifier_obj.classifier_modes.keys():
      tl = loads(test)
      test_run(tl['test']['id'],
         classifier_mode,
         tl['test']['search_body'],
         tl['expected_result']['tag'])

tests.close()

display_recall_precision()
print metrics
#display_value()
   
