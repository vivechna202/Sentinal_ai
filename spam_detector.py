from sklearn.feature_extraction.text import CountVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score

# 1. Sample Data
# In a real-world scenario, you would load a much larger dataset from a CSV, database, etc.
emails = [
    ("Hey, check out this amazing offer!", "spam"),
    ("Meeting at 3 PM today.", "ham"),
    ("URGENT: Your account has been compromised! Your password will expire soon.", "spam"),
    ("Hi, how are you doing?", "ham"),
    ("Win a free iPhone now! Click here to claim.", "spam"),
    ("Regarding our project discussion.", "ham"),
    ("Exclusive discount just for you! Limited time offer.", "spam"),
    ("Can we reschedule our call?", "ham"),
    ("Nigeria lottery winner, claim your prize! Send your bank details.", "spam"),
    ("Please find the report attached.", "ham"),
]

# Separate emails and labels
X = [email[0] for email in emails]  # Email content
y = [email[1] for email in emails]  # Labels (spam/ham)

# 2. Convert text to numerical features using CountVectorizer
# This converts text into a matrix of token counts.
vectorizer = CountVectorizer()
X_vectorized = vectorizer.fit_transform(X)

# 3. Split data into training and testing sets
# For this small dataset, we'll use a simple split.
# In practice, you'd want a larger test set and potentially cross-validation.
X_train, X_test, y_train, y_test = train_test_split(X_vectorized, y, test_size=0.2, random_state=42)

# 4. Train a Multinomial Naive Bayes classifier
# This model is well-suited for classification with discrete features (like word counts).
classifier = MultinomialNB()
classifier.fit(X_train, y_train)

# 5. Make predictions on the test set and evaluate
y_pred = classifier.predict(X_test)
print(f"Accuracy on test set: {accuracy_score(y_test, y_pred):.2f}")

# 6. Predict on new, unseen emails
new_emails = [
    "Claim your prize money! You've won a lottery.",
    "Hello, just following up on our last conversation.",
    "Your bank account needs verification immediately. Click the link.",
    "Project update meeting tomorrow at 10 AM.",
    "Free gift card! Limited offer, act now!"
]

new_emails_vectorized = vectorizer.transform(new_emails)
predictions = classifier.predict(new_emails_vectorized)

print("\nPredictions for new emails:")
for email, prediction in zip(new_emails, predictions):
    print(f"'{email}' is predicted as: {prediction}")
