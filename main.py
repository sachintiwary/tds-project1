# main.py
import os
import base64
import threading
from flask import Flask, request, jsonify
from dotenv import load_dotenv
import openai
from github import Github, Auth
import requests

# --- SETUP AND CONFIGURATION ---
load_dotenv()
app = Flask(__name__)

# Configure AI Pipe client
client = openai.OpenAI(
    api_key=os.getenv("AIPIPE_TOKEN"),
    base_url=os.getenv("OPENAI_BASE_URL"),
)

# Configure GitHub client with the recommended authentication method
auth = Auth.Token(os.getenv("GITHUB_TOKEN"))
g = Github(auth=auth)
GITHUB_USERNAME = os.getenv("GITHUB_USERNAME")

# --- HELPER FUNCTIONS ---

def clean_llm_output(raw_output):
    """
    Cleans the LLM's raw output to ensure it's just HTML code.
    It strips conversational text and markdown fences.
    """
    # Find the start of the actual HTML document
    html_start_index = raw_output.find("<!DOCTYPE html>")
    if html_start_index != -1:
        return raw_output[html_start_index:]

    # As a fallback, try to strip markdown fences if they exist
    if raw_output.strip().startswith("```") and raw_output.strip().endswith("```"):
        lines = raw_output.strip().split('\n')
        # Return content between the fences (e.g., skips ```html and ```)
        return '\n'.join(lines[1:-1])

    # Return original if no specific format is found, hoping for the best
    return raw_output

def generate_code_from_brief(brief_text, checks):
    """Generates and cleans HTML code from a brief using the LLM."""
    print("🤖 Sending brief to LLM via AI Pipe...")

    # A stricter, more forceful prompt to ensure code-only output
    system_prompt = (
        "You are an expert web developer who writes ONLY code. Your task is to build a single-page, self-contained `index.html` file. "
        "Your response MUST be ONLY the complete, raw HTML code for the `index.html` file. "
        "Do NOT include any explanations, comments, or any text outside of the HTML code itself. "
        "Do NOT wrap the code in markdown fences like ```html."
    )
    user_prompt = f"BRIEF:\n---\n{brief_text}\n---\nEVALUATION CHECKS TO PASS:\n---\n{checks}"

    try:
        response = client.chat.completions.create(
            model="gpt-4.1-nano", # Model known to work with AI Pipe
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
        )
        raw_code = response.choices[0].message.content
        html_code = clean_llm_output(raw_code) # Clean the output
        print("🤖 LLM generated the code!")
        return html_code
    except Exception as e:
        print(f"🚨 LLM Error: {e}")
        return None

def create_github_repo(repo_name, html_content, brief):
    """Creates a GitHub repo, pushes code, LICENSE, and README."""
    print(f"🐙 Creating GitHub repo: {repo_name}")
    user = g.get_user()
    try:
        repo = user.create_repo(repo_name, private=False)
        repo.create_file("index.html", "feat: initial commit", html_content)
        mit_license_url = "[https://raw.githubusercontent.com/licenses/MIT/main/LICENSE](https://raw.githubusercontent.com/licenses/MIT/main/LICENSE)"
        mit_license = requests.get(mit_license_url).text
        repo.create_file("LICENSE", "docs: add MIT license", mit_license)
        readme_content = f"# {repo_name}\n\nThis project was auto-generated based on the brief: '{brief}'"
        repo.create_file("README.md", "docs: add README", readme_content)
        print("🐙 Files pushed to repo.")
        return repo
    except Exception as e:
        print(f"🚨 GitHub Repo Error: {e}")
        return None

def enable_github_pages(repo):
    """Enables GitHub Pages for the repository."""
    print("📜 Enabling GitHub Pages...")
    try:
        pages_url = f"[https://api.github.com/repos/](https://api.github.com/repos/){repo.full_name}/pages"
        headers = {
            "Authorization": f"token {os.getenv('GITHUB_TOKEN')}",
            "Accept": "application/vnd.github.v3+json",
        }
        payload = {"source": {"branch": "main", "path": "/"}}
        response = requests.post(pages_url, headers=headers, json=payload)
        if response.status_code == 201:
            print("📜 GitHub Pages enabled successfully.")
            return f"https://{GITHUB_USERNAME}.github.io/{repo.name}/"
        else:
            print(f"🚨 GitHub Pages Error: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"🚨 GitHub Pages Error: {e}")
        return None

def notify_evaluation_api(data, repo_url, pages_url, commit_sha):
    """Pings the instructor's evaluation API with the results."""
    payload = {
        "email": data.get('email'), "task": data.get('task'), "round": data.get('round'),
        "nonce": data.get('nonce'), "repo_url": repo_url, "commit_sha": commit_sha, "pages_url": pages_url,
    }
    print(f"📢 Pinging evaluation API with: {payload}")
    try:
        response = requests.post(data.get('evaluation_url'), json=payload)
        print(f"📢 Evaluation API responded with status: {response.status_code}")
    except Exception as e:
        print(f"🚨 Evaluation API Error: {e}")

# --- BACKGROUND WORKER ---
def process_build_request(data):
    """The main worker function that runs in the background."""
    html_code = generate_code_from_brief(data.get('brief'), data.get('checks'))
    if not html_code:
        print("Stopping process due to LLM failure.")
        return

    repo = create_github_repo(data.get('task'), html_code, data.get('brief'))
    if not repo:
        print("Stopping process due to GitHub repo creation failure.")
        return

    pages_url = enable_github_pages(repo)
    if not pages_url:
        print("Stopping process due to GitHub Pages failure.")
        return

    commit_sha = repo.get_contents("index.html").sha
    notify_evaluation_api(data, repo.html_url, pages_url, commit_sha)
    print("✅✅✅ Full process completed! ✅✅✅")

# --- MAIN API ENDPOINT ---
@app.route('/api-endpoint', methods=['POST'])
def handle_request():
    """Receives the request and starts the background job."""
    print("✅ Request received!")
    data = request.get_json()

    if not data or data.get('secret') != os.getenv("MY_SECRET"):
        print("🚨 ERROR: Invalid secret!")
        return jsonify({"error": "Invalid secret"}), 403

    print("✅ Secret verified. Starting background job.")
    thread = threading.Thread(target=process_build_request, args=(data,))
    thread.start()

    return jsonify({"status": "Job accepted and is now processing in the background."}), 200

# --- SERVER START ---
if __name__ == '__main__':
    app.run(port=5000)