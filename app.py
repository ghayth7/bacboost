from flask import Flask, render_template, request, jsonify
from groq import Groq
from dotenv import load_dotenv
import os
import re

load_dotenv()

app = Flask(__name__)
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# =========================
# OFFICIAL BAC PROGRAM
# =========================

BAC_PROGRAM = {
    "Mathematics": [
        "Limits",
        "Derivatives",
        "Integrals",
        "Complex Numbers",
        "Sequences",
        "Probability",
        "Differential Equations"
    ],
    "Science": [
        "Limits",
        "Derivatives",
        "Integrals",
        "Probability",
        "Sequences"
    ],
    "Economics": [
        "Functions",
        "Derivatives",
        "Probability",
        "Statistics"
    ],
    "Technical": [
        "Functions",
        "Integrals",
        "Complex Numbers",
        "Statistics"
    ],
    "Informatique": [
        "Functions",
        "Probability",
        "Matrices",
        "Complex Numbers",
    ]
}

# =========================
# LATEX CLEANING FUNCTION
# =========================

def clean_latex(text):
    if not text:
        return text

    # Only remove accidental triple dollars
    text = text.replace("$$$", "$$")

    # Trim outer whitespace
    return text.strip()




# =========================
# ROUTES
# =========================

@app.route("/")
def home():
    return render_template("index.html")


# =========================
# GET LESSONS
# =========================

@app.route("/lessons/<section>")
def get_lessons(section):
    lessons = BAC_PROGRAM.get(section)
    if not lessons:
        return jsonify({"error": "Section invalide"}), 400
    return jsonify({"lessons": lessons})


# =========================
# GENERATE QUESTIONS
# =========================

@app.route("/generate", methods=["POST"])
def generate():
    try:
        data = request.get_json()

        if not data or not data.get("lesson") or not data.get("section"):
            return jsonify({"error": "Section et leçon obligatoires"}), 400

        section = data.get("section")
        lesson = data.get("lesson")
        difficulty = data.get("difficulty", "medium")


        if section not in BAC_PROGRAM:
            return jsonify({"error": "Section invalide"}), 400

        if lesson not in BAC_PROGRAM[section]:
            return jsonify({
                "error": f"{lesson} ne fait pas partie du programme de {section}."
            }), 400
        difficulty_instruction = ""

        if difficulty == "easy":
          difficulty_instruction = "Les exercices doivent être simples, directs et courts."
        elif difficulty == "medium":
             difficulty_instruction = "Les exercices doivent être de niveau Bac standard avec raisonnement modéré."
        elif difficulty == "hard":
            difficulty_instruction = "Les exercices doivent être difficiles, avec raisonnement avancé et calculs plus complexes."

        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            temperature=0.6,
            messages=[
                {
                    "role": "system",
                    "content": (
                        f"Tu es un expert en mathématiques du Baccalauréat tunisien "
                        f"pour la section {section}.\n\n"
                        f"Niveau demandé : {difficulty.upper()}.\n"
                        f"{difficulty_instruction}\n\n"
                        f"Génère exactement 3 exercices strictement sur la leçon '{lesson}'.\n\n"
                        f"strictement sur la leçon '{lesson}'.\n\n"
                        "RÈGLES OBLIGATOIRES :\n"
                        "- Tout le texte doit être en français.\n"
                        "- Toutes les expressions mathématiques doivent être entre $...$ ou $$...$$.\n"
                        "- N'écris JAMAIS un symbole mathématique en dehors de $...$.\n"
                        "- Écris toujours les limites comme : $x \\to 0$.\n"
                        "- N'utilise jamais ^ ou _ sans accolades {}.\n"

                        "- Utilise un LaTeX correct.\n"
                        "- Aucun texte avant Question 1.\n"
                        "- Aucun texte après Question 3.\n\n"
                        "Format EXACTEMENT :\n\n"
                        "Question 1:\n...\n\n"
                        "Question 2:\n...\n\n"
                        "Question 3:\n...\n"
                    )
                }
            ]
        )

        full_text = completion.choices[0].message.content
        full_text = clean_latex(full_text)

        # Robust split
        questions = re.split(r"(?i)question\s*\d+\s*:", full_text)
        questions = [q.strip() for q in questions if q.strip()]

        if len(questions) != 3:
            return jsonify({"error": "Erreur génération IA"}), 500

        return jsonify({"questions": questions})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# =========================
# SOLVE QUESTION
# =========================

@app.route("/solve", methods=["POST"])
def solve():
    try:
        data = request.get_json()

        if not data or not data.get("question_text"):
            return jsonify({"error": "Texte de la question requis"}), 400

        question_text = data.get("question_text")

        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            temperature=0.4,
            messages=[
          {
    "role": "system",
    "content": (
        "Donne une correction détaillée étape par étape.\n"
        "Le texte explicatif ne doit JAMAIS être dans $...$.\n"
        "Seules les expressions mathématiques doivent être entre $...$ ou $$...$$.\n"
        "Explique en français clair avec des phrases normales.\n"
        "- N'utilise jamais ^ ou _ sans accolades {}.\n"
    )
}
,
                {
                    "role": "user",
                    "content": question_text
                }
            ]
        )

        solution = completion.choices[0].message.content
        solution = clean_latex(solution)

        return jsonify({"solution": solution})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# =========================

if __name__ == "__main__":
    app.run(debug=True)
