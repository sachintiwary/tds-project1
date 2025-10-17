# main.py
import os
import base64
import threading
import time
import logging
from flask import Flask, request, jsonify
from dotenv import load_dotenv
import openai
from github import Github, Auth, UnknownObjectException
import requests

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

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
    Cleans the LLM's raw output to ensure it's just code.
    It strips conversational text and markdown fences.
    """
    html_start_index = raw_output.find("<!DOCTYPE html>")
    if html_start_index != -1:
        return raw_output[html_start_index:]

    if raw_output.strip().startswith("```") and raw_output.strip().endswith("```"):
        lines = raw_output.strip().split('\n')
        return '\n'.join(lines[1:-1])

    return raw_output

def generate_code_from_brief(brief_text, checks, attachments=None):
    """Generates and cleans HTML code from a brief and attachments using the LLM."""
    logging.info("🤖 Sending brief and attachments to LLM for code generation...")
    system_prompt = (
        "You are an expert web developer who writes ONLY code. Your task is to build a single-page, self-contained `index.html` file. "
        "Your response MUST be ONLY the complete, raw HTML code for the `index.html` file. "
        "Do NOT include any explanations, comments, or any text outside of the HTML code itself. "
        "Do NOT wrap the code in markdown fences like ```html."
    )
    attachments_content = ""
    if attachments:
        attachments_content = "\n\n--- ATTACHED FILES CONTENT ---\n"
        for attachment in attachments:
            try:
                header, encoded = attachment['url'].split(",", 1)
                decoded_content = base64.b64decode(encoded).decode('utf-8')
                attachments_content += f"File Name: `{attachment['name']}`\nContent:\n```\n{decoded_content}\n```\n"
            except Exception as e:
                logging.error(f"🚨 Error decoding attachment {attachment['name']}: {e}")

    # Format checks for better LLM comprehension
    formatted_checks = '\n'.join([f"- {check}" for check in checks]) if checks else ""
    user_prompt = f"BRIEF:\n---\n{brief_text}\n---\nEVALUATION CHECKS TO PASS:\n---\n{formatted_checks}{attachments_content}"

    try:
        response = client.chat.completions.create(
            model="gpt-4.1-nano",
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
            timeout=30
        )
        logging.info("🤖 LLM call completed successfully")
        raw_code = response.choices[0].message.content
        html_code = clean_llm_output(raw_code)
        logging.info("🤖 LLM generated the code!")
        return html_code
    except Exception as e:
        logging.error(f"🚨 LLM Error: {e}")
        import traceback
        traceback.print_exc()
        return None

def generate_revision_from_brief(new_brief, existing_html, checks=None):
    """Generates a revised version of the HTML code."""
    logging.info("🤖 Sending existing code and new brief to LLM for revision...")
    system_prompt = (
        "You are an expert web developer who revises code. Your task is to update an existing `index.html` file based on a new request. "
        "Your response MUST be ONLY the complete, updated HTML code. Do not include explanations."
    )
    # Format checks for better LLM comprehension
    formatted_checks = '\n'.join([f"- {check}" for check in checks]) if checks else ""
    user_prompt = f"NEW REQUEST:\n---\n{new_brief}\n---\nEVALUATION CHECKS TO PASS:\n---\n{formatted_checks}\n\n--- EXISTING `index.html` CODE TO REVISE ---\n```html\n{existing_html}\n```"

    try:
        response = client.chat.completions.create(
            model="gpt-4.1-nano",
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
            timeout=30
        )
        logging.info("🤖 LLM call completed successfully")
        raw_code = response.choices[0].message.content
        updated_html = clean_llm_output(raw_code)
        logging.info("🤖 LLM generated the revised code!")
        return updated_html
    except Exception as e:
        logging.error(f"🚨 LLM Revision Error: {e}")
        return None

def generate_professional_readme(brief, code):
    """Generates a professional README.md for the project."""
    logging.info("📝 Generating professional README.md...")
    system_prompt = (
        "You are a technical writer. Your task is to create a professional README.md file for a software project."
        "The response should be in clean Markdown format. Do not include any other text."
    )
    user_prompt = (
        f"Based on the following project brief and the generated code, create a complete README.md file. "
        f"It must include these sections: \n- A clear project title.\n- A 'Summary' of what the application does.\n- A 'Setup' section explaining how to run it (mention it's a static HTML file).\n- A brief 'Code Explanation'.\n- A 'License' section stating it uses the MIT License."
        f"\n\n--- PROJECT BRIEF ---\n{brief}\n\n--- GENERATED CODE ---\n```html\n{code}\n```"
    )
    try:
        response = client.chat.completions.create(
            model="gpt-4.1-nano",
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
        )
        return response.choices[0].message.content
    except Exception as e:
        logging.error(f"🚨 README Generation Error: {e}")
        return f"# Project\n\nFailed to generate README. See logs for details."

def create_github_repo(repo_name, html_content, brief):
    """Creates a GitHub repo, pushes code, LICENSE, and a professional README."""
    logging.info(f"🐙 Creating GitHub repo: {repo_name}")
    user = g.get_user()
    try:
        # Delete repo if it already exists (useful for local testing)
        try:
            repo = user.get_repo(repo_name)
            repo.delete()
            logging.info(f"🗑️ Deleted existing repo: {repo_name}")
        except UnknownObjectException:
            pass # Repo didn't exist, which is fine

        repo = user.create_repo(repo_name, private=False)
        repo.create_file("index.html", "feat: initial commit", html_content)
        mit_license_url = "https://raw.githubusercontent.com/licenses/MIT/main/LICENSE"
        mit_license = requests.get(mit_license_url).text
        repo.create_file("LICENSE", "docs: add MIT license", mit_license)
        readme_content = generate_professional_readme(brief, html_content)
        repo.create_file("README.md", "docs: add professional README", readme_content)
        logging.info("🐙 Files pushed to repo.")
        return repo
    except Exception as e:
        logging.error(f"🚨 GitHub Repo Error: {e}")
        return None

def enable_github_pages(repo):
    """Enables GitHub Pages for the repository."""
    logging.info("📜 Enabling GitHub Pages...")
    try:
        default_branch = repo.default_branch
        pages_url = f"https://api.github.com/repos/{repo.full_name}/pages"
        headers = {"Authorization": f"token {os.getenv('GITHUB_TOKEN')}", "Accept": "application/vnd.github.v3+json"}
        payload = {"source": {"branch": default_branch, "path": "/"}}
        response = requests.post(pages_url, headers=headers, json=payload)
        if response.status_code == 201:
            logging.info("📜 GitHub Pages enabled successfully.")
            return f"https://{GITHUB_USERNAME}.github.io/{repo.name}/"
        else:
            logging.error(f"🚨 GitHub Pages Error: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        logging.error(f"🚨 GitHub Pages Error: {e}")
        return None

def notify_evaluation_api(data, repo_url, pages_url, commit_sha):
    """Pings the instructor's evaluation API with exponential backoff for retries."""
    payload = {
        "email": data.get('email'), "task": data.get('task'), "round": data.get('round'),
        "nonce": data.get('nonce'), "repo_url": repo_url, "commit_sha": commit_sha, "pages_url": pages_url,
    }
    logging.info(f"📢 Pinging evaluation API with: {payload}")
    retries = 4
    delay = 1
    for i in range(retries):
        try:
            response = requests.post(data.get('evaluation_url'), json=payload, timeout=10)
            if response.status_code == 200:
                logging.info(f"📢 Evaluation API responded with status: {response.status_code}")
                return
        except Exception as e:
            logging.error(f"🚨 Evaluation API Error: {e}")
        logging.info(f"Retrying in {delay} seconds...")
        time.sleep(delay)
        delay *= 2
    logging.error("🚨 Failed to notify evaluation API after multiple retries.")

