import re
import numpy as np
import pandas as pd
from tensorflow.keras.preprocessing.sequence import pad_sequences
from tensorflow.keras.preprocessing.text import Tokenizer

# Constants
MAX_SEQUENCE_LENGTH_ATC = 30
MAX_SEQUENCE_LENGTH_ICD = 20

def preprocess_text_for_hyphens(text):
    text = re.sub(r"\s+(\w+-\w+)", r"\1", text)
    text = re.sub(r"\b(\w+)-(\w+)\b", r"\1\2", text)
    return text

def load_tokenizer_from_csv(filename):
    tokenizer_df = pd.read_csv(filename)
    tokenizer = Tokenizer()
    tokenizer.word_index = {row["Word"]: int(row["Index"]) for _, row in tokenizer_df.iterrows()}
    return tokenizer

def preprocess_inputs(row, tokenizer_csv_path):
    tokenizer = load_tokenizer_from_csv(tokenizer_csv_path)

    # Preprocess ATC + ICD
    atc = preprocess_text_for_hyphens(row["ATC"])
    icd = preprocess_text_for_hyphens(row["ICD"])

    seq_atc = tokenizer.texts_to_sequences([atc])
    seq_icd = tokenizer.texts_to_sequences([icd])

    padded_atc = pad_sequences(seq_atc, maxlen=MAX_SEQUENCE_LENGTH_ATC, padding="post")
    padded_icd = pad_sequences(seq_icd, maxlen=MAX_SEQUENCE_LENGTH_ICD, padding="post")

    # Additional features
    sex = int(row["SEX"])
    index_age = int(row["INDEX_AGE"])

    # Combine everything
    combined = np.concatenate([padded_atc, padded_icd, [[sex]], [[index_age]]], axis=1)

    return combined  # shape (1, 51)
