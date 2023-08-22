# -*- coding: utf-8 -*-
"""Chatbot_with_bert.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/11Uk5IzDIPxzl7kTYXvo2v9XqXjmgZwEy
"""

!pip install transformers[sentencepiece]
!pip install transformers[torch]
!pip install simpletransformers
!pip install datasets
!pip install fugashi ipadic
!pip install unidic_lite
!apt-get install git-lfs
!pip install wandb

import json
import glob
def read_json_file(file_path):
    with open(file_path) as f:
        data = json.load(f)
    return data

bn_train_files = glob.glob("/content/train_merged.json")
bn_val_files = glob.glob("/content/velid_merged.json")

from itertools import chain

bn_train_files

bn_val_files

import json

def read_json_file(file_path, encoding='utf-8'):
    with open(file_path, 'r', encoding=encoding) as file:
        data = json.load(file)
    return data

bn_train_data_list = list(map(lambda x: read_json_file(x, encoding='utf-16'), bn_train_files))
bn_val_data_list = list(map(lambda x: read_json_file(x, encoding='utf-16'), bn_val_files))


#bn_train_data_list= list(map(read_json_file, bn_train_files))
#bn_val_data_list= list(map(read_json_file, bn_val_files))
bn_train_list = [i["data"] for i in bn_train_data_list]
bn_val_list = [i["data"] for i in bn_val_data_list]
bn_train_data = list(chain(* bn_train_list))
bn_val_data = list(chain(* bn_val_list))

len(bn_val_data)

len(bn_train_data)

import random
all_data = bn_train_data + bn_val_data
#all_data = bn_train_data
random.shuffle(all_data)
len(all_data)

percentage = int((len(all_data)*90)/100)
print(percentage)
bn_train_data = all_data[:percentage]
bn_val_data = all_data[percentage:]

from pprint import pprint
for i in bn_train_data[:1]:
    pprint(i)

from transformers import AutoModelForQuestionAnswering, AutoTokenizer
import logging
from simpletransformers.question_answering import QuestionAnsweringModel,  QuestionAnsweringArgs

model = AutoModelForQuestionAnswering.from_pretrained("saiful9379/Bangla_Roberta_Question_and_Answer")
tokenizer = AutoTokenizer.from_pretrained("saiful9379/Bangla_Roberta_Question_and_Answer", use_fast=True)
# tokenizer.do_lower_case = True

text = 'রাগবি লিগটি বেশিরভাগ নিউজিল্যান্ড এবং অস্ট্রেলিয়ায় বসবাসকারী সামোয়ানরা খেলে, প্রশংসাপত্র প্রয়োজন এনআরএল, সুপার লিগ এবং ঘরোয়া '

string_tokenized = tokenizer.encode(text)
print(string_tokenized)

def data_preprocessing(dataset):
    contexts, questions, answers = [], [], []
    for group in dataset:
        for passage in group['paragraphs']:
            context = passage['context']
            for qa in passage['qas']:
                question = qa['question']
                for answer in qa['answers']:
                    contexts.append(context)
                    questions.append(question)
                    answers.append(answer)

    return contexts, questions, answers

from functools import partial
def generated_dict(tokenized_squad):
    tokenized_squad_data = list(map(lambda x: {
            "input_ids": x[0],
            "attention_mask": x[1],
            "start_positions": x[2],
            "end_positions": x[3]
        },
        zip(
            tokenized_squad["input_ids"],
            tokenized_squad["attention_mask"],
            tokenized_squad["start_positions"],
            tokenized_squad["end_positions"]
        )
    ))
    return tokenized_squad_data

train_contexts, train_questions, train_answers = data_preprocessing(bn_train_data)
test_contexts, test_questions, test_answers = data_preprocessing(bn_val_data)
print(len(train_answers))
squad_train = {'answers': train_answers,'context': train_contexts, 'question': train_questions}
squad_test = {'answers': test_answers,'context': test_contexts, 'question': test_questions}

squad_train["answers"][:10]

squad_train["question"][:10]

squad_train["context"][:10]

def preprocess_function(examples, tokenizer):
#     print(examples.keys())
#     exit()
    questions = [q.strip() for q in examples["question"]]
    inputs = tokenizer(
        questions,
        examples["context"],
        max_length=512,
        truncation="only_second",
        return_offsets_mapping=True,
        padding="max_length",
    )

    offset_mapping = inputs.pop("offset_mapping")
    answers = examples["answers"]
    start_positions = []
    end_positions = []

    for i, offset in enumerate(offset_mapping):
        answer = answers[i]
