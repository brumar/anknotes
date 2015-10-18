# Python Imports
import os
import shutil
from fnmatch import fnmatch
from datetime import datetime
import time

# Anknotes Main Imports
from anknotes.constants_standard import FILES, FOLDERS, ANKNOTES
from anknotes.base import encode, item_to_list

def write_file_contents(content, full_path, clear=False, try_encode=True, do_print=False, print_timestamp=True,
                        print_content=None, wfc_timestamp=True, wfc_crosspost=None, get_log_full_path=None, **kwargs):        
    all_args = locals()
    if wfc_crosspost:
        del all_args['kwargs'], all_args['wfc_crosspost'], all_args['content'], all_args['full_path']
        all_args.update(kwargs)
        for cp in item_to_list(wfc_crosspost):
            write_file_contents(content, cp, **all_args)
    orig_path = full_path
    if not os.path.exists(os.path.dirname(full_path)):
        if callable(get_log_full_path):
            full_path = get_log_full_path(full_path)
            if full_path is False:
                return
        else:
            full_path = os.path.abspath(os.path.join(FOLDERS.LOGS, full_path + '.log'))
            base_path = os.path.dirname(full_path)
            if not os.path.exists(base_path):
                os.makedirs(base_path)
            if wfc_timestamp:
                print_content = content
                content = '[%s]: ' % datetime.now().strftime(ANKNOTES.DATE_FORMAT) + content
    with open(full_path, 'w+' if clear else 'a+') as fileLog:
        try:
            print>> fileLog, content
        except UnicodeEncodeError:
            content = encode(content)
            print>> fileLog, content
    if do_print:
        print content if print_timestamp or not print_content else print_content
        
def filter_logs(filename):
    def do_filter(x): return fnmatch(filename, x)
    return (filter(do_filter, item_to_list(FILES.LOGS.ENABLED)) and not 
            filter(do_filter, item_to_list(FILES.LOGS.DISABLED)))
        
def reset_logs(folder='', banner='', clear=True, *a, **kw):
    absolutely_unused_variable = os.system("cls")
    keep = ['anknotes', 'api', 'automation']    
    folder = os.path.join(FOLDERS.LOGS, folder)
    logs = os.listdir(folder)
    for fn in logs:
        full_path = os.path.join(folder, fn)
        if os.path.isfile(full_path):
            if filter(lambda x: fnmatch(fn, x + '*'), keep):
                continue
            if clear:
                with open(full_path, 'w+') as myFile:
                    if banner:
                        print >> myFile, banner
            else:
                os.unlink(full_path)
        else:
            rm_log_path(fn)
            
def rm_log_path(filename='*', subfolders_only=False, retry_errors=0, get_log_full_path=None, *args, **kwargs):
    def del_subfolder(arg=None, dirname=None, filenames=None, is_subfolder=True):
        def rmtree_error(f, p, e):
            rm_log_path.errors += [p]
        
        # Begin del_subfolder
        if is_subfolder and dirname is path:
            return
        shutil.rmtree(dirname, onerror=rmtree_error)    
    
    # Begin rm_log_path
    if callable(get_log_full_path):
        path = get_log_full_path(filename, filter_disabled=False)
    else:
        path = filename
        if FOLDERS.LOGS not in path.strip(os.path.sep):
            path = os.path.join(FOLDERS.LOGS, path)
    path = os.path.abspath(path)
    if not os.path.isdir(path):
        path = os.path.dirname(path)
    if path is FOLDERS.LOGS or FOLDERS.LOGS not in path:
        return
    rm_log_path.errors = []

    if not subfolders_only:
        del_subfolder(dirname=path, is_subfolder=False)
    else:
        os.path.walk(path, del_subfolder, None)
    if rm_log_path.errors:
        if retry_errors > 5:
            print "Unable to delete log path: " + path + ' -> ' + filename
            write_file_contents("Unable to delete log path as requested", filename)
            return
        time.sleep(1)
        rm_log_path(filename, subfolders_only, retry_errors + 1)    
        