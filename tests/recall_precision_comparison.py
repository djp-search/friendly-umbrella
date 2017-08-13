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
mean_tags = 'mean_tags'
random.seed(123)

es = Elasticsearch([
    {'host': '192.168.56.101'}
])

####
# adapt to specific use case: assuming a CRM application
# true positive => correctly identify the client issue
# false positive => misunderstand the client issue
# false negative => take longer to understand the client issue
value = {'tp': 10, 'fp': -15, 'fn': -10}

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
        #'random': RandomClassifier,
        #'fixed': FixedClassifier
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
#metrics = dict()
confusion_matrix = dict()

####
# functions

####
#### Calculate precision, divide by zero safe
#def precision (tp, fp, fn):
#    if tp + fp > 0:
#        return str(tp/float(tp+fp))
#    elif fn > 0:
#        return '0.0'
#    else:
#        return '1.0'
#####
#### Calculate recall, divide by zero safe
#def recall (tp, fp, fn):
#    if tp + fn > 0:
#        return str(tp/float(tp+fn))
#    elif fp > 0:
#        return '0.0'
#    else:
#        return '1.0'
#
#####
### Calculate precision, divide by zero safe
def precision_cm (tp, observed_total):
    if observed_total > 0:
        return tp/float(observed_total)
    elif fn > 0:
        return 0.0
    else:
        return 1.0
####
### Calculate recall, divide by zero safe
def recall_cm(tp, predicted_total):
    if predicted_total > 0:
        return tp/float(predicted_total)
    elif fp > 0:
        return 0.0
    else:
        return 1.0

####
####
def get_tag(classifier_mode,search_body):
   return classifier_obj.get_tag_obj(classifier_mode, search_body)

####
def initialize_metrics():
   # populate list of available tags
   res = es.search(index=training_index,body='{ "query": { "match_all": {} } }')
   for hit in res['hits']['hits']:
      if hit['_source']['doc']['tag'] not in tags:
         tags.append(hit['_source']['doc']['tag'])
   # create a true/false positive/negative confusion matrix per classifier
   for classifier_mode in classifier_obj.classifier_modes.keys():
      #metrics[classifier_mode] = dict()
      #for tag in tags:
      #   metrics[classifier_mode][tag] = {
      #      'false': {'positive': 0, 'negative': 0}, 
      #      'true': {'positive': 0, 'negative': 0}}
      # generate the full confusion matrix per classifer
      confusion_matrix[classifier_mode] = {'predicted':{},'observed_total':{}}
      for predicted in tags:
         confusion_matrix[classifier_mode]['predicted'].update({predicted:{'observed':{},'total':0}})
         confusion_matrix[classifier_mode]['observed_total'].update({predicted:0})
         for observed in tags:
            confusion_matrix[classifier_mode]['predicted'][predicted]['observed'].update({observed:0})

####
def update_metrics(classifier_mode,test_result,expected_result):
   #if test_result == expected_result:
   #   metrics[classifier_mode][test_result]['true']['positive'] += 1
   #   for tag in tags:
   #      if tag != test_result:
   #         metrics[classifier_mode][tag]['true']['negative'] += 1
   #else:
   #   metrics[classifier_mode][expected_result]['false']['negative'] += 1
   #   metrics[classifier_mode][test_result]['false']['positive'] += 1
   #   for tag in tags:
   #      if tag not in [test_result,expected_result]:
   #         metrics[classifier_mode][tag]['true']['negative'] += 1
   confusion_matrix[classifier_mode]['predicted'][expected_result]['observed'][test_result] += 1

