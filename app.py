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
# =========================
# AI TUTOR CHAT
# =========================

@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json()

        if not data or not data.get("message"):
            return jsonify({"error": "Message requis"}), 400

        section = data.get("section")
        lesson = data.get("lesson")
        difficulty = data.get("difficulty")
        questions = data.get("questions", [])
        history = data.get("history", [])
        user_message = data.get("message")

        # Build context block
        context_text = (
            f"Contexte actuel :\n"
            f"- Section : {section}\n"
            f"- Leçon : {lesson}\n"
            f"- Difficulté : {difficulty}\n\n"
            f"Exercices générés :\n"
        )

        for i, q in enumerate(questions):
            context_text += f"\nExercice {i+1}:\n{q}\n"

        # Base system tutor instructions
        system_prompt = (
            "Tu es un tuteur interactif pour le Baccalauréat tunisien.\n"
            "Tu dois guider l'élève étape par étape.\n"
            "NE DONNE JAMAIS la solution complète immédiatement.\n"
            "Pose des questions pour stimuler la réflexion.\n"
            "Si l'élève demande 'donne la solution complète', "
            "donne-la seulement après au moins une tentative de guidage.\n\n"
            "Règles mathématiques :\n"
            "- Les explications normales ne doivent PAS être dans $...$.\n"
            "- Seules les expressions mathématiques doivent être entre $...$ ou $$...$$.\n"
            "- N'utilise jamais ^ ou _ sans accolades {}.\n"
            "- Écris toujours en français clair.\n"
        )

        # Build messages list for Groq
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": context_text}
        ]

        # Add conversation history
        for msg in history:
            messages.append(msg)

        # Add current user message
        messages.append({"role": "user", "content": user_message})

        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            temperature=0.5,
            messages=messages
        )

        reply = completion.choices[0].message.content
        reply = clean_latex(reply)

        return jsonify({"reply": reply})

    except Exception as e:
        return jsonify({"error": str(e)}), 500
@app.route("/lesson_content", methods=["POST"])
def lesson_content():
    try:
        data = request.get_json()

        if not data or not data.get("section") or not data.get("lesson"):
            return jsonify({"error": "Section et leçon requises"}), 400

        section = data.get("section")
        lesson = data.get("lesson")

        if section not in BAC_PROGRAM:
            return jsonify({"error": "Section invalide"}), 400

        if lesson not in BAC_PROGRAM[section]:
            return jsonify({"error": "Leçon invalide"}), 400

        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            max_tokens=3000,

            temperature=0.3,
            messages=[
                {
                    "role": "system",
                   "content": (
    f"Tu es un professeur expert du Baccalauréat tunisien.\n\n"
    f"Rédige un cours COMPLET, DÉTAILLÉ et EXHAUSTIF sur '{lesson}' "
    f"pour la section {section}.\n\n"

    "Le cours doit être suffisamment long pour couvrir tout le chapitre.\n"
    "Il doit être pédagogique, structuré et sans fautes d’orthographe.\n\n"

    "Structure STRICTE en Markdown :\n\n"

    "# Titre du chapitre\n\n"

    "## 1. Introduction détaillée\n"
    "- Présentation du concept\n"
    "- Pourquoi il est important\n"
    "- Où il apparaît dans le Bac\n\n"

    "## 2. Définitions importantes\n"
    "- Définition claire et complète\n"
    "- Explications supplémentaires\n\n"

    "## 3. Propriétés et règles\n"
    "- Propriété 1 avec explication\n"
    "- Propriété 2 avec justification\n\n"

    "## 4. Théorèmes importants\n"
    "- Énoncé\n"
    "- Conditions d'application\n"
    "- Interprétation\n\n"

    "## 5. Méthodes de résolution\n"
    "Pour chaque méthode :\n"
    "- Quand l'utiliser\n"
    "- Étapes détaillées\n\n"

    "## 6. Plusieurs exemples détaillés\n"
    "Donne AU MOINS 3 exemples différents.\n"
    "Chaque exemple doit être expliqué étape par étape.\n\n"

    "## 7. Cas particuliers et erreurs fréquentes\n"
    "- Erreur 1\n"
    "- Erreur 2\n\n"

    "## 8. Remarques importantes\n"
    "- Points clés à retenir pour le Bac\n\n"

    "IMPORTANT:\n"
    "- Utilise des paragraphes espacés.\n"
    "- Utilise des listes avec '-'.\n"
    "- Utilise ## pour les sections.\n"
    "- Les mathématiques doivent être entre $...$.\n"
    "- Le texte doit être sans fautes d'orthographe.\n"
    "- Ne sois PAS trop court.\n"
)


                }
            ]
        )

        lesson_text = clean_latex(completion.choices[0].message.content)

        return jsonify({"lesson": lesson_text})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)
