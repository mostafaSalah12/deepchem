"""
Script that trains multitask models on Tox21 dataset.
"""
from __future__ import print_function
from __future__ import division
from __future__ import unicode_literals

import os
import shutil
import numpy as np
from deepchem.utils.save import load_from_disk
from deepchem.datasets import Dataset
from deepchem import metrics
from deepchem.metrics import Metric
from deepchem.utils.evaluate import Evaluator
from deepchem.models.tensorflow_models.fcnet import TensorflowMultiTaskClassifier
from deepchem.models.tensorflow_models import TensorflowModel
from deepchem.datasets.tox21_datasets import load_tox21


# Only for debug!
np.random.seed(123)

# Set some global variables up top
reload = True
verbosity = "high"
model = "logistic"

base_dir = "/scratch/users/rbharath/tox21_analysis"
if not os.path.exists(base_dir):
  os.makedirs(base_dir)

current_dir = os.path.dirname(os.path.realpath(__file__))
#Make directories to store the raw and featurized datasets.
data_dir = os.path.join(base_dir, "dataset")
train_dir = os.path.join(base_dir, "train_dataset")
valid_dir = os.path.join(base_dir, "valid_dataset")
test_dir = os.path.join(base_dir, "test_dataset")
model_dir = os.path.join(base_dir, "model")

# Load Tox21 dataset
print("About to load Tox21 dataset.")
dataset_file = os.path.join(
    current_dir, "../../datasets/tox21.csv.gz")
dataset = load_from_disk(dataset_file)
print("Columns of dataset: %s" % str(dataset.columns.values))
print("Number of examples in dataset: %s" % str(dataset.shape[0]))

# Do train/valid split.
tox21_tasks, tox21_dataset, transformers = load_tox21(data_dir, reload=reload)
num_train = 7200
X, y, w, ids = tox21_dataset.to_numpy()
X_train, X_valid = X[:num_train], X[num_train:]
y_train, y_valid = y[:num_train], y[num_train:]
w_train, w_valid = w[:num_train], w[num_train:]
ids_train, ids_valid = ids[:num_train], ids[num_train:]

# Not sure if we need to constantly delete these directories...
if os.path.exists(train_dir):
  shutil.rmtree(train_dir)
train_dataset = Dataset.from_numpy(train_dir, X_train, y_train,
                                   w_train, ids_train, tox21_tasks)

if os.path.exists(valid_dir):
  shutil.rmtree(valid_dir)
valid_dataset = Dataset.from_numpy(valid_dir, X_valid, y_valid,
                                   w_valid, ids_valid, tox21_tasks)

# No data transformations for now
transformers = []

# Fit models
tox21_task_types = {task: "Classification" for task in tox21_tasks}

classification_metric = Metric(metrics.roc_auc_score, np.mean,
                               verbosity=verbosity,
                               mode="classification")
params_dict = { 
    "batch_size": 32,
    "nb_epoch": 50,
    "data_shape": train_dataset.get_data_shape(),
    "layer_sizes": [1000],
    "weight_init_stddevs": [1.],
    "bias_init_consts": [1.],
    "dropouts": [.25],
    "num_classification_tasks": len(tox21_tasks),
    "num_classes": 2,
    "penalty": .0,
    "optimizer": "adam",
    "learning_rate": .0003,
}   

# This is for good debug (to make sure nasty state isn't being passed around)
if os.path.exists(model_dir):
  shutil.rmtree(model_dir)
os.makedirs(model_dir)
model = TensorflowModel(tox21_tasks, tox21_task_types, params_dict, model_dir,
                        tf_class=TensorflowMultiTaskClassifier,
                        verbosity=verbosity)

# Fit trained model
model.fit(train_dataset)
model.save()

train_evaluator = Evaluator(model, train_dataset, transformers, verbosity=verbosity)
train_scores = train_evaluator.compute_model_performance([classification_metric])

print("Train scores")
print(train_scores)

valid_evaluator = Evaluator(model, valid_dataset, transformers, verbosity=verbosity)
valid_scores = valid_evaluator.compute_model_performance([classification_metric])

print("Validation scores")
print(valid_scores)
