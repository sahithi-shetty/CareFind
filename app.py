from unittest import result

from flask import Flask, render_template, request ,redirect, session
import pickle
import pandas as pd
from pymongo import MongoClient

app = Flask(__name__)
app.secret_key = "my_secret_key"

# Load trained model
model = pickle.load(open('disease_model.pkl', 'rb'))
client = MongoClient("mongodb://localhost:27017/")

db = client["medibridge"]

predictions_collection = db["predictions"]
users_collection = db["users"]

# Load datasets
training = pd.read_csv('Training.csv')
description_df = pd.read_csv("symptom_Description.csv")
precaution_df = pd.read_csv("symptom_precaution.csv")

# Symptom columns
symptoms_list = training.columns[:-1]


def get_description(disease):
    row = description_df[
        description_df["Disease"] == disease
    ]

    if not row.empty:
        return row.iloc[0]["Description"]

    return "No description available"


def get_precautions(disease):
    row = precaution_df[
        precaution_df["Disease"] == disease
    ]

    if not row.empty:
        return [
            row.iloc[0]["Precaution_1"],
            row.iloc[0]["Precaution_2"],
            row.iloc[0]["Precaution_3"],
            row.iloc[0]["Precaution_4"]
        ]

    return []
def get_specialist(disease):

    specialists = {

        "Fungal infection": "Dermatologist",
        "Allergy": "Dermatologist",
        "Acne": "Dermatologist",
        "Psoriasis": "Dermatologist",

        "Bronchial Asthma": "Pulmonologist",
        "Pneumonia": "Pulmonologist",
        "Tuberculosis": "Pulmonologist",

        "Heart attack": "Cardiologist",
        "Hypertension ": "Cardiologist",

        "Migraine": "Neurologist",
        "Paralysis (brain hemorrhage)": "Neurologist",

        "Diabetes ": "Endocrinologist",
        "Hypothyroidism": "Endocrinologist",
        "Hyperthyroidism": "Endocrinologist",

        "GERD": "Gastroenterologist",
        "Peptic ulcer diseae": "Gastroenterologist",
        "Gastroenteritis": "Gastroenterologist",

        "Arthritis": "Orthopedic",
        "Osteoarthristis": "Orthopedic",
        "Cervical spondylosis": "Orthopedic",

        "Urinary tract infection": "Urologist"
    }

    return specialists.get(disease, "General Physician")

def get_recommended_hospitals(specialist):

    hospitals = {

        "Dermatologist": [
            "Apollo Hospitals",
            "Yashoda Hospitals",
            "CARE Hospitals"
        ],

        "Pulmonologist": [
            "Apollo Hospitals",
            "KIMS Hospitals",
            "CARE Hospitals"
        ],

        "Cardiologist": [
            "Yashoda Hospitals",
            "Apollo Hospitals",
            "Asian Heart Institute"
        ],

        "Neurologist": [
            "KIMS Hospitals",
            "Apollo Hospitals",
            "CARE Hospitals"
        ],

        "Endocrinologist": [
            "Apollo Hospitals",
            "Yashoda Hospitals",
            "CARE Hospitals"
        ],

        "Gastroenterologist": [
            "AIG Hospitals",
            "Apollo Hospitals",
            "Yashoda Hospitals"
        ],

        "Orthopedic": [
            "Sunshine Hospitals",
            "Apollo Hospitals",
            "CARE Hospitals"
        ],

        "Urologist": [
            "Yashoda Hospitals",
            "Apollo Hospitals",
            "KIMS Hospitals"
        ],

        "General Physician": [
            "Apollo Hospitals",
            "Yashoda Hospitals",
            "CARE Hospitals"
        ]
    }

    return hospitals.get(
        specialist,
        ["Apollo Hospitals", "Yashoda Hospitals"]
    )
    
@app.route('/')
def splash():
    return render_template('splash.html')

@app.route('/home')
def home():

    return render_template(
        'index.html',
        symptoms=symptoms_list,
        user=session.get('user'),
        name=session.get('name')
    )


@app.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':

        email = request.form['email']
        password = request.form['password']

        user = users_collection.find_one({

            "email": email,
            "password": password

        })

        if user:

            session['user'] = user['email']
            session['name'] = user['name']

            return redirect('/home')

        return "Invalid Email or Password"

    return render_template('login.html')

@app.route('/logout')
def logout():

    session.clear()

    return redirect('/login')


@app.route('/signup', methods=['GET', 'POST'])
def signup():

    if request.method == 'POST':

        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        print("Signup Route Hit")
        print(name, email, password)

        users_collection.insert_one({
            "name": name,
            "email": email,
            "password": password
        })

        return redirect('/login')

    return render_template('signup.html')

@app.route('/hospitals')
def hospitals():

    specialist = request.args.get(
        'specialist',
        'General Physician'
    )

    recommended_hospitals = get_recommended_hospitals(
        specialist
    )

    return render_template(
        'hospitals.html',
        specialist=specialist,
        recommended_hospitals=recommended_hospitals
    )

@app.route('/history')
def history():

    if 'user' not in session:
        return redirect('/login')

    user_email = session.get('user')

    predictions = list(
        predictions_collection.find(
            {"user_email": user_email}
        ).sort("_id", -1)
    )

    return render_template(
        'history.html',
        predictions=predictions
    )

@app.route('/predict', methods=['POST'])
def predict():

    # Create empty symptom vector
    input_data = [0] * len(symptoms_list)

    # Get selected symptoms
    selected_symptoms = request.form.getlist('symptoms')
    if len(selected_symptoms) == 0:

        return render_template(
            'index.html',
            symptoms=symptoms_list,
            error="Please select at least one symptom.",
            user=session.get('user'),
            name=session.get('name')
        )

    # Convert selected symptoms into binary vector
    for symptom in selected_symptoms:

        if symptom in symptoms_list:

            index = list(symptoms_list).index(symptom)

            input_data[index] = 1

    # Get probabilities
    probabilities = model.predict_proba([input_data])[0]

    classes = model.classes_

    # Combine disease names with probabilities
    results = list(zip(classes, probabilities))

    # Sort by highest probability
    results = sorted(
        results,
        key=lambda x: x[1],
        reverse=True
    )

    # Top 3 diseases
    # Top 3 diseases
    top3 = results[:3]

# Best prediction
    prediction = top3[0][0]

# Extra information
    description = get_description(prediction)

    precautions = get_precautions(prediction)

    specialist = get_specialist(prediction)

    recommended_hospitals = get_recommended_hospitals(
    specialist
)

#Save to MongoDB
    print("Logged User:", session.get('user'))
    result = predictions_collection.insert_one({
    "selected_symptoms": selected_symptoms,
    "predicted_disease": prediction,
    "specialist": specialist,
    "user_email": session.get('user'),

    "top3_predictions": [
        {
            "disease": disease,
            "confidence": float(score * 100)
        }
        for disease, score in top3
    ]
})
    

    #print("Inserted ID:", result.inserted_id)

    return render_template(
    'index.html',
    symptoms=symptoms_list,
    prediction=prediction,
    description=description,
    precautions=precautions,
    specialist=specialist,
    recommended_hospitals=recommended_hospitals,
    top3=top3,
    user=session.get('user'),
    name=session.get('name')
    )


if __name__ == '__main__':
    app.run(debug=True)