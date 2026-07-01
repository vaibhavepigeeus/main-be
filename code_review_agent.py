import os
import re
import io
import json
import requests
import argparse
import boto3
import difflib
import pdfkit
import base64
import html
from botocore.exceptions import ClientError
from langgraph.graph import StateGraph
from typing import TypedDict
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from PyPDF2 import PdfReader, PdfWriter

# config = pdfkit.configuration(
#     wkhtmltopdf=r"C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe"
# )

# ----- State Schema -----
class ReviewState(TypedDict):
    repo: str
    pr_number: int
    diff_text: str
    summary: str
    jira_tickets: list
    merged_at: str
    commit_users: list
    environment: str
    merged_by: str
    file_changes: str

# ====== CONFIG ======
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
HEADERS = {"Authorization": f"token {GITHUB_TOKEN}"}
MAX_CHUNK_SIZE = 100000
AWS_REGION = os.getenv("AWS_REGION")
bucket_name = os.getenv("S3_BUCKET_NAME")
JIRA_PATTERN = re.compile(r"\b[A-Z]{2,10}-\d+\b")

# ====== Helper Functions ======
def get_pr_branch(repo: str, pr_number: int) -> str:
    url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}"
    resp = requests.get(url, headers=HEADERS)
    resp.raise_for_status()
    pr_data = resp.json()
    return pr_data["base"]["ref"]

def upload_to_s3(file_path: str, bucket: str, object_key: str):
    try:
        s3 = boto3.client(
            "s3",
            region_name=AWS_REGION,
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        )
        s3.upload_file(file_path, bucket, object_key)
        print(f"Uploaded {file_path} to s3://{bucket}/{object_key}")
    except Exception as e:
        print(f"Error while uploading to s3: {e}")

def save_summary_to_pdf(summary: str, html_text: str, filename: str) -> str:
    # --- Step 1: Create canvas PDF in memory ---
    canvas_buffer = io.BytesIO()
    c = canvas.Canvas(canvas_buffer, pagesize=letter)
    width, height = letter

    c.setFont("Helvetica", 10)
    margin, y = 50, height - 50
    max_line_width = width - 2 * margin

    for line in summary.splitlines():
        if not line.strip():
            y -= 15
            continue

        title_with_value = re.match(r"^\*\*(.+?)\*\*:\s*(.*)$", line.strip())
        if title_with_value:
            label = f"{title_with_value.group(1)}:"
            value = title_with_value.group(2)
            c.setFont("Helvetica-Bold", 10)
            c.drawString(margin, y, label)
            if value:
                label_width = c.stringWidth(label + " ", "Helvetica-Bold", 10)
                c.setFont("Helvetica", 10)
                c.drawString(margin + label_width, y, value)
            y -= 15
            if y < margin:
                c.showPage()
                c.setFont("Helvetica", 10)
                y = height - 50
            c.setFont("Helvetica", 10)
            continue

        words = line.split()
        current_line = ""
        for word in words:
            if c.stringWidth(current_line + " " + word, "Helvetica", 10) > max_line_width:
                c.drawString(margin, y, current_line.strip())
                y -= 15
                current_line = word
                if y < margin:
                    c.showPage()
                    c.setFont("Helvetica", 10)
                    y = height - 50
            else:
                current_line += " " + word
        if current_line.strip():
            c.drawString(margin, y, current_line.strip())
            y -= 15
            if y < margin:
                c.showPage()
                c.setFont("Helvetica", 10)
                y = height - 50

    c.save()
    canvas_buffer.seek(0)

    # This returns PDF content as bytes
    # pdf_bytes = pdfkit.from_string(html_text, False, configuration=config)
    pdf_bytes = pdfkit.from_string(html_text, False)

    # Wrap in BytesIO to merge later
    html_pdf_buffer = io.BytesIO(pdf_bytes)
    html_pdf_buffer.seek(0)

    # --- Step 3: Merge PDFs ---
    writer = PdfWriter()
    for pdf_buffer in [canvas_buffer, html_pdf_buffer]:
        reader = PdfReader(pdf_buffer)
        for page in reader.pages:
            writer.add_page(page)

    # Save merged PDF
    with open(filename, "wb") as f_out:
        writer.write(f_out)

    return filename

