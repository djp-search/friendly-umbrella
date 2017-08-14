#!/usr/bin/env python
"""calculate recall/precision to compare classification methods"""
from datetime import datetime
from elasticsearch import Elasticsearch
from json import loads
from math import log
import random
import abc

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

####
# adapt to specific use case: assuming a CRM application
# true positive => correctly identify the client issue
# false positive => misunderstand the client issue
# false negative => take longer to understand the client issue
value = {'tp': 15, 'fp': -15, 'fn': -10}

####
# Factory classes for candidate classification modes
#


class AbstractClassifier(object):
    __metaclass__ = abc.ABCMeta

    #@abc.abstractmethod
    # def __init__(self, *args, **kwargs):
    # pass

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
            # slice top 5 (so that results deviate from firstmatch)
            for hit in res['hits']['hits'][0:5]:
                if hit['_source']['doc']['tag'] not in tag_scores.keys():
                    tag_scores[hit['_source']['doc']['tag']] = hit['_score']
                else:
                    tag_scores[hit['_source']['doc']['tag']] += hit['_score']
            return sorted(
                tag_scores,
                key=tag_scores.__getitem__,
                reverse=True)[0]
        else:
            return no_tag

# Purely Random Classification


class RandomClassifier(AbstractClassifier):

    @staticmethod
    def tag(search_body):
        return tags[random.randint(0, 2)]

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
        classifier_mode = ClassifierFactory.classifier_modes.get(
            name.lower(), None)
        if classifier_mode:
            return classifier_mode.tag(search_body)
        raise NotImplementedError(
            'The requested classifier has not been implemented')


####
# Dictionary to encapsulate metrics
tags = []
confusion_matrix = dict()

####
# functions

####
# Calculate precision, divide by zero safe


def precision_cm(tp, observed_total):
    if observed_total > 0:
        return tp / float(observed_total)
    else:
        return 1.0
####
# Calculate recall, divide by zero safe


def recall_cm(tp, predicted_total):
    if predicted_total > 0:
        return tp / float(predicted_total)
    else:
        return 0.0

####
####


def get_tag(classifier_mode, search_body):
    return classifier_obj.get_tag_obj(classifier_mode, search_body)

####


def initialize_metrics():
    # populate list of available tags
    res = es.search(
        index=training_index,
        body='{ "query": { "match_all": {} } }')
    for hit in res['hits']['hits']:
        if hit['_source']['doc']['tag'] not in tags:
            tags.append(hit['_source']['doc']['tag'])
    # create a confusion matrix per classifier
    for classifier_mode in classifier_obj.classifier_modes.keys():
        confusion_matrix[classifier_mode] = {
            'predicted': {}, 'observed_total': {}}
        for predicted in tags:
            confusion_matrix[classifier_mode]['predicted'].update(
                {predicted: {'observed': {}, 'total': 0}})
            confusion_matrix[classifier_mode]['observed_total'].update({
                predicted: 0})
            for observed in tags:
                confusion_matrix[classifier_mode]\
                ['predicted'][predicted]['observed'].update({
                    observed: 0})

####


def update_metrics(classifier_mode, observed, predicted):
    confusion_matrix[classifier_mode]['predicted'][predicted]\
        ['observed'][observed] += 1

####


def display_summary(test_id,
                    classifier_mode,
                    short_description,
                    observed,
                    expected_tag):
    print "Test {:2} {:16} {}... p:{:12} o:{}".format(
        test_id,
        classifier_mode,
        short_description,
        expected_tag,
        observed)

####


def test_run(
        test_id,
        classifier_mode,
        search_body,
        expected_tag):

    observed = get_tag(classifier_mode, search_body)
    update_metrics(classifier_mode, observed, expected_tag)
    display_summary(
        test_id,
        classifier_mode,
        search_body['query']['match']['doc.description'][:12],
        observed,
        expected_tag)

####


def calculate_confusion_matrix_totals():
    print """
Calculate/Collate recall + precision"""
    for mode in classifier_obj.classifier_modes.keys():
        # populate the full mode confusion matrix
        for predicted in tags:
            for observed in tags:
                confusion_matrix[mode]['predicted'][predicted]['total'] += \
                    confusion_matrix[mode]['predicted'][predicted]\
                        ['observed'][observed]
                confusion_matrix[mode]['observed_total'][predicted] += \
                    confusion_matrix[mode]['predicted'][observed]\
                        ['observed'][predicted]


####

def display_confusion_matrix():
    print """
Generating Confusion Matrices
Key:
p: predicted
o: observed
p+:predicted total
o+: observed total"""
    for mode in classifier_obj.classifier_modes.keys():
        col_headers = """
{:14}""".format(mode)
        for tag in tags:
            col_headers += " o:{:12}".format(tag)

        print col_headers
        for predicted in tags:
            row = "p:{:9}".format(predicted)
            for observed in tags:
                row += "{:16}".format(
                    confusion_matrix[mode]['predicted'][predicted]\
                        ['observed'][observed])
            row += "  p+:{:10}:{}".format(
                predicted,
                confusion_matrix[mode]['predicted'][predicted]['total'])
            print row

        total_obs = "{:12}".format("")
        for observed in tags:
            total_obs += "  o+:{:8}:{:1} ".format(
                observed,
                confusion_matrix[mode]['observed_total'][observed])
        print total_obs

        sum_all = {'precision': 0, 'recall': 0}
        for tag in tags:
            precision = precision_cm(
                confusion_matrix[mode]['predicted'][tag]['observed'][tag],
                confusion_matrix[mode]['observed_total'][tag])
            recall = recall_cm(
                confusion_matrix[mode]['predicted'][tag]['observed'][tag],
                confusion_matrix[mode]['predicted'][tag]['total'])
            print "{:10} Precision {:5.2f} Recall {:5.2f}".format(
                tag,
                precision,
                recall)
            sum_all['precision'] += precision
            sum_all['recall'] += recall

        print "{:10} Precision {:5.2f} Recall {:5.2f}".format(
            "Mean",
            sum_all['precision'] / len(tags), sum_all['recall'] / len(tags))

####


def display_value():
    print "Estimating Value by mode"
    for mode in classifier_obj.classifier_modes.keys():
        val = 0
        for tag in tags:
            # tp = pred tag obs tag
            # fn = pred tag total -  tp
            # fp = obs_tot tag - tp
            tp = confusion_matrix[mode]['predicted'][tag]['observed'][tag]
            fp = confusion_matrix[mode]['observed_total'][tag] - tp
            fn = confusion_matrix[mode]['predicted'][tag]['total'] - tp
            val += value['tp'] * tp
            val += value['fp'] * fp
            val += value['fn'] * fn
        print "Mode {:19} estimated Value {:6} minutes/operator/day".format(
            mode, val)

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
        test_run(
            tl['test']['id'],
            classifier_mode,
            tl['test']['search_body'],
            tl['predicted']['tag'])

tests.close()

calculate_confusion_matrix_totals()
display_confusion_matrix()
display_value()
