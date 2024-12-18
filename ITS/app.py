from owlready2 import *
from flask import Flask, render_template, request, redirect, url_for, flash

app = Flask(__name__)

onto = get_ontology("untitled-ontology-7.rdf").load()

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/search', methods=['GET', 'POST'])
def search():
    if request.method == 'POST':
        element_name = request.form.get('element_name').capitalize()

        try:
            element = onto.search_one(iri=f"*#{element_name}")
            
            if element:
                symbol = element.hasSymbol[0] if hasattr(element, 'hasSymbol') else "N/A"
                atomic_number = element.hasAtomicNumber[0] if hasattr(element, 'hasAtomicNumber') else "N/A"
                atomic_weight = element.hasAtomicWeight[0] if hasattr(element, 'hasAtomicWeight') else "N/A"
                group = element.belongsToGroup[0].name if hasattr(element, 'belongsToGroup') else "N/A"
                period = element.belongsToPeriod[0].name if hasattr(element, 'belongsToPeriod') else "N/A"

                feedback = f"{element_name} is an element from the {group} group. Its atomic number is {atomic_number} and atomic weight is {atomic_weight}."

                group_elements_list = []
                if group:
                    group_elements = onto.search(iri=f"*#{group}*")
                    group_elements_list = [e.name for e in group_elements if hasattr(e, 'hasSymbol')]

                if group_elements_list:
                    feedback += f" Other elements in the {group} group include: {', '.join(group_elements_list)}."
                
                return render_template('result.html', element_name=element_name, 
                                       symbol=symbol, atomic_number=atomic_number,
                                       atomic_weight=atomic_weight, group=group, period=period,
                                       feedback=feedback, group_elements_list=group_elements_list)
            else:
                return f"Element '{element_name}' not found in the ontology."
        except Exception as e:
            return f"Error: {e}"

    return render_template('search_form.html')



@app.route('/group_elements', methods=['GET', 'POST'])
def group_elements():
    if request.method == 'GET':
        return render_template('group_elements.html')  # Show the form to input a group name

    if request.method == 'POST':
        group_name = request.form.get('group_name').strip().lower()

        try:
            elements_in_group = []

            for element in onto.Element.instances():
                if hasattr(element, 'belongsToGroup'):
                    for group_relation in element.belongsToGroup:
                        if group_relation.name.lower() == group_name:
                            elements_in_group.append({
                                'name': element.name,
                                'symbol': element.hasSymbol[0] if hasattr(element, 'hasSymbol') else "N/A",
                                'atomic_number': element.hasAtomicNumber[0] if hasattr(element, 'hasAtomicNumber') else "N/A",
                                'atomic_weight': element.hasAtomicWeight[0] if hasattr(element, 'hasAtomicWeight') else "N/A"
                            })

            if elements_in_group:
                return render_template('group_elements.html', group_name=group_name.capitalize(),
                                       elements_in_group=elements_in_group)
            else:
                return f"No elements found in the group '{group_name}'."
        except Exception as e:
            return f"Error: {e}"


@app.route('/same_group_elements', methods=['GET'])
def same_group_elements_form():
    return render_template('same_group_elements.html')  