#         print(answer)
        start_char = answer["answer_start"]
        end_char = answer["answer_start"] + len(answer["text"])
        sequence_ids = inputs.sequence_ids(i)

        # Find the start and end of the context
        idx = 0
        while sequence_ids[idx] != 1:
            idx += 1
        context_start = idx
        while sequence_ids[idx] == 1:
            idx += 1
        context_end = idx - 1

        # If the answer is not fully inside the context, label it (0, 0)
        if offset[context_start][0] > end_char or offset[context_end][1] < start_char:
              start_positions.append(0)
              end_positions.append(0)
        else:
            # Otherwise it's the start and end token positions
            idx = context_start
            while idx <= context_end and offset[idx][0] <= start_char:
                idx += 1
            start_positions.append(idx - 1)

            idx = context_end
            while idx >= context_start and offset[idx][1] >= end_char:
                idx -= 1
            end_positions.append(idx + 1)

    inputs["start_positions"] = start_positions
    inputs["end_positions"] = end_positions
    return inputs

tokenized_squad_train = preprocess_function(squad_train,tokenizer)
tokenized_squad_test = preprocess_function(squad_test,tokenizer)

from functools import partial
def generated_dict(tokenized_squad):
    tokenized_squad_data = list(map(lambda x: {
            "input_ids": x[0],
            "attention_mask": x[1],
            "start_positions": x[2],
            "end_positions": x[3]
        },
        zip(
            tokenized_squad["input_ids"],
            tokenized_squad["attention_mask"],
            tokenized_squad["start_positions"],
            tokenized_squad["end_positions"]
        )
    ))
    return tokenized_squad_data

add_part = partial(generated_dict)
tokenized_squad_train_new = add_part(tokenized_squad_train)
tokenized_squad_val_new = add_part(tokenized_squad_test)

for i in tokenized_squad_train_new[:1]:
    print(i)

len(tokenized_squad_train_new)

len(tokenized_squad_train_new)

import torchvision.transforms as transforms
transform = transforms.Compose([
    transforms.Resize((100, 100)),
    transforms.ToTensor()
])

!pip install koila

from koila import lazy
input = lazy(input, batch=0)

!pip install --upgrade transformers

from transformers import TrainingArguments, Trainer, DefaultDataCollator
import wandb

data_collator = DefaultDataCollator()

wandb.init(project="Question Answer Application", name="MyTrainingRun")

training_args = TrainingArguments(
    output_dir="./results",
    evaluation_strategy="steps",
    learning_rate=2e-5,
    per_device_train_batch_size=20,
    per_device_eval_batch_size=15,
    num_train_epochs=300,
    weight_decay=0.01,
    eval_steps=1000,
    save_total_limit=1,
    save_strategy="steps",  # Save checkpoints during evaluation steps
    save_steps=1000,  # Save checkpoints every 1000 evaluation steps
)

trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=tokenized_squad_train_new,
    eval_dataset=tokenized_squad_val_new,
    tokenizer=tokenizer,
    data_collator=data_collator,
)

# Start the training loop
for epoch in range(training_args.num_train_epochs):
    trainer.train()

    # Log training loss using WandB
    wandb.log({"epoch": epoch, "train_loss": trainer.state.log_history[-1]["loss"]})
    # Log training loss using WandB with error handling
    train_loss = trainer.state.log_history[-1].get("loss", None)
    if train_loss is not None:
       wandb.log({"epoch": epoch, "train_loss": train_loss})
    else:
       print("Training loss not found in log history.")


    # Perform evaluation and log metrics
    evaluation_metrics = trainer.evaluate()
    wandb.log({"epoch": epoch, "validation_loss": evaluation_metrics["eval_loss"]})
    wandb.log({"epoch": epoch, "correct": evaluation_metrics["eval_correct"]})
    wandb.log({"epoch": epoch, "incorrect": evaluation_metrics["eval_incorrect"]})

# Finish the WandB run
wandb.finish()

import os
import torch
model_dir = '/content/drive/MyDrive'  # Update this path
os.makedirs(model_dir, exist_ok=True)

model_path = os.path.join(model_dir, 'model.pth')
torch.save(model.state_dict(), model_path)

from transformers import AutoModelForQuestionAnswering, AutoTokenizer, pipeline
import torch

# Load the model state dictionary
model_dir = '/content/drive/MyDrive'
model_path = os.path.join(model_dir, 'model.pth')
model_state_dict = torch.load(model_path)

# Initialize the model with the saved state dictionary
model = AutoModelForQuestionAnswering.from_pretrained("saiful9379/Bangla_Roberta_Question_and_Answer", state_dict=model_state_dict)
tokenizer = AutoTokenizer.from_pretrained("saiful9379/Bangla_Roberta_Question_and_Answer")

# ... (rest of your code for inference)

