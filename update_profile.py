import urllib.request
import json
import datetime
import os
import re
import sys

def fetch_json(url, token=None):
    req = urllib.request.Request(url)
    req.add_header('User-Agent', '0xD4rkEYe-Profile-Updater')
    if token:
        req.add_header('Authorization', f'token {token}')
    try:
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode('utf-8'))
    except Exception as e:
        print(f"Error fetching {url}: {e}", file=sys.stderr)
        return None

def escape_xml(text):
    if not text:
        return "No description provided."
    # Standard XML escaping
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;").replace("'", "&apos;")
    # Trim to fit layout cleanly
    if len(text) > 48:
        return text[:45] + "..."
    return text

def get_utc_now():
    return datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)

def main():
    token = os.environ.get('GITHUB_TOKEN')
    username = "Padmapriyan27"
    
    # 1. Fetch User Data
    user_data = fetch_json(f"https://api.github.com/users/{username}", token)
    if not user_data:
        print("Failed to fetch user data.", file=sys.stderr)
        sys.exit(1)
        
    followers = user_data.get('followers', 0)
    public_repos_count = user_data.get('public_repos', 0)
    
    # 2. Fetch Repositories
    repos = fetch_json(f"https://api.github.com/users/{username}/repos?sort=pushed&per_page=100", token)
    if not repos:
        print("Failed to fetch repositories.", file=sys.stderr)
        sys.exit(1)
        
    total_stars = 0
    active_repos = []
    
    for r in repos:
        total_stars += r.get('stargazers_count', 0)
        # Skip the profile README repository itself
        if r.get('name').lower() == username.lower():
            continue
        # Skip fork repos to focus on personal work
        if r.get('fork', False):
            continue
        active_repos.append(r)
        
    # Sort repos by last pushed date descending
    active_repos.sort(key=lambda x: x.get('pushed_at', ''), reverse=True)
    
    # Calculate last push status
    last_push_str = user_data.get('updated_at', '')
    if active_repos:
        last_push_str = active_repos[0].get('pushed_at', last_push_str)
        
    status = "STANDBY"
    if last_push_str:
        try:
            last_push_dt = datetime.datetime.strptime(last_push_str, "%Y-%m-%dT%H:%M:%SZ")
            days_since_push = (get_utc_now() - last_push_dt).days
            if days_since_push <= 7:
                status = "ACTIVE_NODE"
            else:
                status = "STANDBY"
        except Exception:
            status = "ACTIVE_NODE"
            
    # 3. Update about.svg
    about_template_path = "assets/about.template.svg"
    about_output_path = "assets/about.svg"
    
    if os.path.exists(about_template_path):
        with open(about_template_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        content = content.replace("{{PUBLIC_REPOS}}", str(public_repos_count))
        content = content.replace("{{STATUS}}", status)
        content = content.replace("{{FOLLOWERS}}", str(followers))
        content = content.replace("{{TOTAL_STARS}}", str(total_stars))
        content = content.replace("{{DECK_STATUS}}", "SECURE // SHIELD_ON")
        
        utc_now = get_utc_now().strftime("%Y-%m-%d %H:%M UTC")
        content = content.replace("{{OPERATIONAL_STATUS}}", f"SYNCED // {utc_now}")
        
        with open(about_output_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print("Updated assets/about.svg successfully.")
    else:
        print(f"Error: Template not found at {about_template_path}", file=sys.stderr)

    # 4. Update projects.svg
    projects_template_path = "assets/projects.template.svg"
    projects_output_path = "assets/projects.svg"
    
    if os.path.exists(projects_template_path):
        with open(projects_template_path, 'r', encoding='utf-8') as f:
            p_content = f.read()
            
        # We need exactly 4 repos
        for i in range(1, 5):
            if len(active_repos) >= i:
                repo = active_repos[i-1]
                name = escape_xml(repo.get('name', '').upper())
                desc = escape_xml(repo.get('description', ''))
                lang = escape_xml(repo.get('language', 'Markdown'))
                
                # Calculate activity status and progress bar length
                pushed_at = repo.get('pushed_at', '')
                days_ago = 999
                if pushed_at:
                    try:
                        pushed_dt = datetime.datetime.strptime(pushed_at, "%Y-%m-%dT%H:%M:%SZ")
                        days_ago = (get_utc_now() - pushed_dt).days
                    except Exception:
                        pass
                
                if days_ago <= 14:
                    status_text = "ACTIVE // STABLE"
                    color_class = "card-val-highlight" # Green
                elif days_ago <= 60:
                    status_text = "OPERATIONAL // STABLE"
                    color_class = "card-val-highlight" # Green
                elif days_ago <= 180:
                    status_text = "STANDBY // MONITOR"
                    color_class = "card-val-yellow" # Yellow
                else:
                    status_text = "SLEEPING // STABLE"
                    color_class = "card-val-gray" # Gray
                    
                # Compute visual progress length (range 15 to 125)
                progress_len = int(max(15, min(125, 125 - (days_ago * 0.6))))
                
                p_content = p_content.replace(f"{{{{REPO_{i}_NAME}}}}", name)
                p_content = p_content.replace(f"{{{{REPO_{i}_DESC}}}}", desc)
                p_content = p_content.replace(f"{{{{REPO_{i}_LANG}}}}", lang)
                p_content = p_content.replace(f"{{{{REPO_{i}_STATUS}}}}", status_text)
                p_content = p_content.replace(f"{{{{REPO_{i}_COLOR_CLASS}}}}", color_class)
                p_content = p_content.replace(f"{{{{REPO_{i}_PROGRESS}}}}", str(progress_len))
            else:
                # Placeholder if user has less than 4 active repos
                p_content = p_content.replace(f"{{{{REPO_{i}_NAME}}}}", f"TARGET_SLOT_{i:02d}")
                p_content = p_content.replace(f"{{{{REPO_{i}_DESC}}}}", "No active operations allocated.")
                p_content = p_content.replace(f"{{{{REPO_{i}_LANG}}}}", "N/A")
                p_content = p_content.replace(f"{{{{REPO_{i}_STATUS}}}}", "SLEEPING // STABLE")
                p_content = p_content.replace(f"{{{{REPO_{i}_COLOR_CLASS}}}}", "card-val-gray")
                p_content = p_content.replace(f"{{{{REPO_{i}_PROGRESS}}}}", "15")
                
        with open(projects_output_path, 'w', encoding='utf-8') as f:
            f.write(p_content)
        print("Updated assets/projects.svg successfully.")
    else:
        print(f"Error: Template not found at {projects_template_path}", file=sys.stderr)

if __name__ == "__main__":
    main()
