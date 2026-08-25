import os
import subprocess
import http.server
import socketserver
import threading
import time
import urllib.request
from urllib.parse import urljoin

PORT = 8080
OUTPUT_DIR = "hls_output"
os.makedirs(os.path.abspath(OUTPUT_DIR), exist_ok=True)

TARGET_STREAM = 'http://hydratv.pro:80/live/076431648/0977842887/415773.m3u8'
local_m3u8_input = os.path.join(os.path.abspath(OUTPUT_DIR), 'local_input.m3u8')
output_m3u8_path = os.path.join(os.path.abspath(OUTPUT_DIR), 'output.m3u8')

def update_manifest_loop():
    while True:
        try:
            req = urllib.request.Request(
                TARGET_STREAM,
                headers={'User-Agent': 'ExoPlayerLib/2.18.1 (Linux;Android 11)', 'Accept': '*/*'}
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                final_url = response.url
                data = response.read().decode('utf-8')
            
            if data and '#EXTM3U' in data:
                lines = data.split('\n')
                new_lines = []
                for line in lines:
                    trimmed = line.strip()
                    if trimmed and not trimmed.startswith('#'):
                        absolute_url = urljoin(final_url, trimmed)
                        new_lines.append(absolute_url)
                    else:
                        new_lines.append(line)
                
                updated_data = '\n'.join(new_lines)
                tmp_file = local_m3u8_input + '.tmp'
                with open(tmp_file, 'w', encoding='utf-8') as f:
                    f.write(updated_data)
                os.replace(tmp_file, local_m3u8_input)
        except Exception as e:
            pass
        time.sleep(2)

def start_ffmpeg():
    while not os.path.exists(local_m3u8_input):
        time.sleep(1)
    
    ffmpeg_cmd = [
        'ffmpeg', '-re',
        '-protocol_whitelist', 'file,http,https,tcp,tls,crypto,data',
        '-i', local_m3u8_input,
        '-vf', "scale=1280:720,drawtext=text='KIDN TV':fontcolor=white:fontsize=30:x=(w-text_w)/2:y=(h-text_h)/2:box=1:boxcolor=black@0.5",
        '-r', '30',
        '-c:v', 'libx264',
        '-preset', 'ultrafast',
        '-tune', 'zerolatency',
        '-c:a', 'copy',
        '-f', 'hls',
        '-hls_time', '2',
        '-hls_list_size', '30',
        '-hls_flags', 'delete_segments+append_list',
        output_m3u8_path
    ]
    
    while True:
        print("[+] بدء معالجة البث بدقة محسنة وسلسة...")
        subprocess.run(ffmpeg_cmd)
        print("[-] إعادة تشغيل المعالجة خلال ثانيتين...")
        time.sleep(2)

class HLSHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        super().end_headers()

    def guess_type(self, path):
        if path.endswith(".m3u8"):
            return "application/vnd.apple.mpegurl"
        elif path.endswith(".ts"):
            return "video/mp2t"
        return super().guess_type(path)

    def copyfile(self, source, outputfile):
        try:
            super().copyfile(source, outputfile)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def log_message(self, format, *args):
        return

def start_server():
    os.chdir(os.path.abspath(OUTPUT_DIR))
    with socketserver.TCPServer(("", PORT), HLSHTTPRequestHandler) as httpd:
        print(f"\n[✔] السيرفر يعمل الآن بسلاسة تامة وبدون تقطيع!")
        print(f"[🔗] رابط البث المحلي: http://127.0.0.1:{PORT}/output.m3u8\n")
        httpd.serve_forever()

if __name__ == "__main__":
    t_manifest = threading.Thread(target=update_manifest_loop)
    t_manifest.daemon = True
    t_manifest.start()

    t_ffmpeg = threading.Thread(target=start_ffmpeg)
    t_ffmpeg.daemon = True
    t_ffmpeg.start()

    start_server()
