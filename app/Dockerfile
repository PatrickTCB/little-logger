FROM python:3

RUN mkdir /db
RUN mkdir /app
RUN mkdir /app/lib

RUN apt-get clean && apt-get update && apt-get install -y locales python3-pip
RUN locale-gen en_US.UTF-8
RUN sed -i -e 's/# en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/' /etc/locale.gen
ENV LC_ALL="en_US.UTF-8"
ENV LC_CTYPE="en_US.UTF-8"
ENV TZ="Europe/Berlin"
RUN dpkg-reconfigure --frontend=noninteractive locales
RUN pip3 install "fastapi[standard]"

EXPOSE 8000

COPY server.py /app/server.py
COPY lib/db.py /app/lib/ldb.py

WORKDIR /app

CMD [ "fastapi", "run", "server.py"]