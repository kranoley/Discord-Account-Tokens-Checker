from flask import Flask, request, redirect, url_for, render_template, jsonify
from config import config
from discord.checker import check_tokens, get_status, stop_check
import re
from tkinter.filedialog import askopenfilename
import os
import threading
from typing import Optional, Tuple, List



def extract_placeholders(template: str) -> List[str]:
    matches = re.findall(r'\{(\w+)\}', template)
    seen = set()
    unique = []
    for name in matches:
        if name not in seen:
            seen.add(name)
            unique.append(name)
    return unique



def get_tokens(file_path: str) -> Optional[Tuple[int, List[str]]]:
    TOKEN_PATTERN = re.compile(r'[\w-]{24,26}\.[\w-]{6}\.[\w-]{27,45}')
    if not os.path.isfile(file_path):
        return None
    
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
    except Exception:
        return None
    
    matches = TOKEN_PATTERN.findall(content)
    tokens = list(dict.fromkeys(matches))
    
    if not tokens:
        return None
    
    return len(tokens), tokens


cfg = config
app = Flask(__name__)


@app.route('/exit')
def exit():
    quit()


@app.route('/')
def home():
    return render_template('main.html', tokens_count=len(cfg['tokens']))


@app.route('/start_check')
def start_check():
    if not cfg['tokens']:
        return render_template('main.html', tokens_count=len(cfg['tokens']))
    
    def run_check():
        check_tokens(cfg)
    
    check_thread = threading.Thread(target=run_check)
    check_thread.daemon = True
    check_thread.start()
    
    return render_template('checking.html', total=len(cfg['tokens']))


@app.route('/api/check_status')
def api_check_status():
    status = get_status()
    return jsonify(status)


@app.route('/api/stop_check', methods=['POST'])
def api_stop_check():
    stop_check()
    return jsonify({'success': True})


@app.route('/upload_file')
def upload_file():
    path = askopenfilename()
    
    if path:
        cfg['path'] = path
        gt = get_tokens(file_path=cfg['path'])
        if gt:
            cfg['tokens'] = gt[1]
    
    return render_template('main.html', tokens_count=len(cfg['tokens']))


@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if request.method == 'POST':
        threads = request.form.get('threads', type=int)
        timeout = request.form.get('timeout', type=int)
        output_format = request.form.get('output_format', '').strip()
        
        if threads and cfg['min_threads'] <= threads <= cfg['max_threads']:
            cfg['threads'] = threads
        
        if timeout and cfg['min_timeout'] <= timeout <= cfg['max_timeout']:
            cfg['timeout'] = timeout
        
        if output_format:
            output_format_placeholders = extract_placeholders(output_format)
            if output_format_placeholders:
                all_valid = all(
                    placeholder in cfg['all_formats']
                    for placeholder in output_format_placeholders
                )
                if all_valid:
                    cfg['format'] = output_format
        
        return redirect(url_for('home'))
    
    return render_template('settings.html')
