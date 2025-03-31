import argparse
import yaml
from flask import Flask, request, jsonify
from flasgger import Swagger
import subprocess
import logging
from logging.handlers import TimedRotatingFileHandler
import json
from hdfs import InsecureClient
import os

# YAML 설정 파일 로드 함수
def load_config(path='config.yaml'):
    with open(path, 'r') as f:
        return yaml.safe_load(f)


# argparse를 사용해 커맨드라인 인자 처리
def parse_args():
    parser = argparse.ArgumentParser(description="Flask server with YAML config")
    parser.add_argument('--config', type=str, default='config.yaml', help='Path to the config YAML file')
    return parser.parse_args()


args = parse_args()
config = load_config(args.config)
app_config = config['app']

# Logger 설정
log_file = app_config['logfile-path']
logger = logging.getLogger("daily_logger")
logger.setLevel(logging.INFO)

handler = TimedRotatingFileHandler(
    filename=log_file,
    when='midnight',  # 자정 기준 롤링
    interval=1,  # 매 1일마다
    backupCount=14,  # 최근 7일치만 보관
    encoding='utf-8',
    utc=False  # 로컬 시간 기준 (True면 UTC 기준)
)

formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')  # Formatter
handler.setFormatter(formatter)

logger.addHandler(handler)  # Log Handler

# Flask App
app = Flask(__name__)
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True

# Swagger
swagger = Swagger(app, template={
    "swagger": "2.0",
    "info": {
        "title": "Keytab API",
        "description": "Keytab API",
        "version": "1.0"
    },
    "basePath": "/",
})


def create_keytab(username, keytab_file_path):
    """
    Keytab 파일을 생성합니다.
    """
    # Kerberos 명령어 사용하여 Keytab 생성
    command = f"ktutil"
    process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    # 명령어 입력으로 Keytab 파일 생성
    input_data = f"add_entry -password -p {username}@YOUR.REALM -k 1 -e aes256-cts-hmac-sha1-96\n"
    input_data += f"wkt {keytab_file_path}\n"
    input_data += "exit\n"
    
    # 프로세스에 데이터 전달
    stdout, stderr = process.communicate(input=input_data)

    if process.returncode != 0:
        print(f"Error creating keytab: {stderr}")
        return False

    print(f"Keytab created at {keytab_file_path}")
    return True

def upload_to_hdfs(local_file_path, hdfs_path, hdfs_url="http://namenode_host:50070"):
    """
    로컬 파일을 HDFS에 업로드합니다.
    """
    client = InsecureClient(hdfs_url)

    # HDFS에 파일 업로드
    try:
        with open(local_file_path, 'rb') as f:
            client.write(hdfs_path, f)
        print(f"Successfully uploaded {local_file_path} to HDFS at {hdfs_path}")
    except Exception as e:
        print(f"Error uploading file to HDFS: {e}")
        return False
    return True

@app.route('/create-keytab', methods=['POST'])
def create_and_upload_keytab():
    """
    POST 요청을 통해 Keytab 파일을 생성하고 HDFS에 업로드합니다.
    """
    try:
        # 사용자명 받아오기
        username = request.json.get('username')
        if not username:
            return jsonify({"error": "Username is required"}), 400
        
        # Keytab 파일 경로 설정
        keytab_file_path = f"/tmp/{username}.keytab"
        hdfs_path = f"/user/hadoop/{username}.keytab"
        
        # Keytab 파일 생성
        if create_keytab(username, keytab_file_path):
            # Keytab 파일을 HDFS에 업로드
            if upload_to_hdfs(keytab_file_path, hdfs_path):
                return jsonify({"message": f"Keytab for {username} created and uploaded to HDFS."}), 200
            else:
                return jsonify({"error": "Failed to upload Keytab to HDFS"}), 500
        else:
            return jsonify({"error": "Failed to create Keytab"}), 500

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/download/<path:file_path>', methods=['GET'])
def download_file(file_path):
    """
    HDFS에서 파일을 다운로드하는 API 엔드포인트.
    :param file_path: 다운로드할 HDFS 파일 경로
    :return: 파일을 클라이언트로 전송
    """
    try:
        # HDFS에서 파일 읽기
        file_data = client.read(file_path)
        
        # 메모리에서 파일 데이터를 바이트 스트림으로 변환
        return send_file(
            io.BytesIO(file_data),
            as_attachment=True,
            download_name=os.path.basename(file_path),  # 파일 이름 지정
            mimetype='application/octet-stream'  # MIME 타입을 일반 바이너리 파일로 설정
        )
    except Exception as e:
        # 오류 처리
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(
        host=app_config.get('host', '127.0.0.1'),
        port=app_config.get('port', 5000),
        debug=app_config.get('debug', False)
    )
