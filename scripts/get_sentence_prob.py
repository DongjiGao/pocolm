#!/usr/bin/env python

# Dongji Gao

# We're using python 3.x style but want it to work in python 2.x

from __future__ import print_function
import argparse
import sys

parser = argparse.ArgumentParser(description="This script evaluate the probabilty of each sentence "
                                             "from data (in text form), given language model in arpa form",
                                 formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument("arpa_lm", type=str,
                    help="Input language model in arpa form")
parser.add_argument("ngram_order", type=int,
                    help="Order of ngram")
parser.add_argument("text_in", type=str,
                    help="Filename of input text file")
parser.add_argument("prob_file", type=str,
                    help="Filename of output probability file")

args = parser.parse_args()

def is_logprob(input):
    if input[0] == "-":
        try:
            float(input[1:])
            return True
        except:
            return False
    else:
        return False

def check_number(model_file, tot_num):
    cur_num = 0
    max_ngram_order = 0
    with open(model_file) as model:
        lines = model.readlines()
        for line in lines[1:]:
            if "=" not in line:
                return (cur_num == tot_num), max_ngram_order
            cur_num += int(line.split("=")[-1])
            max_ngram_order = int(line.split("=")[0].split()[-1])

# This function load language model in arpa form and save in a dictionary for
# computing sentence probabilty of input text file.
def load_model(model_file):
    with open(model_file) as model:
        ngram_dict = {}
        lines = model.readlines()

        # check arpa form
        if lines[0][:-1] != "\\data\\":
            sys.exit("get_sentece_prob.py: Please make sure that language model is in arpa form.")

        # read line
        for line in lines:
            if line[0] == "-":
                line_split = line.split()
                if is_logprob(line_split[-1]):
                    ngram_key = " ".join(line_split[1:-1])
                    if ngram_key in ngram_dict:
                        sys.exit("get_sentence_prob.py: Duplicate ngram in arpa language model: {}.".format(ngram_key))
                    ngram_dict[ngram_key] = (line_split[0], line_split[-1])
                else:
                    ngram_key = " ".join(line_split[1:])
                    if ngram_key in ngram_dict:
                        sys.exit("get_sentence_prob.py: Duplicate ngram in arpa language model: {}.".format(ngram_key))
                    ngram_dict[ngram_key] = (line_split[0],)

    return ngram_dict, len(ngram_dict)

def compute_sublist_prob(sub_list):
    if len(sub_list) == 0:
        sys.exit("get_sentence_prob.py: Ngram substring not found in arpa language model, please check.")

    sub_string = " ".join(sub_list)
    if sub_string in ngram_dict:
        return -float(ngram_dict[sub_string][0][1:])
    else:
        backoff_substring = " ".join(sub_list[:-1])
        backoff_weight = 1.0 if (backoff_substring not in ngram_dict or len(ngram_dict[backoff_substring]) < 2) \
                         else -float(ngram_dict[backoff_substring][1][1:])
        return compute_sublist_prob(sub_list[1:]) + backoff_weight

def compute_begin_prob(sub_list):
    logprob = 0
    for i in range(1, len(sub_list) - 1):
        logprob += compute_sublist_prob(sub_list[:i + 1])
    return logprob
    
# The probability is computed in this way:
# p(word_N | word_N-1 ... word_1) = ngram_dict[word_1 ... word_N][0].
# Here gram_dict is a dictionary stores a tuple corresponding to ngrams.
# The first element of tuple is probablity and the second is backoff probability (if exists).
# If the particular ngram (word_1 ... word_N) is not in the dictionary, then
# p(word_N | word_N-1 ... word_1) = p(word_N | word_(N-1) ... word_2) * backoff_weight(word_(N-1) | word_(N-2) ... word_1) 
# If the sequence (word_(N-1) ... word_1) is not in the dictionary, then the backoff_weight gets replaced with 1.0
# More details can be found in https://cmusphinx.github.io/wiki/arpaformat/
def compute_sentence_prob(sentence, ngram_order):
    sentence_split = sentence.split()
    for i in range(len(sentence_split)):
        if sentence_split[i] not in ngram_dict:
            sentence_split[i] = "<unk>"
    sen_length = len(sentence_split)

    if sen_length < ngram_order:
        return compute_begin_prob(sentence_split)
    else:
        logprob = 0
        begin_sublist = sentence_split[:ngram_order]
        logprob += compute_begin_prob(begin_sublist)

        for i in range(sen_length - ngram_order + 1):
            cur_sublist = sentence_split[i : i + ngram_order]
            logprob += compute_sublist_prob(cur_sublist)

    return logprob
        

def output_result(text_in, output_file, ngram_order):
    with open(args.prob_file, "w") as output_file:
        index = 1
        with open(args.text_in, "r") as text:
            lines = text.readlines()
            for line in lines:
                new_line = "<s> " + line[:-1] + " </s>"
                logprob = compute_sentence_prob(new_line, ngram_order)
                output_file.write("{}\n".format(logprob))
                index += 1
            
if __name__ == "__main__":
    ngram_dict, tot_num = load_model(args.arpa_lm)

    num_valid, max_ngram_order = check_number(args.arpa_lm, tot_num)
    if not num_valid:
        sys.exit("get_sentence_prob.py: Wrong loading model.")
    if args.ngram_order <= 0 or args.ngram_order > max_ngram_order:
        sys.exit("get_sentence_prob.py: " +   
            "Invalid ngram_order (either negative or greater than maximum ngram number ({}) allowed").format(max_ngram_order)

    output_result(args.text_in, args.prob_file, args.ngram_order)
