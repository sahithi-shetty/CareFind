from unittest import result

from flask import Flask, render_template, request ,redirect, session
import pickle
import pandas as pd
from pymongo import MongoClient
from collections import Counter
from datetime import datetime
import os
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)
app.secret_key = "my_secret_key"

# Load trained model
model = pickle.load(open('disease_model.pkl', 'rb'))
client = MongoClient(
    os.getenv("MONGO_URI")
)

db = client["medibridge"]

predictions_collection = db["predictions"]
users_collection = db["users"]
contacts_collection = db["contacts"]
feedback_collection = db["feedback"]

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
hospital_details = {

    "Apollo Hospitals": {
        "website": "https://www.apollohospitals.com/contact-us",
        "phone": "+91 1860 500 1066"
    },

    "Yashoda Hospitals": {
        "website": "https://www.yashodahospitals.com/contact-us/",
        "phone": "+91 40 4567 4567"
    },

    "CARE Hospitals": {
        "website": "https://www.carehospitals.com/contact-us",
        "phone": "+91 40 6810 6585"
    },

    "KIMS Hospitals": {
        "website": "https://www.kimshospitals.com/contact-us",
        "phone": "+91 40 4488 5000"
    },

    "AIG Hospitals": {
        "website": "https://www.aighospitals.com/contact",
        "phone": "+91 40 4244 4222"
    },

    "Sunshine Hospitals": {
        "website": "https://www.kimssunshine.co.in/contact-us/",
        "phone": "+91 40 4455 0000"
    },

    "Asian Heart Institute": {
        "website": "https://asianheartinstitute.org/contact-us",
        "phone": "+91 22 6698 6666"
    }
}
    
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

            return redirect('/about')

        return "Invalid Email or Password"

    return render_template('login.html')

@app.route('/logout')
def logout():

    session.clear()

    return redirect('/login')

@app.route('/dashboard')
def dashboard():

    if 'user' not in session:
        return redirect('/login')

    predictions = list(
        predictions_collection.find(
            {"user_email": session['user']}
        )
    )

    total_predictions = len(predictions)

    latest = predictions_collection.find_one(
        {"user_email": session['user']},
        sort=[("_id",-1)]
    )

    most_common_disease = "N/A"

    if predictions:

        diseases = [
            p["predicted_disease"]
            for p in predictions
        ]

        most_common_disease = Counter(
            diseases
        ).most_common(1)[0][0]

    health_score = min(
        total_predictions * 5,
        100
    )

    tips = [

        "Drink at least 8 glasses of water daily.",

        "Exercise for 30 minutes every day.",

        "Get 7-8 hours of sleep.",

        "Avoid excessive junk food.",

        "Take regular health checkups."
    ]

    import random

    tip_of_day = random.choice(tips)

    return render_template(

        'dashboard.html',

        total_predictions=total_predictions,

        latest=latest,

        most_common_disease=most_common_disease,

        health_score=health_score,

        tip_of_day=tip_of_day,

        user_name=session.get('name')

    )

@app.route('/profile')
def profile():

    if 'user' not in session:
        return redirect('/login')

    user = users_collection.find_one({
        "email": session['user']
    })

    predictions = list(
        predictions_collection.find({
            "user_email": session['user']
        })
    )
    member_since = user["_id"].generation_time.strftime(
            "%d %b %Y"
        )
    print("Member Since:", member_since)

    total_predictions = len(predictions)

    most_common_disease = None
    disease_count = 0
    specialist = None
    health_message = None

    if predictions:

        diseases = [
            p["predicted_disease"]
            for p in predictions
        ]

        disease_stats = Counter(diseases)

        most_common_disease, disease_count = (
            disease_stats.most_common(1)[0]
        )

        specialist = get_specialist(
            most_common_disease
        )

        if disease_count >= 3:

            health_message = (
                f"{most_common_disease} "
                f"predicted frequently."
            )

    return render_template(
    'profile.html',
    user=user,
    member_since=member_since,
    total_predictions=total_predictions,
    most_common_disease=most_common_disease,
    disease_count=disease_count,
    specialist=specialist,
    health_message=health_message
)

@app.route('/feedback', methods=['GET','POST'])
def feedback():

    if 'user' not in session:
        return redirect('/login')

    if request.method == 'POST':

        feedback_collection.insert_one({

            "user_email": session['user'],
            "rating": request.form['rating'],
            "review": request.form['review'],
            "suggestion": request.form['suggestion']

        })

        return render_template(
            'feedback.html',
            success=True
        )

    return render_template(
        'feedback.html'
    )

@app.route('/admin')
def admin():

    total_users = users_collection.count_documents({})

    total_predictions = predictions_collection.count_documents({})

    total_feedback = feedback_collection.count_documents({})

    feedbacks = list(
        feedback_collection.find().sort("_id", -1)
    )

    return render_template(
        'admin.html',
        total_users=total_users,
        total_predictions=total_predictions,
        total_feedback=total_feedback,
        feedbacks=feedbacks
    )
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
            "password": password,
            "created_at": datetime.now()
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
        recommended_hospitals=recommended_hospitals,
        hospital_details=hospital_details
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

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/health-tips')
def health_tips():

    if 'user' not in session:
        return redirect('/login')

    predictions = list(
        predictions_collection.find(
            {"user_email": session['user']}
        )
    )

    if not predictions:

        return render_template(
            "health_tips.html",
            disease=None,
            tips=[]
        )

    diseases = [
        p["predicted_disease"]
        for p in predictions
    ]

    most_common_disease = Counter(
        diseases
    ).most_common(1)[0][0]

    tips = get_precautions(
        most_common_disease
    )

    return render_template(
        "health_tips.html",
        disease=most_common_disease,
        tips=tips
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