# Continue with your inference code
for answer, context, question in zip(squad_test["answers"], squad_test["context"], squad_test["question"]):
    print("context:", context)
    print("question:", question)
    print("gt:", answer)
    QA = pipeline('question-answering', model=model, tokenizer=tokenizer)
    QA_input = {'question': question, 'context': context}
    prediction = QA(QA_input)

    print(prediction)

    print("=" * 40)

from transformers import AutoModelForQuestionAnswering,AutoTokenizer,pipeline

model = AutoModelForQuestionAnswering.from_pretrained("saiful9379/Bangla_Roberta_Question_and_Answer")
tokenizer = AutoTokenizer.from_pretrained("saiful9379/Bangla_Roberta_Question_and_Answer")

for answer, context, question in zip(squad_test["answers"], squad_test["context"], squad_test["question"]):
    print("context:", context)
    print("question:", question)
    print("gt:", answer)
    QA = pipeline('question-answering', model=model, tokenizer=tokenizer)
    QA_input = {'question': question,'context':context}
    prediction = QA(QA_input)

    print(prediction)

    print("="*40)

import json
import glob
import collections
from itertools import chain
from typing import Any, Dict, Iterator, List, Tuple, Union
from transformers import AutoModelForQuestionAnswering, AutoTokenizer, pipeline

def read_json_file(file_path):
    with open(file_path) as f:
        data = json.load(f)
    return data

def data_preprocessing(dataset):
    contexts, questions, answers = [], [], []
    for group in dataset:
        for passage in group['paragraphs']:
            context = passage['context']
            for qa in passage['qas']:
                question = qa['question']
                for answer in qa['answers']:
                    contexts.append(context)
                    questions.append(question)
                    answers.append(answer)

    return contexts, questions, answers

model = AutoModelForQuestionAnswering.from_pretrained("saiful9379/Bangla_Roberta_Question_and_Answer")
tokenizer = AutoTokenizer.from_pretrained("saiful9379/Bangla_Roberta_Question_and_Answer", use_fast=True)

import json

def read_json_file(file_path, encoding='utf-8'):
    with open(file_path, 'r', encoding=encoding) as file:
        data = json.load(file)
    return data

bn_val_files = glob.glob("/content/velid_merged.json")
bn_val_list = [i["data"] for i in bn_val_data_list]
bn_val_data_list = list(map(lambda x: read_json_file(x, encoding='utf-16'), bn_val_files))
bn_val_data = list(chain(* bn_val_list))

test_contexts, test_questions, test_answers = data_preprocessing(bn_val_data)
squad_test = {'answers': test_answers,'context': test_contexts, 'question': test_questions}

ground_truth_values, prediction_values = [], []
for answer, context, question in zip(squad_test["answers"], squad_test["context"], squad_test["question"]):
    QA = pipeline('question-answering', model=model, tokenizer=tokenizer)
    QA_input = {'question': question,'context':context}
    prediction = QA(QA_input)
    gt = answer["text"]
    pt = prediction["answer"]
    ground_truth_values.append(gt)
    prediction_values.append(pt)

ground_train_truth, prediction_train_values = [], []
for answer, context, question in zip(squad_train["answers"], squad_train["context"], squad_train["question"]):
    QA = pipeline('question-answering', model=model, tokenizer=tokenizer)
    QA_input = {'question': question,'context':context}
    prediction = QA(QA_input)
    gt = answer["text"]
    pt = prediction["answer"]
    ground_truth_values.append(gt)
    prediction_values.append(pt)

import collections
from typing import List

def compute_f1_score(ground_truth_values: List[str],
                     prediction_values: List[str]) -> float:
    '''Compute f1 score comparing two list of values.'''
    common = (
        collections.Counter(prediction_values) &
        collections.Counter(ground_truth_values))
    num_same = sum(common.values())

    # Calculate accuracy
    accuracy = num_same / len(ground_truth_values)

    # No answer case.
    if not ground_truth_values or not prediction_values:
       return {"exact_match": int(ground_truth_values == prediction_values),
                "f1_score": 0.0,
                "precision": 0.0,
                "recall": 0.0,
                "accuracy": 0.0}

    if num_same == 0:
        return 0.

    precision = 1.0 * num_same / len(prediction_values)
    recall = 1.0 * num_same / len(ground_truth_values)
    f1_score = (2 * precision * recall) / (precision + recall)
    #accuracy = num_same / len(ground_truth_values)

    return  precision, recall,f1_score, accuracy

f1_score, precision, recall, accuracy = compute_f1_score(ground_truth_values, prediction_values)
print("f1_score : ", f1_score)
print("precision : ", precision)
print("recall : ", recall)
print("accuracy : ", accuracy)

import collections
from typing import List

