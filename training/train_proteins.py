import tensorflow as tf
import matplotlib.pyplot as plt
import numpy as np
import time
import os
import argparse

from copy import deepcopy
from sklearn.model_selection import KFold
from kgcnn.data.datasets.PROTEINS import PROTEINSDatset
from kgcnn.io.loader import NumpyTensorList
from kgcnn.utils.models import ModelSelection
from kgcnn.utils.data import save_json_file
from kgcnn.hyper.datasets import DatasetHyperTraining


# Input arguments from command line.
# A hyper-parameter file can be specified to be loaded containing a python dict for hyper.
parser = argparse.ArgumentParser(description='Train a graph network on PROTEINS dataset.')
parser.add_argument("--model", required=False, help="Graph model to train.", default="GIN")
parser.add_argument("--hyper", required=False, help="Filepath to hyper-parameter config.", default="hyper_proteins.py")
args = vars(parser.parse_args())
print("Input of argparse:", args)

# Model identification
model_name = args["model"]
ms = ModelSelection()
make_model = ms.make_model(model_name)

# Hyper-parameter identification
hyper_selection = DatasetHyperTraining(args["hyper"])
hyper = hyper_selection.get_hyper(model_name=model_name)

# Loading PROTEINS Dataset
hyper_data = hyper['data']
dataset = PROTEINSDatset()
data_name = dataset.dataset_name
data_length = dataset.length
if "set_edge_indices_reverse_pairs" in hyper_data:
    dataset.set_edge_indices_reverse_pairs()
k_fold_info = hyper["training"]["KFold"]

# Data-set split
kf = KFold(**k_fold_info)
split_indices = kf.split(X=np.arange(data_length)[:, None])

# Using NumpyTensorList() to make tf.Tensor objects from a list of arrays.
dataloader = NumpyTensorList(*[getattr(dataset, x['name']) for x in hyper['model']['inputs']])
labels = dataset.graph_labels

# Set learning rate and epochs
hyper_train = deepcopy(hyper['training'])
hyper_fit = deepcopy(hyper_train["fit"])
hyper_compile = deepcopy(hyper_train["compile"])
reserved_fit_arguments = ["callbacks", "validation_data"]
hyper_fit_additional = {key: value for key, value in hyper_fit.items() if key not in reserved_fit_arguments}
reserved_compile_arguments = ["loss", "optimizer", "metrics"]
hyper_compile_additional = {key: value for key, value in hyper_compile.items() if
                            key not in reserved_compile_arguments}

epo = hyper_fit['epochs']
epostep = hyper_fit['validation_freq']
batch_size = hyper_fit['batch_size']
train_loss = []
test_loss = []
acc_5fold = []
all_test_index = []
model = None
for train_index, test_index in split_indices:

    # Make the model for current split.
    model = make_model(**hyper['model'])

    # Select train and test data.
    is_ragged = [x['ragged'] for x in hyper['model']['inputs']]
    xtrain, ytrain = dataloader[train_index].tensor(ragged=is_ragged), labels[train_index]
    xtest, ytest = dataloader[test_index].tensor(ragged=is_ragged), labels[test_index]

    # Compile model with optimizer and loss
    optimizer = tf.keras.optimizers.get(deepcopy(hyper_compile['optimizer']))
    loss = tf.keras.losses.get(hyper_compile["loss"]) if "loss" in hyper_compile else 'categorical_crossentropy'
    metrics = [x for x in hyper_compile["metrics"]] if "metrics" in hyper_compile else []
    metrics = metrics + ['categorical_accuracy']
    model.compile(loss=loss,
                  optimizer=optimizer,
                  weighted_metrics=metrics,
                  **hyper_compile_additional)
    print(model.summary())

    # Start and time training
    cbks = [tf.keras.utils.deserialize_keras_object(x) for x in hyper_fit['callbacks']]
    start = time.process_time()
    hist = model.fit(xtrain, ytrain,
                     validation_data=(xtest, ytest),
                     callbacks=cbks,
                     **hyper_fit_additional
                     )
    stop = time.process_time()
    print("Print Time for taining: ", stop - start)

    # Get loss from history
    train_loss.append(np.array(hist.history['categorical_accuracy']))
    val_acc = np.array(hist.history['val_categorical_accuracy'])
    test_loss.append(val_acc)
    acc_valid = np.mean(val_acc[-10:])
    acc_5fold.append(acc_valid)
    all_test_index.append([train_index, test_index])

# Make output directories
hyper_info = deepcopy(hyper["info"])
post_fix = str(hyper_info["postfix"]) if "postfix" in hyper_info else ""
post_fix_file = str(hyper_info["postfix_file"]) if "postfix_file" in hyper_info else ""
os.makedirs(data_name, exist_ok=True)
filepath = os.path.join(data_name, hyper['model']['name'] + post_fix)
os.makedirs(filepath, exist_ok=True)

# Plot training- and test-loss vs epochs for all splits.
plt.figure()
for x in train_loss:
    plt.plot(np.arange(x.shape[0]), x, c='red', alpha=0.85)
for y in test_loss:
    plt.plot((np.arange(len(y)) + 1) * epostep, y, c='blue', alpha=0.85)
plt.scatter([train_loss[-1].shape[0]], [np.mean(acc_5fold)],
            label=r"Test: {0:0.4f} $\pm$ {1:0.4f}".format(np.mean(acc_5fold), np.std(acc_5fold)), c='blue')
plt.xlabel('Epochs')
plt.ylabel('Accuracy')
plt.title('PROTEINS Loss for ' + model_name)
plt.legend(loc='upper right', fontsize='large')
plt.savefig(os.path.join(filepath, model_name + "_acc_proteins" + post_fix_file + ".png"))
plt.show()

# Save keras-model to output-folder.
model.save(os.path.join(filepath, "model"))

# Save original data indices of the splits.
np.savez(os.path.join(filepath, model_name + "_kfold_splits" + post_fix_file + ".npz"), all_test_index)

# Save hyper-parameter again, which were used for this fit.
save_json_file(hyper, os.path.join(filepath, model_name + "_hyper" + post_fix_file + ".json"))
