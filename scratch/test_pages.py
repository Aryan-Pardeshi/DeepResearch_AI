import urllib.request

def fetch(url):
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req) as resp:
        return resp.read().decode('utf-8')

# 1. Test Landing Page
landing_html = fetch('http://127.0.0.1:8000/')
assert 'From research question to' in landing_html, 'Hero title missing'
assert 'gh-star-count-badge' in landing_html, 'GitHub star badge missing'
assert 'inspector-tabs' in landing_html, 'Inspector tabs missing'
assert 'The 5-Stage Academic Research Pipeline' in landing_html, 'Pipeline section missing'
assert 'AI does the research.' in landing_html, 'HITL section missing'
assert 'Two Ways to Research' in landing_html, 'Modes section missing'
assert 'Built as a real research system' in landing_html, 'Tech section missing'
assert 'href="/app"' in landing_html, 'CTA to /app missing'
assert 'mode=deepsearch' in landing_html, 'DeepSearch CTA missing'
assert 'mode=researchmode' in landing_html, 'Research Mode CTA missing'
print('Landing page content assertions: ALL PASSED')

# 2. Test App Workspace Page
app_html = fetch('http://127.0.0.1:8000/app')
assert 'tab-deepsearch' in app_html, 'DeepSearch tab missing'
assert 'tab-researchmode' in app_html, 'Research Mode tab missing'
assert 'rm-ps-input' in app_html, 'Research Mode input missing'
assert 'query-input' in app_html, 'DeepSearch query input missing'
assert 'rm-tracker-card' in app_html, 'Pipeline tracker missing'
assert 'rm-hitl-panel' in app_html, 'HITL panel missing'
assert 'rm-paper-card' in app_html, 'Paper card missing'
assert 'rm-export-dropdown' in app_html, 'Export dropdown missing'
assert 'app.js' in app_html, 'app.js script tag missing'
assert 'style.css' in app_html, 'style.css stylesheet tag missing'
print('App workspace content assertions: ALL PASSED')

print('\n*** COMPLETE PAGE INTEGRITY VERIFICATION SUCCESSFUL! ***')
