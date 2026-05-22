from flask import Flask, render_template ,request

app = Flask(__name__)

expenses =[]

@app.route('/', methods=['GET','POST'])
def home():
    if request.method == 'POST':
        title = request.form['title']
        amount = request.form['amount']


        expense = {
            'title': title,
            'amount': amount
        }
        expenses.append(expense)
    return render_template('index.html',expenses=expenses)

if __name__ == '__main__':
    app.run(debug=True, port=5001)
 