def get_pr_merged_date(repo: str, pr_number: int):
    """Return the PR merged date (ISO 8601 string) or None if not merged."""
    try:
        url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}"
        resp = requests.get(url, headers=HEADERS)
        resp.raise_for_status()
        pr_data = resp.json()
        return pr_data.get("merged_at"), pr_data["merged_by"]["login"]
    except Exception as e:
        print(f" Error fetching merged date: {e}")
        return None

def format_iso_datetime(dt_iso: str) -> str:
    """Convert ISO 8601 (e.g., 2025-09-30T09:56:32Z) to a readable local string.
    Falls back gracefully if parsing fails or value is falsy.
    """
    if not dt_iso:
        return "Not merged"
    try:
        # Avoid heavy dependencies; use built-in fromisoformat with a small fix for 'Z'
        iso = dt_iso.replace("Z", "+00:00")
        from datetime import datetime
        dt = datetime.fromisoformat(iso)
        # Represent in local time with date and time
        local_dt = dt.astimezone()
        return local_dt.strftime("%Y-%m-%d %H:%M:%S %Z")
    except Exception:
        return dt_iso

def get_pr_commits(repo: str, pr_number: int):
    """Return a list of (commit_sha, author_name, author_login) for all commits in a PR."""
    try:
        url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}/commits"
        commits = []
        page = 1
        while True:
            resp = requests.get(f"{url}?page={page}&per_page=100", headers=HEADERS)
            resp.raise_for_status()
            data = resp.json()
            if not data:
                break
            for c in data:
                sha = c["sha"]
                author_name = c["commit"]["author"]["name"]
                author_login = c["author"]["login"] if c.get("author") else None
                commits.append((sha, author_name, author_login))
            page += 1

        # Get changed files
        files_url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}/files"
        files_resp = requests.get(files_url, headers=HEADERS)
        files_resp.raise_for_status()
        files_data = files_resp.json()

        changed_files = [
            {
                "filename": f["filename"],
                "status": f["status"],           # added, modified, removed, renamed
                "additions": f["additions"],
                "deletions": f["deletions"],
                "changes": f["changes"]
            }
            for f in files_data
        ]

        return commits, changed_files
    except Exception as e:
        print(f"Error fetching commits: {e}")
        return []

def get_file_content_from_sha(repo: str, file_path: str, ref: str) -> list[str] | None:
    """Fetches raw file content from a specific git reference (SHA, branch, tag)."""
    content_url = f"https://api.github.com/repos/{repo}/contents/{file_path}?ref={ref}"
    HEADERS = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
    }
    try:
        resp = requests.get(content_url, headers=HEADERS)
        resp.raise_for_status()
        data = resp.json()
        
        if 'content' in data:
            decoded_content = base64.b64decode(data['content']).decode('utf-8')
            return decoded_content.splitlines()
        else:
            return []

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            return []
        print(f"Error fetching content for {file_path} at {ref}: {e}")
        raise

