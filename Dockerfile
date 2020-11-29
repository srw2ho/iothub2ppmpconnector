FROM python:slim-buster

RUN apt update && apt install -y git gcc
RUN git config --global credential.helper cache

COPY ./ ./

RUN pip install Cython

# RUN pip install -r requirements.txt

# RUN pip install setup.py




RUN pip install git+https://github.com/srw2ho/iothub2ppmpconnector.git

# ENTRYPOINT python -u -m ppmp2influx

ENTRYPOINT tail -f /dev/null