def compute_metrics(ground_truth_values: List[str],
                    prediction_values: List[str]) -> tuple:
    '''Compute F1 score, precision, recall, and accuracy comparing two lists of values.'''
    num_common = sum(1 for value in prediction_values if value in ground_truth_values)

    if not ground_truth_values and not prediction_values:
        accuracy = 1.0
        precision = recall = f1_score = 1.0
    elif not ground_truth_values or not prediction_values:
        accuracy = 0.0
        precision = recall = f1_score = 0.0
    else:
        accuracy = num_common / len(ground_truth_values)
        precision = num_common / len(prediction_values)
        recall = num_common / len(ground_truth_values)
        f1_score = (2 * precision * recall) / (precision + recall)

    return f1_score, precision, recall, accuracy


f1_score, precision, recall, accuracy = compute_metrics(ground_truth_values, prediction_values)

print("F1 Score:", f1_score)
print("Precision:", precision)
print("Recall:", recall)
print("Accuracy:", accuracy)

# Assuming you have already collected ground truth and prediction values
# ground_truth_values and prediction_values

def calculate_em_score(ground_truth_values, prediction_values):
    num_exact_matches = 0

    for gt, pt in zip(ground_truth_values, prediction_values):
        # Convert both ground truth and predicted answers to lowercase for case-insensitive comparison
        gt = gt.lower()
        pt = pt.lower()

        # Check if the predicted answer exactly matches the ground truth
        if gt == pt:
            num_exact_matches += 1

    em_score = num_exact_matches / len(ground_truth_values)
    return em_score

if __name__ == "__main__":
    # Assuming you have collected ground truth and prediction values
    # ground_truth_values and prediction_values

    em_score = calculate_em_score(ground_truth_values, prediction_values)
    print("EM Score:", em_score)

from sklearn.metrics import confusion_matrix


def compute_confusion_matrix_elements(ground_truth_values, prediction_values):
    # Binary classification: Exact Match (EM) vs. Non-Exact Match (Non-EM)
    # For simplicity, we'll convert all exact matches to 1 and non-exact matches to 0
    y_true = [1 if gt == pt else 0 for gt, pt in zip(ground_truth_values, prediction_values)]
    y_pred = [1 if pt == 'no_answer' else 0 for pt in prediction_values]

    # Compute the confusion matrix
    confusion = confusion_matrix(y_true, y_pred)

    # Extract confusion matrix elements
    tn, fp, fn, tp = confusion.ravel()
    return tn, fp, fn, tp

if __name__ == "__main__":
    # Assuming you have collected ground truth and predicted answers for the test dataset
    # ground_truth_values and prediction_values

    # Calculate confusion matrix elements
    tn, fp, fn, tp = compute_confusion_matrix_elements(ground_truth_values, prediction_values)

    # Print the confusion matrix elements
    print("True Negatives:", tn)
    print("False Positives:", fp)
    print("False Negatives:", fn)
    print("True Positives:", tp)

from transformers import AutoModelForQuestionAnswering, AutoTokenizer
import torch

# Load the saved model state dictionary
model_dir = '/content/drive/MyDrive'
model_path = os.path.join(model_dir, 'model.pth')
model_state_dict = torch.load(model_path)

# Load the tokenizer
tokenizer = AutoTokenizer.from_pretrained("saiful9379/Bangla_Roberta_Question_and_Answer")

# Initialize the model with the loaded state dictionary
model = AutoModelForQuestionAnswering.from_pretrained("saiful9379/Bangla_Roberta_Question_and_Answer", state_dict=model_state_dict)

# Define your input for question answering
context = "Bangladesh is a country in South Asia. Its capital is Dhaka."
question = "What is the capital of Bangladesh?"

# Tokenize inputs
inputs = tokenizer.encode_plus(question, context, add_special_tokens=True, return_tensors="pt")

# Get the model's predicted start and end indices
start_logits, end_logits = model(**inputs).start_logits, model(**inputs).end_logits

# Find the indices with maximum logits
start_idx = torch.argmax(start_logits)
end_idx = torch.argmax(end_logits)

# Extract the full context as the answer
answer = tokenizer.decode(inputs["input_ids"][0][start_idx:end_idx + 1])

# Print the answer
print("Answer:", answer)

!pip install gradio

import gradio as gr

for answer, context, question in zip(squad_test["answers"], squad_test["context"], squad_test["question"]):
    QA = pipeline('question-answering', model=model, tokenizer=tokenizer)
    QA_input = {'question': question,'context':context}
    prediction = QA(QA_input)
    gt = answer["text"]
    pt = prediction["answer"]

    print("Context : ", context)
    print("Question : ", question)
    print("GT Answer :", gt)
    print("Prediction : ", pt)
    print("="*40)

interface = gr.Interface.from_pipeline(question_answerer,
    title = title,
    theme = "peach",
    examples = [[context, question]]).launch()