def generate_contextual_html_from_diff(diff_lines: list[str]) -> str:
    """
    Converts the output of difflib.unified_diff into an HTML table with line numbers.
    """
    html_table = '<table class="diff-table">'
    
    # Regex to parse the hunk header (e.g., "@@ -34,6 +34,7 @@")
    hunk_re = re.compile(r'^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@.*$')
    
    old_line_num, new_line_num = 0, 0
    
    for line in diff_lines:
        if line.startswith('---') or line.startswith('+++'):
            continue # Skip file headers
        
        match = hunk_re.match(line)
        if match:
            # Extract starting line numbers from the hunk header
            old_line_num = int(match.group(1))
            new_line_num = int(match.group(3))
            
            # Display the hunk header itself
            html_table += f'<tr class="diff-hunk"><td class="line-num">...</td><td class="line-num">...</td><td colspan="2">{html.escape(line)}</td></tr>'
            continue
            
        escaped_line = html.escape(line[1:])
        
        if line.startswith('+'):
            html_table += f'<tr class="diff-add"><td class="line-num"></td><td class="line-num">{new_line_num}</td><td>+</td><td class="code-line">{escaped_line}</td></tr>'
            new_line_num += 1
        elif line.startswith('-'):
            html_table += f'<tr class="diff-del"><td class="line-num">{old_line_num}</td><td class="line-num"></td><td>-</td><td class="code-line">{escaped_line}</td></tr>'
            old_line_num += 1
        else: # Context line
            html_table += f'<tr class="diff-context"><td class="line-num">{old_line_num}</td><td class="line-num">{new_line_num}</td><td> </td><td class="code-line">{escaped_line}</td></tr>'
            old_line_num += 1
            new_line_num += 1
            
    html_table += '</table>'
    return html_table

def get_pr_html_diff_exact(repo: str, pr_number: int):
    """
    Generate an HTML diff page that displays ONLY the actual changes
    (the diff hunks) from GitHub’s PR API, not a full file diff.
    """
    try:
        files_url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}/files"
        files_resp = requests.get(files_url, headers=HEADERS)
        files_resp.raise_for_status()
        files_data = files_resp.json()

        html_output = """
        <html>
        <head>
            <title>PR Diff (Changed Lines Only)</title>
            <style>
                body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif; margin: 2em; }
                .diff-container { border: 1px solid #ddd; border-radius: 5px; margin-bottom: 2em; overflow: hidden; }
                .file-header { background-color: #f6f8fa; padding: 10px; font-weight: bold; border-bottom: 1px solid #ddd; }
                pre { margin: 0; font-family: monospace; font-size: 12px; white-space: pre-wrap; word-wrap: break-word; }
                .diff-add { background-color: #e6ffed; }
                .diff-del { background-color: #ffeef0; }
                .diff-hunk { background-color: #f1f8ff; color: #555; }
            </style>
        </head>
        <body>
        """
        html_output += f"<h1>Pull Request #{pr_number} - Changed Lines</h1>"

        for f in files_data:
            filename = f["filename"]
            status = f["status"]
            patch = f.get("patch")

            if not patch:
                # GitHub omits 'patch' for binary or large files
                continue

            html_output += f'<div class="diff-container">'
            html_output += f'<div class="file-header">{filename} - {status}</div>'
            html_output += '<pre>'

            for line in patch.splitlines():
                esc_line = html.escape(line)
                if line.startswith('@@'):
                    html_output += f'<span class="diff-hunk">{esc_line}</span>\n'
                elif line.startswith('+'):
                    html_output += f'<span class="diff-add">{esc_line}</span>\n'
                elif line.startswith('-'):
                    html_output += f'<span class="diff-del">{esc_line}</span>\n'
                else:
                    html_output += esc_line + '\n'

            html_output += '</pre></div>'

        html_output += "</body></html>"
        return html_output

    except Exception as e:
        print(f"Error generating HTML diff: {e}")
        return None