@app.route('/same_group_elements', methods=['POST'])
def same_group_elements():
    element_name = request.form.get('element_name', "").strip().lower()

    try:
        def get_element_by_name(name):
            return onto.search_one(iri=f"*#{name.capitalize()}")

        def get_group_by_element(element):
            if hasattr(element, 'belongsToGroup') and element.belongsToGroup:
                return element.belongsToGroup[0].name
            return None

        def get_elements_in_group(group_name):
            elements = []
            for el in onto.Element.instances():
                if hasattr(el, 'belongsToGroup'):
                    for group_relation in el.belongsToGroup:
                        if group_relation.name.lower() == group_name.lower():
                            elements.append({
                                'name': el.name,
                                'symbol': getattr(el, 'hasSymbol', ["Unknown"])[0],
                                'atomic_number': getattr(el, 'hasAtomicNumber', ["Unknown"])[0],
                                'atomic_weight': getattr(el, 'hasAtomicWeight', ["Unknown"])[0]
                            })
            return elements

        # Main logic
        element = get_element_by_name(element_name)
        if not element:
            flash(f"Element '{element_name}' not found in the ontology.")
            return redirect('/same_group_elements')

        group_name = get_group_by_element(element)
        if not group_name:
            flash(f"Element '{element_name}' does not belong to any group.")
            return redirect('/same_group_elements')

        elements_in_group = get_elements_in_group(group_name)
        if not elements_in_group:
            flash(f"No other elements found in the group '{group_name}'.")
            return redirect('/same_group_elements')

        # results
        return render_template('group_elements.html', group_name=group_name.capitalize(),
                               elements_in_group=elements_in_group)

    except Exception as e:
        flash(f"An unexpected error occurred: {e}")
        return redirect('/same_group_elements')



def generate_question(element_name):
    element = onto.search_one(iri=f"*#{element_name}")
    
    if element is None:
        return None

    questions = []
    
    if hasattr(element, 'hasAtomicNumber'):
        atomic_number = element.hasAtomicNumber[0]
        questions.append({
            'question': f"What is the atomic number of {element_name}?",
            'correct_answer': str(atomic_number),
            'answer_type': 'text'  # or 'number'
        })
        
    if hasattr(element, 'hasSymbol'):
        symbol = element.hasSymbol[0]
        questions.append({
            'question': f"What is the atomic symbol of {element_name}?",
            'correct_answer': symbol,
            'answer_type': 'text'
        })
        
    if hasattr(element, 'hasAtomicWeight'):
        atomic_weight = element.hasAtomicWeight[0]
        questions.append({
            'question': f"What is the atomic weight of {element_name}?",
            'correct_answer': str(atomic_weight),
            'answer_type': 'text'
        })

    if hasattr(element, 'belongsToGroup'):
        group = element.belongsToGroup[0].name
        questions.append({
            'question': f"What group is {element_name} in?",
            'correct_answer': group,
            'answer_type': 'text'
        })

    return questions

current_question_index = 0

@app.route('/quiz', methods=['GET', 'POST'])
def quiz():
    global current_question_index

    if request.method == 'POST':
        user_answer = request.form.get('answer')
        
        element_name = request.form.get('element_name')
        
        questions = generate_question(element_name)
        correct_answer = questions[current_question_index]['correct_answer']
        
        if user_answer.strip().lower() == correct_answer.strip().lower():
            feedback = "Correct!"
        else:
            feedback = f"Incorrect! The correct answer is {correct_answer}."

        current_question_index += 1
        
        if current_question_index < len(questions):
            question = questions[current_question_index]['question']
            return render_template('quiz.html', question=question, feedback=feedback, current_question_index=current_question_index, element_name=element_name)
        else:
            return render_template('quiz_result.html', feedback="You've completed the quiz!", score=feedback)

    element_name = "Sodium"  # This can be dynamically chosen based on your needs
    questions = generate_question(element_name)
    question = questions[current_question_index]['question']
    
    return render_template('quiz.html', question=question, current_question_index=current_question_index, element_name=element_name)


@app.route('/quiz_answer', methods=['POST'])
def quiz_answer():
    return redirect(url_for('quiz'))


# Route for the feedback form
@app.route('/')
def feedback_form():
    return render_template('feedback.html')

# Route to handle form submission
@app.route('/submit-feedback', methods=['POST'])
def submit_feedback():
    name = request.form['name']
    email = request.form['email']
    feedback = request.form['feedback']

    # Print the feedback to the console (you can save this to a database or file later)
    print(f"Name: {name}, Email: {email}, Feedback: {feedback}")

    # Return a thank-you response
    return f"<h1>Thank you, {name}! Your feedback has been submitted.</h1>"




if __name__ == '__main__':
    app.run(debug=True)