####
def display_summary(test_id,
   classifier_mode,
   short_description,
   test_result,
   expected_tag):
   print "Test {:2} {:16} {}... Result {:12} Expected {}".format(
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
   print "\nCalculate/Collate recall + precision"
   for mode in classifier_obj.classifier_modes.keys():
      #metrics[mode][mean_tags] = {'sum':{'precision':0,'recall':0},'mean':{'precision':0,'recall':0},'count':len(tags)}
      #for tag in tags:
      #   metrics[mode][tag].update({'precision':
      #      float(precision(metrics[mode][tag]['true']['positive'],
      #         metrics[mode][tag]['false']['positive'],
      #         metrics[mode][tag]['false']['negative'])),
      #      'recall':
      #      float(recall(metrics[mode][tag]['true']['positive'],
      #         metrics[mode][tag]['false']['positive'],
      #         metrics[mode][tag]['false']['negative']))})
      #   for key in 'precision','recall':
      #      metrics[mode][mean_tags]['sum'][key] += metrics[mode][tag][key]
      #   print "Mode {:19} Tag {:12} Precision {:5.2f} Recall {:5.2f}".format(
      #      mode,
      #      tag,
      #      metrics[mode][tag]['precision'],
      #      metrics[mode][tag]['recall'])
      #for key in 'precision','recall':
      #   metrics[mode][mean_tags]['mean'][key] += metrics[mode][mean_tags]['sum'][key]/metrics[mode][mean_tags]['count']
      #print "Mode {:19} Tag {:12} Precision {:5.2f} Recall {:5.2f}".format(
      #      mode,
      #      "Mean of all",
      #      metrics[mode][mean_tags]['mean']['precision'],
      #      metrics[mode][mean_tags]['mean']['recall']) 
      
      # populate the full mode confusion matrix
      for predicted in tags:
         for observed in tags:
            confusion_matrix[mode]['predicted'][predicted]['total'] += \
               confusion_matrix[mode]['predicted'][predicted]['observed'][observed]
            confusion_matrix[mode]['observed_total'][predicted] += \
               confusion_matrix[mode]['predicted'][observed]['observed'][predicted]
      

####

def display_confusion_matrix():
   print "\nGenerating Confusion Matrices"
   for mode in classifier_obj.classifier_modes.keys():
      col_headers = "{:16}".format(mode)
      for tag in tags:
         col_headers += "obs:{:12}".format(tag)
      print col_headers
      for predicted in tags:
         row = "pred:{:11}".format(predicted)
         for observed in tags:
            row += "{:16}".format(confusion_matrix[mode]['predicted'][predicted]['observed'][observed])
         row += "  tot:{:10}:{}".format(predicted,confusion_matrix[mode]['predicted'][predicted]['total'])
         print row
      total_obs = "{:16}".format("")
      for observed in tags:
         total_obs += "tot:{:8}:{:2} ".format(observed,confusion_matrix[mode]['observed_total'][observed])
      print total_obs
      sum_all = {'precision':0,'recall':0}
      for tag in tags:
         precision = precision_cm(confusion_matrix[mode]['predicted'][tag]['observed'][tag],confusion_matrix[mode]['observed_total'][tag])
         recall = recall_cm(confusion_matrix[mode]['predicted'][tag]['observed'][tag],confusion_matrix[mode]['predicted'][tag]['total'])
         print "{:10} Precision {:5.2f} Recall {:5.2f}".format(tag,
            precision,
            recall)
         sum_all['precision'] += precision
         sum_all['recall'] += recall
      print "{:10} Precision {:5.2f} Recall {:5.2f}\n".format("Mean",
         sum_all['precision']/len(tags),sum_all['recall']/len(tags))

####
def display_value():
   print "\nEstimating Value by mode"
   for mode in classifier_obj.classifier_modes.keys():
      val = 0
      for tag in tags:
         #tp = pred tag obs tag
         #fn = pred tag total -  tp
         #fp = obs_tot tag - tp
         tp = confusion_matrix[mode]['predicted'][tag]['observed'][tag]
         fp = confusion_matrix[mode]['observed_total'][tag] - tp
         fn = confusion_matrix[mode]['predicted'][tag]['total'] - tp 
         val += value['tp'] * tp
         val += value['fp'] * fp
         val += value['fn'] * fn
      print "Mode {:19} estimated Value {:6} minutes/operator/day".format(
          mode,val)

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
display_confusion_matrix()
display_value()
   
