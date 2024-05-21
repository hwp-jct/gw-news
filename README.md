# gw-news

## Python Environment
- 3.9, pyinstaller
```powershell
py -3.9 -m venv .venv
```

## 소스 저정소에 가져온 후 패키기 설치
```sh
python -m venv .venv # 가상환경 생성
source venv/bin/activate # 가상환경 활성화
pip install -r requirements.txt # 패키지 설치
```

## Make Executable File
```sh
pyinstaller -F xx.py
```