# --- BACKGROUND WORKERS ---

def process_build_request(data):
    """The main worker for Round 1: Build and Deploy."""
    try:
        html_code = generate_code_from_brief(data.get('brief'), data.get('checks'), data.get('attachments'))
        if not html_code:
            logging.error("Stopping process due to LLM failure.")
            return

        repo = create_github_repo(data.get('task'), html_code, data.get('brief'))
        if not repo:
            logging.error("Stopping process due to GitHub repo creation failure.")
            return

        pages_url = enable_github_pages(repo)
        if not pages_url:
            logging.error("Stopping process due to GitHub Pages failure.")
            return

        commit_sha = repo.get_contents("index.html").sha
        notify_evaluation_api(data, repo.html_url, pages_url, commit_sha)
        logging.info("✅✅✅ Round 1 process completed! ✅✅✅")
    except Exception as e:
        logging.error(f"🚨 Round 1 Error: {e}")
        import traceback
        traceback.print_exc()

def process_revise_request(data):
    """The main worker for Round 2: Revise and Redeploy."""
    try:
        repo_name = data.get('task')
        logging.info(f"🔄 Starting Round 2 revision for repo: {repo_name}")
        try:
            repo = g.get_user().get_repo(repo_name)
        except UnknownObjectException:
            logging.error(f"🚨 Round 2 Error: Repository '{repo_name}' not found.")
            return

        try:
            existing_html_file = repo.get_contents("index.html")
            existing_readme_file = repo.get_contents("README.md")
            existing_html = existing_html_file.decoded_content.decode('utf-8')
        except Exception as e:
            logging.error(f"🚨 Round 2 Error: Could not fetch existing files. {e}")
            return

        new_brief = data.get('brief')
        updated_html = generate_revision_from_brief(new_brief, existing_html, data.get('checks'))
        if not updated_html:
            logging.error("Stopping Round 2 due to LLM failure.")
            return

        try:
            update_html_response = repo.update_file(
                path="index.html", message="feat: revise application for round 2",
                content=updated_html, sha=existing_html_file.sha
            )
            commit_sha = update_html_response['commit'].sha

            updated_readme = generate_professional_readme(new_brief, updated_html)
            repo.update_file(
                path="README.md", message="docs: update README for round 2",
                content=updated_readme, sha=existing_readme_file.sha
            )
            logging.info("🐙 Updated index.html and README.md in the repo.")
        except Exception as e:
            logging.error(f"🚨 Round 2 Error: Failed to update files on GitHub. {e}")
            return
            
        pages_url = f"https://{GITHUB_USERNAME}.github.io/{repo.name}/"
        
        notify_evaluation_api(data, repo.html_url, pages_url, commit_sha)
        logging.info("✅✅✅ Round 2 process completed! ✅✅✅")
    except Exception as e:
        logging.error(f"🚨 Round 2 Unexpected Error: {e}")
        import traceback
        traceback.print_exc()

# --- MAIN API ENDPOINT ---
@app.route('/api-endpoint', methods=['POST'])
def handle_request():
    """Receives requests and routes them to the correct background worker."""
    logging.info("✅ Request received!")
    data = request.get_json()

    if not data or data.get('secret') != os.getenv("MY_SECRET"):
        logging.error("🚨 ERROR: Invalid secret!")
        return jsonify({"error": "Invalid secret"}), 403

    round_number = data.get('round', 1)
    if round_number == 2:
        logging.info("✅ Secret verified. Starting Round 2 background job.")
        thread = threading.Thread(target=process_revise_request, args=(data,))
    else:
        logging.info("✅ Secret verified. Starting Round 1 background job.")
        thread = threading.Thread(target=process_build_request, args=(data,))
    
    thread.start()
    return jsonify({"status": f"Job for Round {round_number} accepted and is processing."}), 200

# --- SERVER START ---
if __name__ == '__main__':
    app.run(port=5000)