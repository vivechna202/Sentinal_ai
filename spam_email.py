
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
import string

# 1. Create a Dummy Dataset
data = {
    'text': [
        "Congratulations! You've won a free iPhone. Click here now!",
        "Meeting reminder for tomorrow at 10 AM.",
        "URGENT: Your account has been compromised. Verify your details.",
        "Hello, just checking in to see how you are doing.",
        "Claim your prize! Limited time offer.",
        "Project update: The new features are almost ready.",
        "Free money! Work from home opportunity.",
        "Can we reschedule our call for next week?",
        "Viagra for sale. Best prices!",
        "Regarding the document you sent earlier."
    ],
    'label': [1, 0, 1, 0, 1, 0, 1, 0, 1, 0] # 1 for spam, 0 for ham
}
df = pd.DataFrame(data)

print("Original DataFrame:")
print(df)
print("\n")

# 2. Text Preprocessing Function
def preprocess_text(text):
    text = text.lower() # Convert to lowercase
    text = "".join([char for char in text if char not in string.punctuation]) # Remove punctuation
    return text

df['processed_text'] = df['text'].apply(preprocess_text)

print("DataFrame after preprocessing:")
print(df)
print("\n")

# Split data into training and testing sets
X_train, X_test, y_train, y_test = train_test_split(
    df['processed_text'], df['label'], test_size=0.3, random_state=42
)

# 3. Feature Extraction using TF-IDF
tfidf_vectorizer = TfidfVectorizer(stop_words='english', max_features=1000) # Limit features for simplicity
X_train_tfidf = tfidf_vectorizer.fit_transform(X_train)
X_test_tfidf = tfidf_vectorizer.transform(X_test)

print("Shape of X_train_tfidf:", X_train_tfidf.shape)
print("Shape of X_test_tfidf:", X_test_tfidf.shape)
print("\n")

# 4. Model Training (Multinomial Naive Bayes)
model = MultinomialNB()
model.fit(X_train_tfidf, y_train)

print("Model trained successfully!\n")

# 5. Model Evaluation
y_pred = model.predict(X_test_tfidf)

print("Model Evaluation:")
print(f"Accuracy: {accuracy_score(y_test, y_pred):.2f}")
print(f"Precision: {precision_score(y_test, y_pred):.2f}")
print(f"Recall: {recall_score(y_test, y_pred):.2f}")
print(f"F1-Score: {f1_score(y_test, y_pred):.2f}")
print("\n")

# 6. Prediction on a new email
def predict_spam(email_text):
    processed_email = preprocess_text(email_text)
    email_tfidf = tfidf_vectorizer.transform([processed_email])
    prediction = model.predict(email_tfidf)[0]
    return "Spam" if prediction == 1 else "Ham"

new_email_1 = "You've won a lottery! Claim your prize now."
new_email_2 = "Hi, can we catch up next week?"
new_email_3 = "Exclusive offer: Get 50% off on all products!"

print(f"'{new_email_1}' is classified as: {predict_spam(new_email_1)}")
print(f"'{new_email_2}' is classified as: {predict_spam(new_email_2)}")
print(f"'{new_email_3}' is classified as: {predict_spam(new_email_3)}")