def send_email_with_attachment(sender, subject, body_text, file_path):
    ses_client = boto3.client(
        "ses",
        region_name=AWS_REGION,
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    )

    recipients = os.getenv("EMAIL_RECIPIENTS", "").split(",")
    recipients = [r.strip() for r in recipients if r.strip()]

    if not recipients:
        print(" No recipients configured in EMAIL_RECIPIENTS env var")
        return

    with open(file_path, "rb") as f:
        attachment_data = f.read()

    sent_count = 0
    skipped_count = 0

    for recipient in recipients:
        msg = MIMEMultipart()
        msg["Subject"] = subject
        msg["From"] = sender
        msg["To"] = recipient

        msg.attach(MIMEText(body_text, "plain"))

        part = MIMEApplication(attachment_data)
        part.add_header(
            "Content-Disposition",
            "attachment",
            filename=os.path.basename(file_path)
        )
        msg.attach(part)

        try:
            response = ses_client.send_raw_email(
                Source=sender,
                Destinations=[recipient],
                RawMessage={"Data": msg.as_string()}
            )
            print(f"Email sent to {recipient}! Message ID: {response['MessageId']}")
            sent_count += 1

        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            error_message = e.response["Error"]["Message"]

            if error_code == "MessageRejected":
                print(f" Email NOT sent to {recipient}: address not verified ({error_message})")
                skipped_count += 1
            else:
                print(f" Failed to send email to {recipient}: {error_code} - {error_message}")
                skipped_count += 1

        except Exception as e:
            print(f" Unexpected error sending to {recipient}: {e}")
            skipped_count += 1

    print("\n=== Email Sending Summary ===")
    print(f"Successfully sent: {sent_count}")
    print(f"Skipped/failed: {skipped_count}")
    print("=============================")

# Configure Bedrock client
bedrock = boto3.client(
    service_name="bedrock-runtime",
    region_name="us-east-1",
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"), # Replace with your AWS Access Key
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY") # Replace with your AWS Secret Key
)

# ---------- PR REVIEW NODES ----------
def fetch_pr_commits_node(repo, pr_number):
    # --- Get PR details (to extract description) ---
    pr_url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}"
    pr_resp = requests.get(pr_url, headers=HEADERS)
    pr_resp.raise_for_status()
    pr_data = pr_resp.json()
    pr_description = pr_data.get("body", "")

    # # --- Get PR commits ---
    # commits_url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}/commits"
    # resp = requests.get(commits_url, headers=HEADERS)
    # resp.raise_for_status()
    # commits = resp.json()

    # print(f"\nFound {len(commits)} commits in PR #{pr_number}:\n")
    # for i, commit in enumerate(commits, 1):
    #     sha = commit["sha"]
    #     msg = commit["commit"]["message"].split("\n")[0]
    #     print(f"{i}. {sha} - {msg}")

    # selected = input("\nEnter commit number or SHA to review (default latest): ").strip()
    # if not selected:
    #     selected_commit = commits[-1]
    # else:
    #     selected_commit = None
    #     if selected.isdigit():
    #         idx = int(selected) - 1
    #         if 0 <= idx < len(commits):
    #             selected_commit = commits[idx]
    #     if selected_commit is None:
    #         for c in commits:
    #             if c["sha"].startswith(selected):
    #                 selected_commit = c
    #                 break
    #     if selected_commit is None:
    #         raise ValueError("Invalid commit selection.")

    # commit_sha = selected_commit["sha"]
    # commit_msg = selected_commit["commit"]["message"]

    # # --- Get commit details (to extract file diffs) ---
    # commit_url = f"https://api.github.com/repos/{repo}/commits/{commit_sha}"
    # commit_resp = requests.get(commit_url, headers=HEADERS)
    # commit_resp.raise_for_status()
    # commit_data = commit_resp.json()

    # files = commit_data.get("files", [])
    # diffs = "\n\n".join(
    #     [f"File: {f['filename']}\nPatch:\n{f.get('patch', '')}" for f in files]
    # )

    # # --- Detect Jira tickets from commit, diff, and PR description ---
    detected_tickets = set()
    # detected_tickets.update(JIRA_PATTERN.findall(commit_msg))
    # detected_tickets.update(JIRA_PATTERN.findall(diffs))

    if pr_description is not None:
        detected_tickets.update(JIRA_PATTERN.findall(pr_description))
        print("\nDetected Jira Tickets:", ", ".join(detected_tickets))
    else:
        print("\nNo Jira tickets detected.")

    return detected_tickets

