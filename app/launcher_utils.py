import os
import subprocess
import sys
import time

def close_yam_instances():
    exe_name = 'YAM.exe'
    print(f'Closing all running instances of {exe_name}...')
    if sys.platform == 'win32':
        subprocess.run(['taskkill', '/IM', exe_name, '/F'], shell=True)
    else:
        subprocess.run(['pkill', '-f', exe_name])
    time.sleep(2)
    print('All instances closed.')

def clear_icon_cache():
    print('Clearing Windows icon cache...')
    if sys.platform == 'win32':
        subprocess.run('ie4uinit.exe -show', shell=True)
        subprocess.run('taskkill /IM explorer.exe /F', shell=True)
        subprocess.run('DEL /A /Q "%localappdata%\IconCache.db"', shell=True)
        subprocess.run('start explorer.exe', shell=True)
    print('Icon cache cleared.')

if __name__ == '__main__':
    close_yam_instances()
    clear_icon_cache() 