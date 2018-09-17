# friendly-umbrella
scripts to compare/rate classification strategies

These scripts connect via the python API to an instance of elasticsearch 
(configured in the scripts) to index training documents and then run 
classification operations in a selection of modes for a fixed test set, 
generating recall/precision statistics to compare performance and 
estimate solution value of each mode.

Content:
./data:
training_docs.json

./docker:
docker-compose.yml

./expected_output:
output_test_01-06.txt

./scenarios:
test_01-06.json

./setup:
load_training.py

./tests:
recall_precision_comparison.py

To spin up a single-node Elasticsearch cluster on 0.0.0.0:9200

$ cd ./docker
$ docker-compose up

To load the training dataset:

$ cd ./setup

$ python load_training.py 

To run the example tests (from top directory):

$ cd ./tests

$ python recall_precision_comparison.py

Definitions in both training_docs.json and test_01-06.json are excerpts copied from Wikipedia under the terms of Wikipedia:Text of Creative Commons Attribution-ShareAlike 3.0 Unported License