def fetch_pr_files_node(state: ReviewState) -> ReviewState:
    repo = state["repo"]
    pr_number = state["pr_number"]

    # Fetch changed files in PR
    files_url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}/files"
    resp = requests.get(files_url, headers=HEADERS)
    resp.raise_for_status()
    files = resp.json()

    print(f"\nFound {len(files)} files changed in PR #{pr_number}:\n")
    for i, f in enumerate(files, 1):
        print(f"{i}. {f['filename']}")

    diffs = "\n\n".join(
        [f"File: {f['filename']}\nPatch:\n{f.get('patch', '')}" for f in files]
    )

    # # Detect Jira tickets
    # detected_tickets = JIRA_PATTERN.findall(diffs)
    # if detected_tickets:
    #     print("\nDetected Jira Tickets:", ", ".join(set(detected_tickets)))
    # else:
    #     print("\nNo Jira tickets detected.")

    jira_tickets = fetch_pr_commits_node(repo, pr_number)

    merged_at_raw, merged_by = get_pr_merged_date(repo, pr_number)
    merged_at_formatted = format_iso_datetime(merged_at_raw)

    commits, file_changes_data = get_pr_commits(repo, pr_number)

    html_output = get_pr_html_diff_exact(repo, pr_number)

    commit_users = []
    for sha, name, login in commits:
        if name not in commit_users:
            commit_users.append(name)

    environment = get_pr_branch(args.repo, args.pr)

    return {
        **state, 
        "diff_text": diffs, 
        "jira_tickets": list(jira_tickets), 
        "merged_at": merged_at_formatted, 
        "commit_users": commit_users, 
        "environment": environment,
        "merged_by": merged_by,
        "file_changes": html_output
    }


def chunk_text(text: str, chunk_size: int = MAX_CHUNK_SIZE):
    """Split text into chunks without breaking lines mid-way."""
    lines = text.splitlines()
    chunks = []
    current_chunk = []
    current_size = 0

    for line in lines:
        line_size = len(line) + 1  # account for newline
        if current_size + line_size > chunk_size:
            chunks.append("\n".join(current_chunk))
            current_chunk = []
            current_size = 0
        current_chunk.append(line)
        current_size += line_size

    if current_chunk:
        chunks.append("\n".join(current_chunk))

    return chunks

def summarize_node(state: ReviewState) -> ReviewState:
    diff_text = state["diff_text"]
    merged_at = state["merged_at"]

    chunks = chunk_text(diff_text)
    summaries = []

    jira_tickets = state["jira_tickets"]
    commit_users = state["commit_users"]
    environment = state["environment"]
    merged_by = state["merged_by"]
    for idx, chunk in enumerate(chunks, 1):
        if not chunk.strip():
            continue

        prompt = f"""
You are a senior software engineer performing a detailed commit review.

OUTPUT FORMAT REQUIREMENTS:
- Produce PLAIN TEXT only; no headings, emojis, or code fences.
- Bold ONLY the five section titles using double asterisks; everything else must be plain text.
- Use the following exact section labels on their own lines:
  **PR Number**:
  **Environment**:
  **PR Merged AT**:
  **PR Commiters**:
  **PR Merger**:
  **JIRA Ticket Review**:
  **Summary of Changes**:
  **Coding Standards**:
  **Security Review**:
  **Functionality Review**:
- Within each section, use simple hyphen-prefixed lines (e.g., "- ") for points.

Instructions:
- Highlight what is done well.
- Point out issues with line/file references and suggest specific fixes.
- If no issues are found in a section, write: No issues found.

JIRA Ticket Review details:
- The detected Jira tickets for this commit are: {jira_tickets}.
- If one or more valid Jira ticket IDs are present (format ABC-123), acknowledge them as valid.
- If no valid tickets are found, state: JIRA ticket reference is missing. Please link the commit to the appropriate ticket.

PR Merged AT details: {merged_at}

PR Number details: {state['pr_number']}

PR Commiters details: {', '.join(commit_users)}

PR Merger details: {merged_by}

Environment details: {environment}

CODE DIFF (Chunk {idx}/{len(chunks)}):
{chunk}
"""

        try:
            response = bedrock.invoke_model(
                modelId="arn:aws:bedrock:us-east-1:767398071985:inference-profile/global.anthropic.claude-sonnet-4-20250514-v1:0",
                body=json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 1000,
                    "messages": [
                        {"role": "user", "content": [{"type": "text", "text": prompt}]}
                    ]
                }),
                contentType="application/json",
                accept="application/json"
            )

            result = json.loads(response["body"].read())
            # ✅ Correct way to extract Claude output
            text_summary = "".join(
                [c["text"] for c in result.get("content", []) if c["type"] == "text"]
            ) or "[No output from model]"

            summaries.append(f"\n{text_summary}")

        except Exception as e:
            summaries.append(f"[Error summarizing chunk {idx}: {e}]")

    return {**state, "summary": "\n\n".join(summaries)}

