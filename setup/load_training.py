from datetime import datetime
from elasticsearch import Elasticsearch
from json import loads

######
# file:    load_training.py
# date:    20170808 
# status:  draft
# version: 0.1
# authors: djptek
# purpose: index multiple documents to elastic via python api
######
 
# set to your elastic host (in this case VM)
es = Elasticsearch([
    {'host': '192.168.56.101'}
])

training_index = 'training'
training_type = 'example'
training_datafile = '../data/training_docs.json'

# delete the current 'training' index
res = es.indices.delete(index=training_index, ignore=[400, 404])

# check delete OK likewise accept if Index did not exist
if (res.keys()[0] == 'acknowledged' or 
      ('error' in res.keys() and 
       res['error']['root_cause'][0]['type'] == u'index_not_found_exception')):
   print 'populating index [{}]'.format(training_index)

   # open the example docs datafile
   training_docs = open(training_datafile,'r')

   # iterate through the file creating example documents in the index
   for training_doc in training_docs:
      doc = loads(training_doc)   
      res = es.index(index=training_index, doc_type=training_type, body=doc)
      print 'doc [{}] tag [{}] indexed : id [{}]'.format(
         doc['doc']['name'],doc['doc']['tag'],res['_id'])


   # close file on disk
   training_docs.close()
    
else:
   # flag issue with the index
   print 'issue deleting [{}] result [{}]'.format(training_index,str(res))

