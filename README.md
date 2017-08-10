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

./expected_output:
output_test_01-06.txt

./scenarios:
test_01-06.json

./setup:
load_training.py

./tests:
recall_precision_comparison.py

To load the training dataset:

$ cd ./setup
$ python load_training.py 

To run the example tests (from top directory):

$ cd ./tests
$ python recall_precision_comparison.py