# Build LangGraph workflow
graph = StateGraph(ReviewState)
graph.add_node("fetch_files", fetch_pr_files_node)
graph.add_node("summarize", summarize_node)
graph.add_edge("fetch_files", "summarize")
graph.set_entry_point("fetch_files")
graph.set_finish_point("summarize")
app = graph.compile()


# ====== Main ======
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True, help="GitHub repo (e.g., org/repo)")
    parser.add_argument("--pr", required=True, type=int, help="Pull request number")
    args = parser.parse_args()

    output = app.invoke({
        "repo": args.repo,
        "pr_number": args.pr,
        "diff_text": "",
        "summary": "",
        "jira_tickets": [],
        "merged_at": "",
        "commit_users": [],
        "environment": "",
        "merged_by": "",
        "file_changes": ""
    })

    summary_text = output.get("summary", str(output))
    html_text = output.get("file_changes", str(output))

    environment = get_pr_branch(args.repo, args.pr)

    jira_tickets = fetch_pr_commits_node(args.repo, args.pr)

    if environment in ["sit-env", "sit-env-fe"]:
        pre_folder = "SIT/"
    elif environment in ["uat3"]:
        pre_folder = "UAT/"
    elif environment in ["pre-production"]:
        pre_folder = "PREPROD/"
    elif environment in ["prod", "Production"]:
        pre_folder = "PROD/"
    else:
        pre_folder = ""

    pdf_filename = f"BE_{', '.join(list(jira_tickets))}_PR_{args.pr}_review_summary.pdf"
    save_summary_to_pdf(summary_text, html_text, pdf_filename)

    object_key = f"{pre_folder}{pdf_filename}"
    upload_to_s3(pdf_filename, os.getenv("S3_BUCKET_NAME"), object_key)

    # Send Email After Upload
    sender = os.getenv("SES_SENDER")
    subject = f"BE Jira#{', '.join(list(jira_tickets))} PR#{args.pr} {environment} Review Summary"
    pr_url = f"https://github.com/{args.repo}/pull/{args.pr}"
    merged_at_raw, merged_by = get_pr_merged_date(args.repo, args.pr)
    merged_at = format_iso_datetime(merged_at_raw)
    merged_line = f"Merged At: {merged_at}"
    body_text = f"""Hello,

The review summary for PR #{args.pr} has been generated.
Branch: {environment}
Jira Tickets: {', '.join(list(jira_tickets))}
PR Link: {pr_url}
{merged_line}

Please find the attached PDF.

Regards
"""

    send_email_with_attachment(sender, subject, body_text, pdf_filename)

    print(f"\n=== Review Summary for PR #{args.pr} on branch {environment} ===\n")
    # Strip Markdown asterisks from section titles for console output
    cleaned_summary = re.sub(r"\*\*(.+?)\*\*:", r"\1:", summary_text)
    # print(cleaned_summary)
