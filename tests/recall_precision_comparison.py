from datetime import datetime
from elasticsearch import Elasticsearch
from json import loads		

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

class AbstractClassifier(object):
    __metaclass__ = abc.ABCMeta

    #@abc.abstractmethod
    #def __init__(self, *args, **kwargs):
        #pass

    @abc.abstractmethod
    def tag(self, *args, **kwargs):
        pass


class FirstMatchClassifier(AbstractClassifier):
    #def __init__(self, *args, **kwargs):
        # Initialize Facebook OAuth
        #...

    @staticmethod
    def tag(search_body):
       # Tag of highest weighted hit
       res = es.search(index=training_index, body=search_body)
       if int(res['hits']['total']) > 0:
          return res['hits']['hits'][0]['_source']['doc']['tag']
       else:
          return no_tag

class AggregateWeightClassifier(AbstractClassifier):
    #def __init__(self, *args, **kwargs):
        ## Initialize Twitter OAuth
        #...

    @staticmethod
    def tag(search_body):
        # Sum weights on per tag basis and return highest 
        return 'test_tag'


class ClassifierFactory(object):
    tag_classes = {
        'firstmatch': FirstMatchClassifier,
        'aggregateweight': AggregateWeightClassifier
    }

    @staticmethod
    def get_tag_obj(name, search_body):
       tag_class = ClassifierFactory.tag_classes.get(name.lower(), None)
       if tag_class:
          return tag_class.tag(search_body)
       raise NotImplementedError('The requested classifier has not been '\
          'implemented')

classifier_obj = ClassifierFactory()

# test results
summary = {'true': {'positive': 0, 'negative': 0},
    'false': {'positive': 0, 'negative': 0}}

for tag_class in classifier_obj.tag_classes.keys():
   tests = open(test_datafile, 'r')
   for test in tests:
      tl = loads(test)
      print "Test {} {} {}... Result [{}] Expected [{}]".format(
         tl['test']['id'],
         tag_class,
         tl['test']['search_body']['query']['match']['doc.description'][:12],
         classifier_obj.get_tag_obj(tag_class, 
            tl['test']['search_body']),
         tl['expected_result']['tag'])
   
   tests.close()
   
