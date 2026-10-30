import re
import nltk
from nltk.corpus import stopwords
from nltk.stem import PorterStemmer

# Download the small NLTK stopword list if it is not available.
try:
    STOP_WORDS = set(stopwords.words("english"))
except LookupError:
    nltk.download("stopwords")
    STOP_WORDS = set(stopwords.words("english"))

stemmer = PorterStemmer()

def preprocess_text(text):
    """Lowercase, remove punctuation, tokenize, remove stopwords and stem."""
    text = str(text).lower()
    text = re.sub(r"http\S+|www\S+", " ", text)       # remove URLs
    text = re.sub(r"[^a-z\s]", " ", text)             # remove punctuation/numbers
    tokens = text.split()                             # simple tokenization
    tokens = [word for word in tokens if word not in STOP_WORDS]
    tokens = [stemmer.stem(word) for word in tokens]
    return " ".join(tokens)
