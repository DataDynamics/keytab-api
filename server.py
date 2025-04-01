#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Author: KIM BYOUNGGON (architect@data-dynamics.io)
Description: Active Directory 서버에서 Keytab을 생성 및 다운로드를 기능을 제공하는 API
"""

import argparse
import io
import logging
import os
import subprocess
from logging.handlers import TimedRotatingFileHandler

import yaml
from flasgger import Swagger
from flask import Flask, jsonify, send_file, request, abort
from hdfs import InsecureClient


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

formatter = logging.Formatter('%(asctime)s - [%(levelname)s] %(filename)s:%(lineno)d - %(message)s')  # Formatter
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

    # Active Directory Realm
    realm = app_config.get('realm', 'DATALAKE')
    password = app_config.get('keytab-default-password', '@123qwe')

    # Kerberos 명령어 사용하여 Keytab 생성
    command = [
        'C:\Windows\System32\ktpass.exe',
        '-out',
        f'{keytab_file_path}\\{username}.keytab',
        '-princ',
        f'{username}@{realm}.LOCAL',
        '-mapuser',
        f'{realm}\\{username}',
        '-pass',
        f'{password}',
        '-ptype',
        'KRB5_NT_PRINCIPAL',
        '-kvno',
        '0'
    ]
    command_string = ' '.join(command)
    logger.info(f"Keytab 파일을 생성하기 위한 커맨드 라인: {command_string}")

    process = subprocess.run(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    if process.returncode != 0:
        logger.warning(f"Keytab 파일을 생성할 수 없습니다. 커맨드라인 에러: {process.stderr}")
        return False

    logger.info(f"로컬 경로({keytab_file_path}\\{username}.keytab)에 keytab 파일을 생성했습니다.")
    return True


def upload_to_hdfs(local_file_path, hdfs_path, hdfs_url="http://httpfs:14000"):
    """
    로컬 파일을 HDFS에 업로드합니다.
    """
    client = InsecureClient(hdfs_url)

    # Keytab 파일 존재여부 확인 및 삭제
    delete_file_if_exists(hdfs_path, hdfs_path)

    # HDFS에 파일 업로드
    try:
        with open(local_file_path, 'rb') as f:
            client.write(hdfs_path, f)
        logger.info(f"생성한 로컬의 keytab 파일({local_file_path}을 HDFS의 {hdfs_path} 경로에 업로드하였습니다.")
    except Exception as e:
        logger.warning(f"HDFS에 파일을 업로드할 수 없습니다. 원인: {e}")
        return False
    return True


@app.route('/api/keytab/create', methods=['POST'])
def create_and_upload_keytab():
    """
    Keytab 파일 생성 및 HDFS 업로드
    ---
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - username
          properties:
            username:
              type: string
              example: Administrator
    responses:
      200:
        description: 성공적으로 사용자의 keytab 파일을 생성하고 HDFS에 업로드
      500:
        description: Keytab 파일 생성 에러
    """
    try:
        # 사용자명 받아오기
        username = request.json.get('username')
        if not username:
            return jsonify({"error": "'username' 파라미터가 필요합니다."}), 400

        logger.info(f"Keytab 파일을 생성합니다. 사용자: {username}")

        # Keytab 파일을 생성할 로컬 임시 경로
        temp_path = app_config['keytab-file-local-temp-path']
        ensure_directory_exists(temp_path)

        # Keytab 파일 경로 설정
        hdfs_keytab_path = app_config['keytab-file-path']
        keytab_file_path = f"{temp_path}\\{username}.keytab"
        hdfs_path = f"{hdfs_keytab_path}/{username}.keytab"

        # Keytab 파일 생성
        if create_keytab(username, temp_path):
            # Keytab 파일을 HDFS에 업로드
            if upload_to_hdfs(keytab_file_path, hdfs_path, app_config['webhdfs-url']):
                return jsonify({"message": f"사용자({username})의 keytab 파일을 생성하고 HDFS에 업로드하였습니다."}), 200
            else:
                return jsonify({"error": "HDFS에 keytab 파일을 업로드할 수 없습니다."}), 500
        else:
            return jsonify({"error": "Keytab 파일을 생성할 수 없습니다."}), 500

    except Exception as e:
        logger.warning(f"Keytab 파일을 생성하던 도중 에러가 발생했습니다. 원인: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route('/api/keytab/download', methods=['GET'])
def download_file():
    """
    Keytab 파일 다운로드
    ---
    parameters:
        - name: username
          in: query
          type: string
          required: true
          description: Keytab 파일을 다운로드할 사용자명
    responses:
      200:
        description: 성공적으로 사용자의 keytab 파일을 다운로드합니다.
        content:
            application/octet-stream:
                schema:
                    type: string
                    format: binary
      400:
        description: 사용자명 없음 (username)
      404:
        description: 사용자의 keytab 파일 없음
    """
    try:
        client = InsecureClient(app_config['webhdfs-url'])

        # Keytab을 생성할 Username
        username = request.args.get('username')
        logger.info(f"사용자의 keytab 파일을 다운로드합니다. 사용자: {username}")
        if not username:
            abort(400, description="Query 파라미터가 존재하지 않습니다. 누락된 파라미터: 'username'")

        # HDFS에서 파일 읽기
        hdfs_keytab_path = app_config['keytab-file-path']
        hdfs_path = f"{hdfs_keytab_path}/{username}.keytab"

        file_status = client.status(hdfs_path, strict=False)
        if not file_status:
            logger.warning(f"HDFS에서 keytab 파일을 찾을 수 없습니다. 경로: {hdfs_path}")
            abort(404, description="HDFS에서 keytab 파일을 찾을 수 없습니다. 관리자에게 문의하십시오.")

        with client.read(hdfs_path) as reader:
            file_data = reader.read()

        file_like = io.BytesIO(file_data)
        file_like.seek(0)

        # 메모리에서 파일 데이터를 바이트 스트림으로 변환
        return send_file(
            file_like,
            as_attachment=True,
            download_name=os.path.basename(hdfs_path),  # 파일 이름 지정
            mimetype='application/octet-stream'  # MIME 타입을 일반 바이너리 파일로 설정
        )
    except Exception as e:
        logger.warning(f"에러가 발생했습니다. 원인: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


def ensure_directory_exists(directory_path):
    if not os.path.exists(directory_path):
        os.makedirs(directory_path)
        print(f"Directory '{directory_path}' was created.")
    else:
        print(f"Directory '{directory_path}' already exists.")


def delete_file_if_exists(client, hdfs_path):
    try:
        status = client.status(hdfs_path, strict=False)
        if status:
            client.delete(hdfs_path)
            print(f"파일을 삭제했습니다. 경로: {hdfs_path}")
        else:
            print(f"파일을 찾을 수 없습니다. 경로: {hdfs_path}")
    except Exception as e:
        print(f"파일을 삭제하던 도중 에러가 발생했습니다. 원인: {str(e)}")


if __name__ == '__main__':
    app.run(
        host=app_config.get('host', '0.0.0.0'),
        port=app_config.get('port', 5000),
        debug=app_config.get('debug', False)
    )
