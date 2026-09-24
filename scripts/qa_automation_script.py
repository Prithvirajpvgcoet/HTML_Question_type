import requests
import time
import sys

BASE_URL = "http://localhost:8001/api/v1"

QUESTIONS = [
    {
        "title": "Interactive Button",
        "description_html": "<p>Create a button with id 'click-me'. When clicked, it should change its text to 'Clicked!' and its background color to 'blue'.</p>",
        "html": "<button id='click-me'>Click Me</button>",
        "css": "button { background-color: red; color: white; padding: 10px; }",
        "js": "document.getElementById('click-me').addEventListener('click', function() { this.innerText = 'Clicked!'; this.style.backgroundColor = 'blue'; });"
    },
    {
        "title": "Simple Counter",
        "description_html": "<p>Create a div with id 'count' showing '0'. Create a button with id 'inc'. Clicking the button increments the count.</p>",
        "html": "<div id='count'>0</div><button id='inc'>Increment</button>",
        "css": "#count { font-size: 24px; }",
        "js": "let c = 0; document.getElementById('inc').addEventListener('click', () => { c++; document.getElementById('count').innerText = c; });"
    },
    {
        "title": "Hidden Text Toggle",
        "description_html": "<p>Create a button 'Toggle' (id 'tgl') and a paragraph (id 'txt'). Clicking the button should toggle the paragraph's display property between 'none' and 'block'.</p>",
        "html": "<button id='tgl'>Toggle</button><p id='txt' style='display:block;'>Hello World</p>",
        "css": "",
        "js": "document.getElementById('tgl').addEventListener('click', () => { let el = document.getElementById('txt'); el.style.display = el.style.display === 'none' ? 'block' : 'none'; });"
    },
    {
        "title": "Color List",
        "description_html": "<p>Create a ul list with id 'colors'. It should contain 3 li elements with texts: Red, Green, Blue.</p>",
        "html": "<ul id='colors'><li>Red</li><li>Green</li><li>Blue</li></ul>",
        "css": "ul { list-style-type: square; }",
        "js": ""
    },
    {
        "title": "Input Mirror",
        "description_html": "<p>Create an input field (id 'inp') and a span (id 'out'). Typing in the input should instantly update the span's text to match.</p>",
        "html": "<input id='inp' type='text' /><span id='out'></span>",
        "css": "",
        "js": "document.getElementById('inp').addEventListener('input', (e) => { document.getElementById('out').innerText = e.target.value; });"
    },
    {
        "title": "Flexbox Centering",
        "description_html": "<p>Create a container (id 'box') 200x200px. Inside it, place a div (id 'inner'). Center the inner div perfectly using flexbox.</p>",
        "html": "<div id='box'><div id='inner'>Center</div></div>",
        "css": "#box { width: 200px; height: 200px; display: flex; align-items: center; justify-content: center; background: #eee; } #inner { background: red; padding: 10px; }",
        "js": ""
    },
    {
        "title": "Basic Form Validation",
        "description_html": "<p>Create a form with an input (id 'email') and a submit button. On submit, if the input is empty, show a red error border.</p>",
        "html": "<form id='frm'><input id='email' type='text'/><button type='submit'>Go</button></form>",
        "css": ".error { border: 2px solid red; }",
        "js": "document.getElementById('frm').addEventListener('submit', (e) => { e.preventDefault(); let el = document.getElementById('email'); if(!el.value) el.classList.add('error'); });"
    },
    {
        "title": "Hover Card",
        "description_html": "<p>Create a div (id 'card'). When hovered, its box-shadow should become '0px 10px 20px rgba(0,0,0,0.5)'.</p>",
        "html": "<div id='card'>Card Content</div>",
        "css": "#card { padding: 20px; transition: box-shadow 0.3s; box-shadow: 0 0 0 transparent; } #card:hover { box-shadow: 0px 10px 20px rgba(0,0,0,0.5); }",
        "js": ""
    },
    {
        "title": "Tab Component",
        "description_html": "<p>Create two buttons (id 'tab1', 'tab2') and two content divs (id 'content1', 'content2'). Only one content should be visible at a time based on the active tab.</p>",
        "html": "<button id='tab1'>T1</button><button id='tab2'>T2</button><div id='content1'>C1</div><div id='content2' style='display:none;'>C2</div>",
        "css": "",
        "js": "document.getElementById('tab1').addEventListener('click', () => { document.getElementById('content1').style.display='block'; document.getElementById('content2').style.display='none'; }); document.getElementById('tab2').addEventListener('click', () => { document.getElementById('content1').style.display='none'; document.getElementById('content2').style.display='block'; });"
    },
    {
        "title": "Progress Bar",
        "description_html": "<p>Create a div (id 'progress-bg') and an inner div (id 'progress-bar'). Write a JS function setProgress(val) that updates the width percentage.</p>",
        "html": "<div id='progress-bg' style='width:100px; background:#ddd;'><div id='progress-bar' style='width:0%; background:green; height:10px;'></div></div>",
        "css": "",
        "js": "function setProgress(val) { document.getElementById('progress-bar').style.width = val + '%'; } window.setProgress = setProgress;"
    }
]

