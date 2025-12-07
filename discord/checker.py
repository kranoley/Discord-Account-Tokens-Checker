import requests
import threading
import time
from queue import Queue
import os
from typing import Optional, Dict, Any

FILESTART = """
Discord Account Tokens Checker
https://github.com/kranoley/Discord-Account-Tokens-Checker  
V0.1

Valid tokens - {valid_count}


"""


check_status = {
    'checked': 0,
    'valid': 0,
    'invalid': 0,
    'error': 0,
    'is_running': False,
    'should_stop': False,
    'start_time': None,
    'total': 0
}
status_lock = threading.Lock()


def reset_status(total: int) -> None:
    with status_lock:
        check_status['checked'] = 0
        check_status['valid'] = 0
        check_status['invalid'] = 0
        check_status['error'] = 0
        check_status['is_running'] = True
        check_status['should_stop'] = False
        check_status['start_time'] = time.time()
        check_status['total'] = total


def get_status() -> Dict[str, Any]:
    with status_lock:
        elapsed = 0
        if check_status['start_time']:
            elapsed = int(time.time() - check_status['start_time'])
        return {
            'checked': check_status['checked'],
            'valid': check_status['valid'],
            'invalid': check_status['invalid'],
            'error': check_status['error'],
            'is_running': check_status['is_running'],
            'total': check_status['total'],
            'elapsed_time': elapsed
        }


def stop_check() -> None:
    with status_lock:
        check_status['should_stop'] = True


def get_account(token: str, timeout: int) -> Optional[Dict[str, Any]]:
    headers = {
        "authorization": token,
    }
    try:
        req = requests.get(
            "https://discord.com/api/v9/users/@me",
            headers=headers,
            timeout=timeout
        )
        if req.status_code == 200:
            return req.json()
        elif req.status_code == 401:
            return False
        else:
            return None
    except Exception:
        return None


def process_tokens(
    token_queue: Queue,
    valid_tokens: list,
    cfg: Dict[str, Any],
    lock: threading.Lock,
    timeout: int
) -> None:
    while not token_queue.empty():
        with status_lock:
            if check_status['should_stop']:
                break
        
        try:
            token = token_queue.get_nowait()
        except Exception:
            break
        
        try:
            account_data = get_account(token.strip(), timeout)
            
            with status_lock:
                check_status['checked'] += 1
            
            if account_data is False:
                with status_lock:
                    check_status['invalid'] += 1
            elif account_data:
                format_str = cfg['format']
                formatted_token = format_str
                
                for field in [
                    'id', 'username', 'global_name', 'mfa_enabled',
                    'locale', 'email', 'verified', 'phone'
                ]:
                    if field in account_data:
                        placeholder = "{" + field + "}"
                        formatted_token = formatted_token.replace(
                            placeholder,
                            str(account_data[field])
                        )
                
                formatted_token = formatted_token.replace(
                    "{token}",
                    token.strip()
                )
                
                with lock:
                    valid_tokens.append(formatted_token)
                
                with status_lock:
                    check_status['valid'] += 1
            else:
                with status_lock:
                    check_status['error'] += 1
                    
        except Exception:
            with status_lock:
                check_status['error'] += 1
        
        token_queue.task_done()


def check_tokens(cfg: Dict[str, Any]) -> int:
    timeout = cfg['timeout']
    threads_count = cfg['threads']
    path = os.path.dirname(cfg['path'])
    tokens = cfg['tokens']
    
    if not tokens:
        return 0
    
    token_queue = Queue()
    valid_tokens = []
    lock = threading.Lock()
    

    reset_status(len(tokens))
    

    for token in tokens:
        token_queue.put(token)
    

    threads = []
    threads_to_create = min(threads_count, token_queue.qsize())
    
    for _ in range(threads_to_create):
        thread = threading.Thread(
            target=process_tokens,
            args=(token_queue, valid_tokens, cfg, lock, timeout)
        )
        thread.daemon = True
        thread.start()
        threads.append(thread)
    
    try:
        token_queue.join()
    except Exception:
        pass
    
    for thread in threads:
        thread.join(timeout=1)
    

    was_stopped = False
    with status_lock:
        was_stopped = check_status['should_stop']
        check_status['is_running'] = False
    
    if valid_tokens or not was_stopped:
        results_content = FILESTART.format(valid_count=len(valid_tokens))
        if valid_tokens:
            results_content += "\n".join(valid_tokens)
        
        os.makedirs(path, exist_ok=True)
        
        results_path = os.path.join(path, "results.txt")
        with open(results_path, "w", encoding="utf-8") as f:
            f.write(results_content)
    
    return len(valid_tokens)
