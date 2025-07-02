import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.feature_extraction.text import TfidfVectorizer
import joblib

# Cargar CSV localmente
df = pd.read_csv("dataset-tickets-multi-lang-4-20k.csv")


df['text'] = df['subject'].fillna('') + ' ' + df['body'].fillna('')


def map_queue_to_category(queue: str) -> str:
    queue = queue.lower()
    if "technical support" in queue or "it support" in queue:
        return "technical"
    elif "billing" in queue or "payment" in queue:
        return "billing"
    else:
        return "general"


df['category'] = df['queue'].apply(map_queue_to_category)


X_train, X_test, y_train, y_test = train_test_split(df['text'], df['category'], test_size=0.2, random_state=42)


pipeline = Pipeline([
    ('tfidf', TfidfVectorizer(max_features=10000)),
    ('clf', LogisticRegression(max_iter=200))
])

pipeline.fit(X_train, y_train)

print("¿idf_ existe?:", hasattr(pipeline.named_steps['tfidf'], 'idf_'))
print("Tamaño X_train:", len(X_train))
print("Primeros elementos X_train:", X_train[:3])
print(pipeline.named_steps["tfidf"].__dict__.keys())


joblib.dump(pipeline, 'models/pipeline.joblib')

print("✅ Complete pipeline trained and saved.")
print("🎯 Accuracy in test:", pipeline.score(X_test, y_test))