def run_tests():
    print("Starting Automated E2E Workflow Testing...")
    for idx, q in enumerate(QUESTIONS):
        print(f"\n--- Processing Question {idx+1}/10: {q['title']} ---")
        
        # 1. Create Question
        resp = requests.post(f"{BASE_URL}/questions", json={
            "title": q["title"],
            "description_html": q["description_html"],
            "question_type": "HTML/CSS/JS",
            "is_published": True
        })
        if resp.status_code != 200:
            print(f"Error creating question: {resp.text}")
            continue
        q_id = resp.json()["id"]
        print(f"Created Question ID: {q_id}")

        # 2. Add Code Solution
        resp = requests.put(f"{BASE_URL}/questions/{q_id}/code-solution", json={
            "reference_html": q["html"],
            "reference_css": q["css"],
            "reference_js": q["js"]
        })
        print(f"Added code solution: {resp.status_code}")

        # 3. Generate Assertions (AI)
        print("Generating AI Assertions...")
        resp = requests.post(f"{BASE_URL}/questions/{q_id}/generate-assertions", timeout=120)
        print(f"Assertions generated: {resp.status_code}")

        # 4. Submit Candidate Code
        print("Creating Candidate Submission...")
        resp = requests.post(f"{BASE_URL}/submissions", json={
            "question_id": q_id,
            "candidate_name": "Automation Tester",
            "submitted_html": q["html"],
            "submitted_css": q["css"],
            "submitted_js": q["js"]
        })
        if resp.status_code != 200:
            print(f"Error creating submission: {resp.text}")
            continue
        sub_id = resp.json()["id"]
        print(f"Submission created ID: {sub_id}")

        # 5. Evaluate
        print("Triggering Evaluation...")
        resp = requests.post(f"{BASE_URL}/submissions/{sub_id}/evaluate")
        
        # 6. Poll for completion
        completed = False
        for _ in range(30):
            time.sleep(2)
            eval_resp = requests.get(f"{BASE_URL}/submissions/{sub_id}/evaluation")
            if eval_resp.status_code == 200:
                data = eval_resp.json()
                if data.get("status") in ["completed", "failed"]:
                    completed = True
                    print(f"Evaluation finished with status: {data['status']}")
                    print(f"Score: {data.get('total_score')}/100")
                    break
        if not completed:
            print("Evaluation timed out.")
            
        print("Pacing: sleeping for 6 seconds to respect Gemini 10 RPM free tier limits...")
        time.sleep(6)


    print("\nE2E Workflow Testing Complete.")

if __name__ == "__main__":
    run_tests()
