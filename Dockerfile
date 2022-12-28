FROM python:3.7
COPY casino_holdem_live.py.py .
COPY zero.json .
COPY emitter.py .
COPY requirements.txt .
RUN pip3 install -r requirements.txt
CMD ["python3", "casino_holdem_live.py.py"]